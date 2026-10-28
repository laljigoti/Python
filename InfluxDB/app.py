"""PLC data logger with a NiceGUI dashboard.

Run with:  uv run app.py
Then open: http://localhost:8080
"""
from __future__ import annotations

from datetime import datetime, timezone

from dotenv import load_dotenv
from nicegui import app, run, ui

load_dotenv()  # read .env before Settings.from_env()

from logger_service import HISTORY_RANGES, LoggerService, Settings  # noqa: E402

cfg = Settings.from_env()
service = LoggerService(cfg)
app.on_startup(service.start)
app.on_shutdown(service.stop)

TEMP_COLOR = "#e0892b"     # amber
CURRENT_COLOR = "#2f9bb5"  # teal


# --------------------------------------------------------------------------
# Small UI helpers
# --------------------------------------------------------------------------
def kpi_card(title: str, icon: str, unit: str):
    """A value card. Returns the label that shows the value."""
    with ui.card().classes("w-full gap-1 p-4"):
        with ui.row().classes("w-full items-center justify-between no-wrap"):
            ui.label(title).classes("text-sm text-slate-500")
            ui.icon(icon).classes("text-xl text-slate-400")
        with ui.row().classes("items-baseline gap-1 no-wrap"):
            value = ui.label("--").classes("text-4xl font-semibold tabular-nums")
            ui.label(unit).classes("text-slate-500")
    return value


def status_row(label: str):
    """A row in the system panel. Returns the value label."""
    with ui.row().classes("w-full items-center justify-between no-wrap"):
        ui.label(label).classes("text-slate-500")
        value = ui.label("--").classes("font-medium")
    return value


def make_chart(height: str = "h-96"):
    return ui.echart(
        {
            "animation": False,
            "tooltip": {"trigger": "axis"},
            "legend": {"data": ["Temperature (°C)", "Current (A)"]},
            "grid": {"left": 55, "right": 55, "top": 45, "bottom": 30},
            "xAxis": {"type": "time"},
            "yAxis": [
                {"type": "value", "name": "°C", "scale": True},
                {"type": "value", "name": "A", "scale": True, "splitLine": {"show": False}},
            ],
            "series": [
                {
                    "name": "Temperature (°C)",
                    "type": "line",
                    "showSymbol": False,
                    "smooth": True,
                    "color": TEMP_COLOR,
                    "data": [],
                },
                {
                    "name": "Current (A)",
                    "type": "line",
                    "showSymbol": False,
                    "smooth": True,
                    "yAxisIndex": 1,
                    "color": CURRENT_COLOR,
                    "data": [],
                },
            ],
        }
    ).classes(f"w-full {height}")


