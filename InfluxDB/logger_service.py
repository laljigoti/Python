"""Background service: polls the PLC over Modbus TCP and writes to InfluxDB 3.

The service runs in its own thread so the web UI never blocks on network I/O.
The UI only reads the state exposed by this class.
"""
from __future__ import annotations

import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone

from influxdb_client_3 import InfluxDBClient3, Point
from pymodbus.client import ModbusTcpClient


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Settings:
    plc_host: str = "127.0.0.1"
    plc_port: int = 502
    device_id: int = 1
    poll_s: float = 1.0

    influx_host: str = "http://localhost:8181"
    influx_token: str = "apiv3_FhtnkJEGkCNE-NnN9iNZIA4Z_mxJMcM9kLHnwQ_3Qbsv2MfUP0UElXoQgtgXXjOASq7xaN6cZeahXfLGGKqeaA"
    influx_database: str = "MachineDB"

    machine: str = "sim_01"
    line: str = "A"

    buffer_max: int = 10_000       # points kept in memory while InfluxDB is down
    live_window: int = 600         # samples kept for the live chart (10 min at 1 Hz)
    temp_alarm: float = 80.0       # degC, shown red in the UI above this value

    @classmethod
    def from_env(cls) -> "Settings":
        e = os.getenv
        return cls(
            plc_host=e("PLC_HOST", cls.plc_host),
            plc_port=int(e("PLC_PORT", cls.plc_port)),
            device_id=int(e("PLC_DEVICE_ID", cls.device_id)),
            poll_s=float(e("POLL_S", cls.poll_s)),
            influx_host=e("INFLUX_HOST", cls.influx_host),
            influx_token=e("INFLUX_TOKEN", cls.influx_token),
            influx_database=e("INFLUX_DATABASE", cls.influx_database),
            machine=e("MACHINE", cls.machine),
            line=e("LINE", cls.line),
            buffer_max=int(e("BUFFER_MAX", cls.buffer_max)),
            live_window=int(e("LIVE_WINDOW", cls.live_window)),
            temp_alarm=float(e("TEMP_ALARM", cls.temp_alarm)),
        )


@dataclass(frozen=True)
class Sample:
    ts: datetime          # timezone-aware UTC, taken when the PLC was read
    temperature: float    # degC
    current: float        # A
    running: bool
    cycles: int


# History ranges offered in the UI: label -> (minutes, aggregation bucket)
HISTORY_RANGES: dict[str, tuple[int, str]] = {
    "15 min": (15, "1 second"),
    "1 h": (60, "10 seconds"),
    "6 h": (360, "1 minute"),
    "24 h": (1440, "5 minutes"),
}


# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------
class LoggerService:
    def __init__(self, cfg: Settings) -> None:
        self.cfg = cfg
        self._plc = ModbusTcpClient(cfg.plc_host, port=cfg.plc_port, timeout=2)
        self._db = InfluxDBClient3(
            host=cfg.influx_host, token=cfg.influx_token, database=cfg.influx_database
        )

        self._buffer: deque[Sample] = deque(maxlen=cfg.buffer_max)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        # State read by the UI (written only by the worker thread)
        self.latest: Sample | None = None
        self.history: deque[Sample] = deque(maxlen=cfg.live_window)
        self.plc_ok: bool | None = None     # None = not tried yet
        self.db_ok: bool | None = None
        self.last_error: str = ""
        self.written_total: int = 0
        self.started_at: datetime = datetime.now(timezone.utc)

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="logger", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._plc.close()
        self._db.close()

    @property
    def buffered(self) -> int:
        return len(self._buffer)

    # -- worker loop -------------------------------------------------------
    def _run(self) -> None:
        while not self._stop.is_set():
            t0 = time.monotonic()
            self._poll_plc()
            self._flush()
            self._stop.wait(max(0.05, self.cfg.poll_s - (time.monotonic() - t0)))

    def _poll_plc(self) -> None:
        try:
            if not self._plc.connected and not self._plc.connect():
                raise ConnectionError(
                    f"PLC not reachable at {self.cfg.plc_host}:{self.cfg.plc_port}"
                )
            rr = self._plc.read_holding_registers(
                address=0, count=4, device_id=self.cfg.device_id
            )
            if rr.isError():
                raise IOError(f"Modbus error: {rr}")

            temp, cur, running, cycles = rr.registers
            sample = Sample(
                ts=datetime.now(timezone.utc),
                temperature=temp / 10.0,
                current=cur / 10.0,
                running=bool(running),
                cycles=cycles,
            )
            self.latest = sample
            self.history.append(sample)
            self._buffer.append(sample)
            self.plc_ok = True
        except Exception as exc:  # noqa: BLE001 - keep the logger alive
            self.plc_ok = False
            self.last_error = f"PLC: {exc}"
            self._plc.close()   # force a clean reconnect on the next cycle

    def _flush(self) -> None:
        if not self._buffer:
            return
        batch = list(self._buffer)
        try:
            self._db.write(record=[self._to_point(s) for s in batch])
        except Exception as exc:  # noqa: BLE001
            self.db_ok = False
            self.last_error = f"InfluxDB: {exc}"
            return
        for _ in batch:                      # only this thread touches the deque
            self._buffer.popleft()
        self.written_total += len(batch)
        self.db_ok = True

    def _to_point(self, s: Sample) -> Point:
        return (
            Point("motor")
            .tag("machine", self.cfg.machine)
            .tag("line", self.cfg.line)
            .field("temperature", s.temperature)
            .field("current", s.current)
            .field("running", s.running)
            .field("cycles", s.cycles)
            .time(s.ts)                      # PLC read time, not write time
        )

    # -- history (called from the UI via run.io_bound) --------------------
    def query_history(self, range_label: str) -> list[tuple[int, float, float]]:
        """Return [(epoch_ms, temperature, current), ...] aggregated per bucket."""
        minutes, bucket = HISTORY_RANGES[range_label]
        sql = f"""
            SELECT date_bin(INTERVAL '{bucket}', time) AS t,
                   avg(temperature) AS temperature,
                   avg("current")   AS current_a
            FROM motor
            WHERE machine = '{self.cfg.machine}'
              AND time >= now() - INTERVAL '{minutes} minutes'
            GROUP BY 1
            ORDER BY 1
        """
        df = self._db.query(sql).to_pandas()
        rows: list[tuple[int, float, float]] = []
        for t, temp, cur in zip(df["t"], df["temperature"], df["current_a"]):
            ts = t.tz_localize("UTC") if t.tzinfo is None else t
            rows.append((int(ts.timestamp() * 1000), round(float(temp), 2), round(float(cur), 2)))
        return rows
