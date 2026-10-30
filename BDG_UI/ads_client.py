"""ADS communication module (TwinCAT <-> Python).

Kept free of any UI code so it can be reused and tested on its own.
All ADS calls run on ONE dedicated worker thread, so writes reach the PLC
in exactly the order they were requested (press -> release never swaps).
"""
from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyads

log = logging.getLogger(__name__)

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


class AdsError(Exception):
    """Raised when an ADS operation fails."""


@dataclass(frozen=True) #  makes the instances of your data class immutable (read-only)
class PlcVariable:
    name: str          # full symbol path in the PLC
    type: str          # e.g. "BOOL"
    display_name: str  # label shown in the UI


@dataclass(frozen=True)
class AdsConfig:
    ams_id: str
    port: int
    variables: tuple[PlcVariable, ...] # ... means tuple can have zero, one, or many elements

    @classmethod
    def from_file(cls, path: str | Path) -> "AdsConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        variables = tuple(
            PlcVariable(
                name=v["name"],
                type=v.get("type", "BOOL").upper(),
                display_name=v.get("display_name", v["name"]),
            )
            for v in data["PLC_Var"]
        )
        for v in variables:
            if v.type not in _TYPE_MAP:
                raise ValueError(f"Unsupported PLC type '{v.type}' for {v.name}")
        return cls(data["plc_ams_id"], int(data["plc_port"]), variables)


class AdsClient:
    """Thread-safe wrapper around a pyads connection with auto-reconnect."""

    def __init__(self, config: AdsConfig) -> None:
        self._cfg = config
        self._types = {v.name: _TYPE_MAP[v.type] for v in config.variables}
        self._conn: pyads.Connection | None = None
        self._lock = threading.Lock()
        # max_workers=1 -> strict FIFO ordering of all ADS calls
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ads")

    # ---------- connection ----------
    @property
    def connected(self) -> bool:
        conn = self._conn
        if conn is None or not conn.is_open:
            return False
        try:
            state = conn.read_state()  # cheap round-trip to verify the link
            return state is not None
        except pyads.ADSError:
            return False

    def connect(self) -> None:
        with self._lock:
            self._close_unlocked()
            try:
                conn = pyads.Connection(self._cfg.ams_id, self._cfg.port)
                conn.open()
                conn.read_state()
            except pyads.ADSError as exc:
                raise AdsError(f"Cannot connect to {self._cfg.ams_id}:{self._cfg.port} - {exc}") from exc
            self._conn = conn
            log.info("ADS connected to %s:%s", self._cfg.ams_id, self._cfg.port)

    def close(self) -> None:
        with self._lock:
            self._close_unlocked()
        self._executor.shutdown(wait=False)

    def _close_unlocked(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except pyads.ADSError:
                pass
            self._conn = None

    # ---------- writing ----------
    def write(self, name: str, value: Any) -> None:
        """Blocking write. Requires an explicit connect() first (no silent auto-connect)."""
        plc_type = self._types.get(name)
        if plc_type is None:
            raise AdsError(f"Variable not in config: {name}")
        with self._lock:
            if self._conn is None or not self._conn.is_open:
                raise AdsError("Not connected to the PLC. Press Connect first.")
            try:
                self._conn.write_by_name(name, value, plc_type)
            except pyads.ADSError as exc:
                log.warning("ADS write failed (%s): %s", name, exc)
                self._close_unlocked()  # link is bad; user must reconnect
                raise AdsError(f"Write failed for {name}: {exc}") from exc

    def read_many(self, names: list[str]) -> dict[str, Any]:
        """Blocking batched read (one ADS round-trip) of several variables."""
        with self._lock:
            if self._conn is None or not self._conn.is_open:
                raise AdsError("Not connected to the PLC. Press Connect first.")
            try:
                return dict(self._conn.read_list_by_name(names))
            except pyads.ADSError as exc:
                log.warning("ADS read failed: %s", exc)
                self._close_unlocked()
                raise AdsError(f"Read failed: {exc}") from exc

    async def read_many_async(self, names: list[str]) -> dict[str, Any]:
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self.read_many, names)

    async def write_async(self, name: str, value: Any) -> None:
        """Non-blocking write for use from async code (NiceGUI handlers)."""
        import asyncio

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self.write, name, value)

    async def connect_async(self) -> None:
        """Open the ADS connection without blocking the event loop."""
        import asyncio

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self.connect)

    async def disconnect_async(self) -> None:
        """Close the ADS connection (the client can be connected again later)."""
        import asyncio

        def _disconnect() -> None:
            with self._lock:
                self._close_unlocked()

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, _disconnect)

    async def connected_async(self) -> bool:
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, lambda: self.connected)