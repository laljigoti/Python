"""ADS communication module (TwinCAT <-> Python).

Kept free of any UI code so it can be reused and tested on its own.

Design rules
------------
* Every ADS call runs on ONE dedicated worker thread (``max_workers=1``).
  That gives strict FIFO ordering, so writes reach the PLC in exactly the
  order they were requested (e.g. "button pressed" never overtakes
  "button released").
* A lock additionally protects the connection object, so the blocking
  (sync) methods are also safe to call from other threads.
* Every blocking method has an ``*_async`` twin that hands the work to the
  worker thread, so async code (e.g. NiceGUI handlers) never blocks the
  event loop.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, TypeVar

import pyads

log = logging.getLogger(__name__)

T = TypeVar("T")

# Config "type" string -> pyads data type
_TYPE_MAP: dict[str, Any] = {
    "BOOL": pyads.PLCTYPE_BOOL,
    "BYTE": pyads.PLCTYPE_BYTE,
    "SINT": pyads.PLCTYPE_SINT,
    "USINT": pyads.PLCTYPE_USINT,
    "INT": pyads.PLCTYPE_INT,
    "UINT": pyads.PLCTYPE_UINT,
    "WORD": pyads.PLCTYPE_WORD,
    "DINT": pyads.PLCTYPE_DINT,
    "UDINT": pyads.PLCTYPE_UDINT,
    "DWORD": pyads.PLCTYPE_DWORD,
    "REAL": pyads.PLCTYPE_REAL,
    "LREAL": pyads.PLCTYPE_LREAL,
}

_NOT_CONNECTED_MSG = "Not connected to the PLC. Press Connect first."


class AdsError(Exception):
    """Raised when an ADS operation fails."""


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class PlcVariable:
    name: str          # full symbol path in the PLC
    type: str          # e.g. "BOOL"
    display_name: str  # label shown in the UI


@dataclass(frozen=True)
class AdsConfig:
    ams_id: str
    port: int
    variables: tuple[PlcVariable, ...]

    @classmethod
    def from_file(cls, path: str | Path) -> "AdsConfig":
        """Load and validate the JSON configuration file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))

        variables = tuple(
            PlcVariable(
                name=v["name"],
                type=v.get("type", "BOOL").upper(),
                display_name=v.get("display_name", v["name"]),
            )
            for v in data["PLC_Var"]
        )

        # Fail early on typos instead of at the first read/write.
        for var in variables:
            if var.type not in _TYPE_MAP:
                raise ValueError(f"Unsupported PLC type '{var.type}' for {var.name}")

        return cls(data["plc_ams_id"], int(data["plc_port"]), variables)


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------
class AdsClient:
    """Thread-safe wrapper around a pyads connection.

    The client never connects silently: call ``connect()`` / ``connect_async()``
    first. After any ADS failure the link is closed and must be re-opened
    explicitly.
    """

    def __init__(self, config: AdsConfig) -> None:
        self._cfg = config
        # name -> pyads type, for O(1) lookup when writing
        self._types = {v.name: _TYPE_MAP[v.type] for v in config.variables}
        self._conn: pyads.Connection | None = None
        self._lock = threading.Lock()
        # max_workers=1 -> strict FIFO ordering of all ADS calls
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ads")

    # ---------- internal helpers ----------
    async def _run(self, func: Callable[..., T], *args: Any) -> T:
        """Run a blocking method on the ADS worker thread without blocking the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, func, *args)

    @contextmanager
    def _session(self, action: str) -> Iterator[pyads.Connection]:
        """Lock the client and yield the open connection.

        * Raises ``AdsError`` if there is no open connection.
        * If the ADS call inside the ``with`` block fails, the link is closed
          (it is considered broken) and the error is re-raised as ``AdsError``.
        """
        with self._lock:
            conn = self._conn
            if conn is None or not conn.is_open:
                raise AdsError(_NOT_CONNECTED_MSG)
            try:
                yield conn
            except pyads.ADSError as exc:
                log.warning("ADS %s failed: %s", action, exc)
                self._close_unlocked()
                raise AdsError(f"{action} failed: {exc}") from exc

    def _close_unlocked(self) -> None:
        """Close the connection. The caller must already hold ``self._lock``."""
        if self._conn is None:
            return
        try:
            self._conn.close()
        except pyads.ADSError:
            pass  # already broken - nothing more to do
        self._conn = None

    # ---------- connection ----------
    @property
    def connected(self) -> bool:
        """True if the link is open AND the PLC answers (cheap round-trip)."""
        with self._lock:
            conn = self._conn
            if conn is None or not conn.is_open:
                return False
            try:
                return conn.read_state() is not None
            except pyads.ADSError:
                return False

    def connect(self) -> None:
        """Open a fresh connection (any previous one is closed first)."""
        with self._lock:
            self._close_unlocked()
            conn = pyads.Connection(self._cfg.ams_id, self._cfg.port)
            try:
                conn.open()
                conn.read_state()  # verify the PLC really answers
            except pyads.ADSError as exc:
                try:
                    conn.close()  # don't leak a half-open connection
                except pyads.ADSError:
                    pass
                raise AdsError(
                    f"Cannot connect to {self._cfg.ams_id}:{self._cfg.port} - {exc}"
                ) from exc
            self._conn = conn
            log.info("ADS connected to %s:%s", self._cfg.ams_id, self._cfg.port)

    def disconnect(self) -> None:
        """Close the ADS connection. The client can be connected again later."""
        with self._lock:
            self._close_unlocked()

    def close(self) -> None:
        """Disconnect AND shut down the worker thread (final; call on app exit)."""
        self.disconnect()
        self._executor.shutdown(wait=False)

    # ---------- reading ----------
    def read_many(self, names: list[str]) -> dict[str, Any]:
        """Blocking batched read of several variables (one ADS round-trip)."""
        with self._session("Read") as conn:
            return dict(conn.read_list_by_name(names))

    # ---------- writing ----------
    def write(self, name: str, value: Any) -> None:
        """Blocking write of a single variable."""
        plc_type = self._types.get(name)
        if plc_type is None:
            raise AdsError(f"Variable not in config: {name}")
        with self._session(f"Write of {name}") as conn:
            conn.write_by_name(name, value, plc_type)

    def write_many(self, values: dict[str, Any]) -> None:
        """Blocking batched write of several variables (one ADS round-trip)."""
        unknown = [name for name in values if name not in self._types]
        if unknown:
            raise AdsError(f"Variable(s) not in config: {', '.join(unknown)}")

        with self._session("Batch write") as conn:
            result = conn.write_list_by_name(values)

        # pyads reports a per-variable status string; anything but "no error" is a failure.
        failed = {n: r for n, r in result.items() if str(r).lower() != "no error"}
        if failed:
            details = ", ".join(f"{n}: {r}" for n, r in failed.items())
            raise AdsError(f"{len(failed)} variable(s) could not be written ({details})")

    # ---------- async API (for NiceGUI / asyncio code) ----------
    async def connect_async(self) -> None:
        """Open the ADS connection without blocking the event loop."""
        await self._run(self.connect)

    async def disconnect_async(self) -> None:
        """Close the ADS connection (the client can be connected again later)."""
        await self._run(self.disconnect)

    async def connected_async(self) -> bool:
        """Check the link state without blocking the event loop."""
        return await self._run(lambda: self.connected)

    async def read_many_async(self, names: list[str]) -> dict[str, Any]:
        return await self._run(self.read_many, names)

    async def write_async(self, name: str, value: Any) -> None:
        """Non-blocking write for use from async code (NiceGUI handlers)."""
        await self._run(self.write, name, value)

    async def write_many_async(self, values: dict[str, Any]) -> None:
        await self._run(self.write_many, values)