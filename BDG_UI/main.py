"""NiceGUI front-end: header + 24 Clamp buttons + 24 Park buttons (TwinCAT via ADS)."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from nicegui import app, ui

from ads_client import AdsClient, AdsConfig, AdsError

logging.basicConfig(level=logging.INFO)

def app_dir() -> Path:
    """Folder of the .exe when packaged (PyInstaller / nicegui-pack), else of this script."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


CONFIG_PATH = app_dir() / "Config.json"

try:
    config = AdsConfig.from_file(CONFIG_PATH)
except FileNotFoundError:
    sys.exit(f"Config.json not found. Place it in the same folder as the program:\n  {CONFIG_PATH}")
except (ValueError, KeyError) as exc:
    sys.exit(f"Config.json is invalid ({CONFIG_PATH}): {exc!r}")

plc = AdsClient(config)

# Row definitions: (text found in the PLC variable name, row title, Material icon, mode)
# mode "toggle": click = switch on/off and stay;  "hold": TRUE while held, FALSE on release.
# display_name is just a number, so rows are grouped by the PLC variable name.
ROWS = [
    ("stManuellClamping", "Clamping", "compress", "toggle"),
    ("stGoToParkPos", "Go to park position", "local_parking", "hold"),
]

CSS = """
:root { --btn-w:84px; --btn-h:84px; --gap:14px; --bg:#e3e7ee; --hi:#ffffff; --lo:#b8bfcc; --ink:#3a4252; --ok:#2e9e6a; --bad:#d4493f; }
body { background: var(--bg); color: var(--ink); font-family: 'Segoe UI', system-ui, sans-serif; }
.neu-panel {
  background: var(--bg); border-radius: 28px; padding: 28px; width: fit-content; max-width: 100%;
  box-shadow: 12px 12px 24px var(--lo), -12px -12px 24px var(--hi);
}
.neu-btn {
  background: var(--bg) !important; color: var(--ink) !important;
  border-radius: 18px !important; width: var(--btn-w) !important; min-width: 0 !important; min-height: var(--btn-h); padding: 4px !important;
  font-size: .95rem; font-weight: 600;
  box-shadow: 5px 5px 10px var(--lo), -5px -5px 10px var(--hi) !important;
  transition: box-shadow .12s ease, transform .12s ease;
  touch-action: manipulation; user-select: none; -webkit-user-select: none;
}
.neu-btn .q-icon { font-size: 1.5rem; margin-bottom: 2px; }
.q-btn.neu-btn .q-icon { color: var(--ok) !important; }   /* icon colour */
.neu-btn:active, .neu-btn.is-down {
  box-shadow: inset 4px 4px 8px var(--lo), inset -4px -4px 8px var(--hi) !important;
  transform: scale(.985);
}
.neu-btn.is-on {
  box-shadow: inset 4px 4px 8px var(--lo), inset -4px -4px 8px var(--hi) !important;
  color: var(--ok) !important;
}
.neu-btn:focus-visible { outline: 3px solid #5b7fd6; outline-offset: 4px; }
.neu-btn .q-focus-helper { display: none; }
.neu-btn.q-btn--disabled, .neu-btn[disabled] { opacity: .45 !important; }
.neu-connect { min-height: 52px; min-width: 150px !important; width: auto !important; padding: 4px 18px !important; border-radius: 16px !important; }
.neu-connect .q-icon { font-size: 1.2rem; margin: 0 6px 0 0; }
.neu-grid { display: grid; grid-template-columns: repeat(12, var(--btn-w)); gap: var(--gap);
  justify-content: start; width: 100%; }
@media (max-width: 1250px) { .neu-grid { grid-template-columns: repeat(8, var(--btn-w)); } }
@media (max-width: 900px)  { .neu-grid { grid-template-columns: repeat(6, var(--btn-w)); } }
@media (max-width: 600px)  { .neu-grid { grid-template-columns: repeat(3, var(--btn-w)); justify-content: center; } }
.status-dot { width: 14px; height: 14px; border-radius: 50%; background: var(--bad);
  box-shadow: inset 2px 2px 4px rgba(0,0,0,.25), inset -2px -2px 4px rgba(255,255,255,.6); }
@media (prefers-reduced-motion: reduce) { .neu-btn { transition: none; } }
"""


