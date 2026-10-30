"""NiceGUI front-end (glassmorphism): header + 24 Clamp toggles + 24 Park hold-buttons.

Backend: TwinCAT PLC over ADS (see ads_client.py).
Config.json must be in the same folder as the .exe (or as this script when run with uv).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from nicegui import app, ui

from ads_client import AdsClient, AdsConfig, AdsError

logging.basicConfig(level=logging.INFO)


# --------------------------------------------------------------------------- config
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
#   mode "toggle": click = switch on/off and stay (state is mirrored from the PLC)
#   mode "hold"  : TRUE while the button is held, FALSE on release
# display_name is just a number, so rows are grouped by the PLC variable name.
ROWS = [
    ("stManuellClamping", "Clamping", "compress", "toggle"),
    ("stGoToParkPos", "Go to park position", "local_parking", "hold"),
]

# --------------------------------------------------------------------------- style
CSS = r"""
:root {
  --btn-w: 84px; --btn-h: 84px; --gap-x: 18px; --gap-y: 24px;
  --ink: #ffffff; --ink-dim: rgba(255,255,255,.72);
  --ok: #4ade80; --bad: #f87171;
  --tint: rgba(10,14,28,.55);          /* dark tint keeps contrast equal everywhere */
}
html, body { min-height: 100vh; }
body {
  background: #090d1a; color: var(--ink);
  font-family: 'Segoe UI', system-ui, sans-serif;
}
/* soft, dim colour glows in the corners only - the centre stays dark and calm */
body::before {
  content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background:
    radial-gradient(60% 55% at 8% 10%,  rgba(124,58,237,.50), transparent 70%),
    radial-gradient(55% 50% at 94% 8%,  rgba(14,165,233,.38), transparent 70%),
    radial-gradient(60% 55% at 92% 95%, rgba(219,39,119,.34), transparent 70%),
    radial-gradient(55% 50% at 6% 94%,  rgba(37,99,235,.40),  transparent 70%);
}

/* ---- panel ---- */
.glass-panel {
  background: linear-gradient(135deg, rgba(255,255,255,.12), rgba(255,255,255,.03)), var(--tint);
  -webkit-backdrop-filter: blur(24px) saturate(150%); backdrop-filter: blur(24px) saturate(150%);
  border: 1px solid rgba(255,255,255,.28); border-radius: 28px; padding: 28px;
  width: fit-content; max-width: 100%;
  box-shadow: 0 24px 60px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.40);
}
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .glass-panel { background: rgba(22,28,52,.95); }
}
.glass-sub { color: var(--ink-dim); letter-spacing: .02em; }