def set_badge(badge: ui.badge, ok: bool | None, ok_text: str, bad_text: str) -> None:
    if ok is None:
        badge.set_text("Waiting")
        badge.props("color=grey")
    elif ok:
        badge.set_text(ok_text)
        badge.props("color=positive")
    else:
        badge.set_text(bad_text)
        badge.props("color=negative")


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------
@ui.page("/")
def index() -> None:
    ui.colors(primary="#2f6f8f", secondary="#4b5563", positive="#2e8b57", negative="#c0392b")
    dark = ui.dark_mode(value=True)

    # ---- header ----------------------------------------------------------
    with ui.header(elevated=True).classes("items-center justify-between px-6 py-3"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("precision_manufacturing").classes("text-3xl")
            with ui.column().classes("gap-0"):
                ui.label("Machine monitor").classes("text-lg font-semibold leading-tight")
                ui.label(f"{cfg.machine} · line {cfg.line}").classes("text-xs opacity-80")
        with ui.row().classes("items-center gap-4"):
            with ui.row().classes("items-center gap-1"):
                ui.label("PLC").classes("text-sm")
                plc_badge = ui.badge("Waiting").props("color=grey")
            with ui.row().classes("items-center gap-1"):
                ui.label("Database").classes("text-sm")
                db_badge = ui.badge("Waiting").props("color=grey")
            ui.button(icon="dark_mode", on_click=dark.toggle).props("flat round color=white").tooltip(
                "Switch light / dark"
            )

    # ---- tabs ------------------------------------------------------------
    with ui.tabs().classes("w-full") as tabs:
        live_tab = ui.tab("Live", icon="monitor_heart")
        history_tab = ui.tab("History", icon="history")

    with ui.tab_panels(tabs, value=live_tab).classes("w-full bg-transparent"):
        # ================= LIVE =================
        with ui.tab_panel(live_tab).classes("p-0"):
            with ui.column().classes("w-full max-w-7xl mx-auto gap-4 p-4"):
                with ui.grid(columns="repeat(auto-fit, minmax(200px, 1fr))").classes("w-full gap-4"):
                    temp_val = kpi_card("Temperature", "device_thermostat", "°C")
                    cur_val = kpi_card("Motor current", "bolt", "A")
                    cycles_val = kpi_card("Cycles", "autorenew", "")
                    with ui.card().classes("w-full gap-1 p-4"):
                        with ui.row().classes("w-full items-center justify-between no-wrap"):
                            ui.label("Motor").classes("text-sm text-slate-500")
                            ui.icon("settings").classes("text-xl text-slate-400")
                        state_chip = ui.chip("--", icon="help").props("outline")

                with ui.row().classes("w-full gap-4 items-stretch no-wrap max-md:flex-wrap"):
                    with ui.card().classes("grow p-4"):
                        ui.label("Last 10 minutes").classes("text-base font-medium")
                        live_chart = make_chart()

                    with ui.card().classes("w-full md:w-80 p-4 gap-3"):
                        ui.label("System").classes("text-base font-medium")
                        last_val = status_row("Last sample")
                        written_val = status_row("Points written")
                        buffer_val = status_row("Waiting to write")
                        uptime_val = status_row("Running for")
                        ui.separator()
                        ui.label("Last problem").classes("text-sm text-slate-500")
                        error_val = ui.label("None").classes("text-sm break-words")

        # ================= HISTORY =================
        with ui.tab_panel(history_tab).classes("p-0"):
            with ui.column().classes("w-full max-w-7xl mx-auto gap-4 p-4"):
                with ui.card().classes("w-full p-4"):
                    with ui.row().classes("w-full items-center justify-between"):
                        range_toggle = ui.toggle(list(HISTORY_RANGES), value="1 h").props("no-caps")
                        with ui.row().classes("items-center gap-3"):
                            hist_info = ui.label("").classes("text-sm text-slate-500")
                            refresh_btn = ui.button("Reload", icon="refresh").props("flat")
                    hist_chart = make_chart("h-[28rem]")

    # ---- live updates ----------------------------------------------------
    def refresh_live() -> None:
        s = service.latest
        set_badge(plc_badge, service.plc_ok, "Connected", "Offline")
        set_badge(db_badge, service.db_ok, "Connected", "Offline")

        if s is not None:
            temp_val.set_text(f"{s.temperature:.1f}")
            temp_val.classes(
                add="text-red-500" if s.temperature >= cfg.temp_alarm else "",
                remove="" if s.temperature >= cfg.temp_alarm else "text-red-500",
            )
            cur_val.set_text(f"{s.current:.1f}")
            cycles_val.set_text(str(s.cycles))
            if s.running:
                state_chip.set_text("Running")
                state_chip.props("icon=play_arrow color=positive")
            else:
                state_chip.set_text("Stopped")
                state_chip.props("icon=stop color=grey")
            age = (datetime.now(timezone.utc) - s.ts).total_seconds()
            last_val.set_text(f"{age:.0f} s ago" if age >= 1 else "now")

        written_val.set_text(f"{service.written_total:,}")
        buffer_val.set_text(f"{service.buffered:,}")
        up = int((datetime.now(timezone.utc) - service.started_at).total_seconds())
        uptime_val.set_text(f"{up // 3600}h {up % 3600 // 60:02d}m {up % 60:02d}s")
        error_val.set_text(service.last_error or "None")

        hist = list(service.history)
        live_chart.options["series"][0]["data"] = [
            [int(x.ts.timestamp() * 1000), x.temperature] for x in hist
        ]
        live_chart.options["series"][1]["data"] = [
            [int(x.ts.timestamp() * 1000), x.current] for x in hist
        ]
        live_chart.update()

    ui.timer(1.0, refresh_live)

    # ---- history loading -------------------------------------------------
    async def load_history() -> None:
        label = range_toggle.value
        refresh_btn.props("loading")
        try:
            rows = await run.io_bound(service.query_history, label)
        except Exception as exc:  # noqa: BLE001
            ui.notify(f"Could not load history: {exc}", type="negative", multi_line=True)
            hist_info.set_text("Query failed")
            return
        finally:
            refresh_btn.props(remove="loading")

        hist_chart.options["series"][0]["data"] = [[t, a] for t, a, _ in rows]
        hist_chart.options["series"][1]["data"] = [[t, b] for t, _, b in rows]
        hist_chart.update()
        hist_info.set_text(
            f"{len(rows):,} points" if rows else "No data in this range yet"
        )

    range_toggle.on_value_change(load_history)
    refresh_btn.on_click(load_history)
    tabs.on_value_change(lambda e: load_history() if e.value == "History" else None)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Machine monitor", port=8080, reload=False, favicon="🏭")