@ui.page("/")
async def index() -> None:
    ui.add_css(CSS)
    ui.query("body").classes("q-pa-md")
    pressed: set[str] = set()  # variables this browser session currently holds TRUE
    plc_buttons: list[ui.button] = []
    toggle_buttons: dict[str, ui.button] = {}   # PLC variable name -> button
    toggle_state: dict[str, bool] = {}          # last known PLC value

    async def write(name: str, value: bool) -> None:
        try:
            await plc.write_async(name, value)
        except AdsError as exc:
            ui.notify(str(exc), type="negative", position="top", timeout=4000)

    async def press(var_name: str) -> None:
        pressed.add(var_name)
        await write(var_name, True)

    async def release(var_name: str) -> None:
        if var_name in pressed:          # ignore duplicate up/leave/cancel events
            pressed.discard(var_name)
            await write(var_name, False)

    async def release_all() -> None:     # browser closed / link lost while holding a button
        for name in list(pressed):
            await release(name)

    ui.context.client.on_disconnect(release_all)   # only affects hold-type buttons

    def show_state(name: str, on: bool) -> None:
        toggle_state[name] = on
        btn = toggle_buttons[name]
        btn.classes(add="is-on") if on else btn.classes(remove="is-on")

    async def toggle(name: str) -> None:
        new = not toggle_state.get(name, False)
        try:
            await plc.write_async(name, new)
        except AdsError as exc:
            ui.notify(str(exc), type="negative", position="top", timeout=4000)
            return
        show_state(name, new)

    async def refresh_status() -> None:
        ok = await plc.connected_async()
        dot.style(f"background: {'var(--ok)' if ok else 'var(--bad)'}")
        status.set_text(f"PLC connected ({config.ams_id}:{config.port})" if ok else "PLC offline")
        connect_btn.set_text("Disconnect" if ok else "Connect")
        for b in plc_buttons:
            b.set_enabled(ok)
        if ok and toggle_buttons:
            try:  # mirror the real PLC values so the buttons never show a wrong state
                values = await plc.read_many_async(list(toggle_buttons))
                for name, value in values.items():
                    show_state(name, bool(value))
            except AdsError:
                pass  # link dropped; the next cycle shows "PLC offline"
        elif not ok:
            for name in toggle_buttons:
                show_state(name, False)

    async def toggle_connection() -> None:
        connect_btn.disable()
        try:
            if await plc.connected_async():
                await release_all()
                await plc.disconnect_async()
                ui.notify("Disconnected from PLC", type="info", position="top")
            else:
                await plc.connect_async()
                ui.notify("Connected to PLC", type="positive", position="top")
        except AdsError as exc:
            ui.notify(str(exc), type="negative", position="top", timeout=5000)
        finally:
            connect_btn.enable()
            await refresh_status()

    with ui.column().classes("w-full items-center"):
        with ui.element("div").classes("neu-panel"):
            # ---- Row 1: title | connect button | PLC status ----
            with ui.row().classes("w-full items-center justify-between q-mb-lg"):
                ui.label("Roll magazine control").classes("text-h5 text-weight-bold")
                connect_btn = (
                    ui.button("Connect", icon="power", on_click=toggle_connection)
                    .props("flat unelevated no-caps")
                    .classes("neu-btn neu-connect")
                )
                with ui.row().classes("items-center gap-2"):
                    dot = ui.element("div").classes("status-dot")
                    status = ui.label("Checking…")

            # ---- Rows 2 and 3: one button row per PLC variable group ----
            for key, title, icon, mode in ROWS:
                ui.label(title).classes("text-subtitle1 text-weight-medium q-mt-md q-mb-sm")
                with ui.element("div").classes("neu-grid"):
                    for var in (v for v in config.variables if key in v.name):
                        btn = (
                            ui.button(var.display_name, icon=icon)
                            .props("flat unelevated no-caps stack")
                            .classes("neu-btn")
                        )
                        plc_buttons.append(btn)
                        if mode == "toggle":
                            toggle_buttons[var.name] = btn
                            btn.on_click(lambda _e, n=var.name: toggle(n))
                        else:
                            btn.on("pointerdown", lambda _e, n=var.name: press(n))
                            for ev in ("pointerup", "pointerleave", "pointercancel"):
                                btn.on(ev, lambda _e, n=var.name: release(n))

    ui.timer(2.0, refresh_status)


app.on_shutdown(plc.close)


if __name__ in {"__main__", "__mp_main__"}:  # guard required when packaged as .exe
    ui.run(title="Roll magazine control", port=8080, reload=True, favicon="./asset/Detective.ico")