/* ---- buttons: round glass "bubbles" (selectors use .q-btn.glass-btn to beat Quasar defaults) ---- */
.q-btn.glass-btn {
  position: relative; overflow: visible;
  /* clear centre, slightly brighter edge = glass volume */
  background:
    radial-gradient(circle at 50% 45%, rgba(255,255,255,.05) 0%, rgba(255,255,255,.09) 55%, rgba(255,255,255,.22) 100%) !important;
  color: var(--ink) !important;
  -webkit-backdrop-filter: blur(10px) saturate(140%); backdrop-filter: blur(10px) saturate(140%);
  border: 1.5px solid rgba(255,255,255,.50) !important; border-radius: 50% !important;
  width: var(--btn-w) !important; height: var(--btn-h); min-width: 0 !important; min-height: var(--btn-h);
  padding: 0 !important;
  font-size: 1rem; font-weight: 700; text-shadow: 0 1px 2px rgba(0,0,0,.55);
  box-shadow:
    inset 2px 3px 3px -1px rgba(255,255,255,.85),    /* bright rim, top-left */
    inset -2px -3px 3px -1px rgba(255,255,255,.45),  /* softer rim, bottom-right */
    inset 0 0 14px rgba(255,255,255,.14),            /* inner glow */
    0 14px 22px -4px rgba(0,0,0,.42),                /* soft drop shadow underneath */
    0 2px 5px rgba(0,0,0,.25) !important;
  transition: background .15s ease, box-shadow .15s ease, transform .12s ease, border-color .15s ease;
  touch-action: manipulation; user-select: none; -webkit-user-select: none;
}
.q-btn.glass-btn::before { box-shadow: none !important; }   /* remove Quasar's own shadow layer */
/* specular highlight (the curved gloss on the upper half) */
.q-btn.glass-btn::after {
  content: ""; position: absolute; top: 5%; left: 14%; width: 72%; height: 42%;
  border-radius: 50%; pointer-events: none;
  background: linear-gradient(to bottom, rgba(255,255,255,.34), rgba(255,255,255,0));
}
.q-btn.glass-btn .q-btn__content { color: var(--ink) !important; position: relative; z-index: 1; }
.q-btn.glass-btn .q-icon {
  font-size: 1.5rem; margin-bottom: 2px; color: var(--ok) !important;
  filter: drop-shadow(0 0 4px rgba(74,222,128,.55)); text-shadow: none;
}
@media (hover: hover) {
  .q-btn.glass-btn:hover { transform: translateY(-2px);
    background: radial-gradient(circle at 50% 45%, rgba(255,255,255,.10) 0%, rgba(255,255,255,.15) 55%, rgba(255,255,255,.30) 100%) !important; }
}
.q-btn.glass-btn:active {
  transform: scale(.95);
  box-shadow:
    inset 3px 4px 8px rgba(0,0,0,.40), inset -2px -3px 4px -1px rgba(255,255,255,.35),
    0 4px 8px -2px rgba(0,0,0,.40) !important;
}
.q-btn.glass-btn:active::after { opacity: .5; }
.q-btn.glass-btn.is-on {              /* toggle ON: green glass, glowing rim, white label */
  background: radial-gradient(circle at 50% 45%, rgba(74,222,128,.14) 0%, rgba(74,222,128,.26) 60%, rgba(74,222,128,.45) 100%) !important;
  border-color: rgba(134,239,172,.95) !important;
  box-shadow:
    inset 2px 3px 3px -1px rgba(255,255,255,.85), inset -2px -3px 3px -1px rgba(255,255,255,.45),
    0 0 22px rgba(74,222,128,.60), 0 12px 20px -4px rgba(0,0,0,.40) !important;
}
.q-btn.glass-btn:focus-visible { outline: 2px solid #ffffff; outline-offset: 4px; }
.q-btn.glass-btn .q-focus-helper { display: none; }
/* offline: dimmer but still readable */
.q-btn.glass-btn.disabled, .q-btn.glass-btn[disabled] { opacity: .62 !important; cursor: not-allowed !important; }

/* ---- connect button: same glass, pill shape ---- */
.q-btn.glass-btn.glass-connect {
  height: 54px; min-height: 54px; min-width: 160px !important; width: auto !important;
  padding: 0 22px !important; border-radius: 999px !important;
}
.q-btn.glass-btn.glass-connect::after { border-radius: 999px; top: 6%; left: 6%; width: 88%; height: 46%; }
.glass-connect .q-icon { font-size: 1.2rem; margin: 0 6px 0 0; }

/* ---- grid ---- */
.glass-grid { display: grid; grid-template-columns: repeat(12, var(--btn-w)); gap: var(--gap-y) var(--gap-x);
  justify-content: start; width: 100%; }
@media (max-width: 1250px) { .glass-grid { grid-template-columns: repeat(8, var(--btn-w)); } }
@media (max-width: 900px)  { .glass-grid { grid-template-columns: repeat(6, var(--btn-w)); } }
@media (max-width: 600px)  { .glass-grid { grid-template-columns: repeat(3, var(--btn-w)); justify-content: center; } }

/* ---- status ---- */
.status-dot { width: 14px; height: 14px; border-radius: 50%; background: var(--bad);
  box-shadow: 0 0 10px var(--bad), inset 0 1px 1px rgba(255,255,255,.5); }

@media (prefers-reduced-motion: reduce) {
  .q-btn.glass-btn { transition: none; }
  .q-btn.glass-btn:hover { transform: none; }
}
"""


def glass_button(text: str, icon: str, *, stack: bool = False) -> ui.button:
    """Glass-styled button. color=None removes Quasar's default blue text colour."""
    props = "flat unelevated no-caps" + (" stack" if stack else "")
    return ui.button(text, icon=icon, color=None).props(props).classes("glass-btn")


# --------------------------------------------------------------------------- page
@ui.page("/")
async def index() -> None:
    ui.add_css(CSS)
    ui.query("body").classes("q-pa-md")

    pressed: set[str] = set()                    # hold-type variables this browser currently holds TRUE
    plc_buttons: list[ui.button] = []            # every PLC button (enabled only while connected)
    toggle_buttons: dict[str, ui.button] = {}    # PLC variable name -> toggle button
    toggle_state: dict[str, bool] = {}           # last known PLC value

    # ---- hold buttons -------------------------------------------------------
    async def write(name: str, value: bool) -> None:
        try:
            await plc.write_async(name, value)
        except AdsError as exc:
            ui.notify(str(exc), type="negative", position="top", timeout=4000)

    async def press(var_name: str) -> None:
        pressed.add(var_name)
        await write(var_name, True)

    async def release(var_name: str) -> None:
        if var_name in pressed:                  # ignore duplicate up/leave/cancel events
            pressed.discard(var_name)
            await write(var_name, False)

    async def release_all() -> None:             # browser closed / link lost while holding a button
        for name in list(pressed):
            await release(name)

    ui.context.client.on_disconnect(release_all)  # affects hold buttons only; toggles keep their state

    # ---- toggle buttons -----------------------------------------------------
    def show_state(name: str, on: bool) -> None:
        toggle_state[name] = on
        btn = toggle_buttons[name]
        if on:
            btn.classes(add="is-on")
        else:
            btn.classes(remove="is-on")

    async def toggle(name: str) -> None:
        new = not toggle_state.get(name, False)
        try:
            await plc.write_async(name, new)
        except AdsError as exc:
            ui.notify(str(exc), type="negative", position="top", timeout=4000)
            return
        show_state(name, new)

    # ---- connection / status ------------------------------------------------
    async def refresh_status() -> None:
        ok = await plc.connected_async()
        colour = "var(--ok)" if ok else "var(--bad)"
        dot.style(f"background: {colour}; box-shadow: 0 0 10px {colour}, inset 0 1px 1px rgba(255,255,255,.5)")
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

    # ---- layout -------------------------------------------------------------
    with ui.column().classes("w-full items-center"):
        with ui.element("div").classes("glass-panel"):
            # Row 1: title | connect button | PLC status
            with ui.row().classes("w-full items-center justify-between q-mb-lg"):
                ui.label("Roll magazine control").classes("text-h5 text-weight-bold")
                connect_btn = glass_button("Connect", "power").classes("glass-connect")
                connect_btn.on_click(toggle_connection)
                with ui.row().classes("items-center gap-2"):
                    dot = ui.element("div").classes("status-dot")
                    status = ui.label("Checking…")

            # Rows 2 and 3: one button grid per PLC variable group
            for key, title, icon, mode in ROWS:
                ui.label(title).classes("text-subtitle1 text-weight-medium q-mt-md q-mb-sm glass-sub")
                with ui.element("div").classes("glass-grid"):
                    for var in (v for v in config.variables if key in v.name):
                        btn = glass_button(var.display_name, icon, stack=True)
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
    ui.run(title="Roll magazine control", port=8080, reload=False, show=False)