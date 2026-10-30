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
  --btn-w: 84px; --btn-h: 84px; --radius: 20px; --gap-x: 18px; --gap-y: 24px;
  --ink: #ffffff; --ink-dim: rgba(255,255,255,.62);
  --ok: #4ade80; --bad: #f87171;
}
html, body { min-height: 100vh; }
body {
  color: var(--ink); font-family: 'Segoe UI', system-ui, sans-serif;
  background: radial-gradient(120% 90% at 50% 0%, #353a47 0%, #262a33 55%, #1d2027 100%) fixed;
}

/* ---- panel: dark slate card ---- */
.glass-panel {
  background: linear-gradient(145deg, #323744, #292d37);
  border: 1px solid rgba(255,255,255,.07); border-radius: 30px; padding: 28px;
  width: fit-content; max-width: 100%;
  box-shadow: 0 28px 60px rgba(0,0,0,.50), inset 1px 1px 0 rgba(255,255,255,.08);
}
.glass-sub { color: var(--ink-dim); letter-spacing: .02em; }

/* ---- buttons: dark smoked glass with glinting rim (selectors beat Quasar's defaults) ---- */
.q-btn.glass-btn {
  position: relative; overflow: visible;
  background: linear-gradient(145deg, rgba(255,255,255,.20) 0%, rgba(255,255,255,.07) 50%, rgba(255,255,255,.12) 100%) !important;
  color: var(--ink) !important;
  -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px);
  border: none !important; border-radius: var(--radius) !important;
  width: var(--btn-w) !important; height: var(--btn-h); min-width: 0 !important; min-height: var(--btn-h);
  padding: 0 !important;
  font-size: 1rem; font-weight: 700; text-shadow: 0 1px 2px rgba(0,0,0,.45);
  box-shadow:
    0 12px 20px -4px rgba(0,0,0,.55),              /* soft drop shadow */
    -3px -3px 8px rgba(255,255,255,.035),          /* faint top-left lift */
    inset 0 0 12px rgba(255,255,255,.07) !important;
  transition: background .15s ease, box-shadow .15s ease, transform .12s ease;
  touch-action: manipulation; user-select: none; -webkit-user-select: none;
}
/* rim: thin edge that glints at the top-right and bottom-left (drawn with a masked gradient) */
.q-btn.glass-btn::before {
  content: ""; position: absolute; inset: 0; border-radius: inherit; padding: 1.5px;
  box-sizing: border-box; box-shadow: none !important; pointer-events: none;
  background: linear-gradient(45deg,
    rgba(255,255,255,.80) 0%, rgba(255,255,255,.14) 30%,
    rgba(255,255,255,.10) 70%, rgba(255,255,255,.70) 100%);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask: linear-gradient(#000 0 0) content-box exclude, linear-gradient(#000 0 0);
  mask-composite: exclude;
}
/* soft sheen on the upper part */
.q-btn.glass-btn::after {
  content: ""; position: absolute; top: 3%; left: 4%; width: 92%; height: 46%;
  border-radius: calc(var(--radius) - 3px) calc(var(--radius) - 3px) 60% 60% / calc(var(--radius) - 3px) calc(var(--radius) - 3px) 35% 35%;
  pointer-events: none;
  background: linear-gradient(to bottom, rgba(255,255,255,.14), rgba(255,255,255,0));
}
.q-btn.glass-btn .q-btn__content { color: var(--ink) !important; position: relative; z-index: 1; }
.q-btn.glass-btn .q-icon { font-size: 1.5rem; margin-bottom: 2px; color: #ffffff !important; text-shadow: none; }

@media (hover: hover) {
  .q-btn.glass-btn:hover { transform: translateY(-2px);
    background: linear-gradient(145deg, rgba(255,255,255,.28) 0%, rgba(255,255,255,.10) 50%, rgba(255,255,255,.17) 100%) !important; }
}
.q-btn.glass-btn:active {
  transform: scale(.95);
  box-shadow: 0 4px 8px -2px rgba(0,0,0,.55), inset 3px 4px 10px rgba(0,0,0,.45) !important;
}
.q-btn.glass-btn:active::after { opacity: .4; }
.q-btn.glass-btn.is-on {              /* toggle ON: green-tinted glass + glowing rim, icon stays white */
  background: linear-gradient(145deg, rgba(74,222,128,.42) 0%, rgba(74,222,128,.16) 55%, rgba(74,222,128,.28) 100%) !important;
  box-shadow: 0 0 22px rgba(74,222,128,.50), 0 12px 20px -4px rgba(0,0,0,.50),
              inset 0 0 12px rgba(74,222,128,.25) !important;
}
.q-btn.glass-btn.is-on::before {
  background: linear-gradient(45deg, rgba(187,247,208,.95) 0%, rgba(74,222,128,.45) 30%,
                                     rgba(74,222,128,.40) 70%, rgba(187,247,208,.90) 100%);
}
.q-btn.glass-btn:focus-visible { outline: 2px solid #ffffff; outline-offset: 4px; }
.q-btn.glass-btn .q-focus-helper { display: none; }
/* offline: dimmer but still readable */
.q-btn.glass-btn.disabled, .q-btn.glass-btn[disabled] { opacity: .62 !important; cursor: not-allowed !important; }

/* ---- connect button: same glass, wide rounded rectangle ---- */
.q-btn.glass-btn.glass-connect {
  height: 54px; min-height: 54px; min-width: 170px !important; width: auto !important;
  padding: 0 24px !important; border-radius: 18px !important;
}

.q-btn.glass-btn.glass-connect::after { border-radius: 15px 15px 50% 50% / 15px 15px 30% 30%; }  /* normal glass sheen */

/* Rotating rainbow ring + neon glow: ONLY while connected to the PLC (class .is-connected).
   --ring-angle is animated through @property (Chrome/Edge, Safari 16.4+, Firefox 128+);
   older browsers simply show the ring without rotation. */
@property --ring-angle { syntax: "<angle>"; initial-value: 0deg; inherits: false; }
@keyframes ring-spin { to { --ring-angle: 360deg; } }
.q-btn.glass-btn.glass-connect.is-connected::before,
.q-btn.glass-btn.glass-connect.is-connected::after {
  --ring: conic-gradient(from var(--ring-angle),
    #ff7a18, #ffd200, #3df27a, #00e0ff, #3df27a, #ffd200, #ff7a18);
  background: var(--ring);
  animation: ring-spin 4s linear infinite;
}
.q-btn.glass-btn.glass-connect.is-connected::before { padding: 2px; }          /* crisp 2px ring */
.q-btn.glass-btn.glass-connect.is-connected::after {                           /* blurred copy = glow */
  top: -2px; left: -2px; width: calc(100% + 4px); height: calc(100% + 4px);
  border-radius: 20px; box-sizing: border-box; padding: 4px; opacity: .95; filter: blur(9px);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask: linear-gradient(#000 0 0) content-box exclude, linear-gradient(#000 0 0);
  mask-composite: exclude;
}
.q-btn.glass-btn.glass-connect.is-connected:active::after { opacity: .7; }

.glass-connect .q-icon { font-size: 1.2rem; margin: 0 8px 0 0; }

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
  .q-btn.glass-btn.glass-connect.is-connected::before, .q-btn.glass-btn.glass-connect.is-connected::after { animation: none; }
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
        if ok:
            connect_btn.classes(add="is-connected")      # rotating glowing ring on
        else:
            connect_btn.classes(remove="is-connected")   # back to plain glass
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
    ui.run(title="Roll magazine control", port=8080, reload=True)