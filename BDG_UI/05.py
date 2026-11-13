"""NiceGUI front-end (glassmorphism): header + Clamp toggles + Park hold-buttons.

Backend: TwinCAT PLC over ADS (see ads_client.py).
Config.json must be in the same folder as the .exe (or as this script when run with uv).

How the page works
------------------
* ``ROWS`` describes the button groups. Each group collects the PLC variables
  whose name contains ``RowSpec.key`` and renders one button per variable.
* "toggle" buttons switch a PLC bool on/off. Their state is *mirrored from the
  PLC* every poll cycle, so the UI can never show a wrong state.
* "hold" buttons write TRUE on pointer-down and FALSE on release.
* All PLC access goes through ``AdsClient``'s ``*_async`` methods, which run on
  one worker thread. That keeps the UI responsive and guarantees write order.
"""
from __future__ import annotations

import base64
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Awaitable, NamedTuple

from nicegui import app, ui

from ads_client import AdsClient, AdsConfig, AdsError

logging.basicConfig(level=logging.INFO)

POLL_INTERVAL_S = 2.0   # how often every open browser page checks the PLC
NOTIFY_MS = 4000        # how long error pop-ups stay visible


# --------------------------------------------------------------------------- config
def app_dir() -> Path:
    """Folder of the .exe when packaged (PyInstaller / nicegui-pack), else of this script."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


CONFIG_PATH = app_dir() / "Config.json"

# Fail fast with a readable message instead of a traceback.
try:
    config = AdsConfig.from_file(CONFIG_PATH)
except FileNotFoundError:
    sys.exit(f"Config.json not found. Place it in the same folder as the program:\n  {CONFIG_PATH}")
except (ValueError, KeyError) as exc:
    sys.exit(f"Config.json is invalid ({CONFIG_PATH}): {exc!r}")

plc = AdsClient(config)


class RowSpec(NamedTuple):
    """One group of buttons on the page."""
    key: str      # text searched for in the PLC variable name (display_name is only a number)
    title: str    # row heading
    icon: str     # Material icon name, or an "img:..." string for a custom icon (see svg_icon)
    mode: str     # "toggle": click = switch on/off and stay (state mirrored from the PLC)
                  # "hold"  : TRUE while the button is held, FALSE on release
    prefix: str   # short word used in log lines, e.g. "Clamp 3"


# --------------------------------------------------------------------------- custom icons
def svg_icon(svg: str) -> str:
    """Turn SVG markup into a value usable as ``icon=`` (Quasar's ``img:`` icon type).

    The SVG is embedded as a base64 data URI, so no extra file has to ship next to
    the .exe. Note: an SVG used this way is drawn like a picture, so it cannot
    inherit the button's text colour -> the colour is written into the SVG itself.
    """
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"img:data:image/svg+xml;base64,{encoded}"


# Roller clamp: two rollers (outer ring + inner hub) pressing on a vertical web/strip.
# White strokes to match the other icons on the dark glass buttons.
# The viewBox is slightly larger than the drawing (-5..105) so the round stroke ends aren't clipped.
ROLLER_CLAMP_ICON = svg_icon(
    """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="-5 -5 110 110"
         fill="none" stroke="#ffffff" stroke-width="7" stroke-linecap="round">
      <circle cx="24" cy="50" r="24"/>   <!-- left roller: outer ring -->
      <circle cx="24" cy="50" r="11"/>   <!-- left roller: hub -->
      <circle cx="76" cy="50" r="24"/>   <!-- right roller: outer ring -->
      <circle cx="76" cy="50" r="11"/>   <!-- right roller: hub -->
      <line x1="50" y1="0" x2="50" y2="100"/>   <!-- strip between the rollers -->
    </svg>
    """
)

ROWS = (
    RowSpec("stManuellClamping", "Flat Clamping", "compress", "toggle", "FlatClamp"),
    RowSpec("stFeedRollerClamping", "Roller Clamping", ROLLER_CLAMP_ICON, "toggle", "RollerClamp"),
    RowSpec("stGoToParkPos", "Go to park position", "local_parking", "hold", "Park"),
)

# --------------------------------------------------------------------------- style
CSS = r"""
:root {
  --btn-w: 84px; --btn-h: 50px; --radius: 10px; --gap-x: 18px; --gap-y: 24px;
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
  font-size: 1.2rem; font-weight: 700; text-shadow: 0 1px 2px rgba(0,0,0,.45);
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

/* ---- master "clamp all" button: compact wide glass button ---- */
.q-btn.glass-btn.glass-wide {
  height: 44px; min-height: 44px; min-width: 150px !important; width: auto !important;
  padding: 0 20px !important; border-radius: 16px !important;
}
.q-btn.glass-btn.glass-wide::after { border-radius: 13px 13px 50% 50% / 13px 13px 30% 30%; }
.glass-wide .q-icon { font-size: 1.2rem; margin: 0 8px 0 0; }

/* ---- grid ---- */
.glass-grid { display: grid; grid-template-columns: repeat(12, var(--btn-w)); gap: var(--gap-y) var(--gap-x);
  justify-content: start; width: 100%; }
@media (max-width: 1250px) { .glass-grid { grid-template-columns: repeat(8, var(--btn-w)); } }
@media (max-width: 900px)  { .glass-grid { grid-template-columns: repeat(6, var(--btn-w)); } }
@media (max-width: 600px)  { .glass-grid { grid-template-columns: repeat(3, var(--btn-w)); justify-content: center; } }

/* ---- log panel ---- */
.nicegui-log.glass-log {
  height: 170px; padding: 10px 14px !important; border-radius: 16px !important;
  background: rgba(0,0,0,.30) !important; color: rgba(255,255,255,.88) !important;
  border: 1px solid rgba(255,255,255,.08) !important;
  box-shadow: inset 0 2px 8px rgba(0,0,0,.40);
  font-family: Consolas, 'Cascadia Mono', monospace; font-size: .85rem; line-height: 1.5;
}

/* ---- status ---- */
.status-dot { width: 14px; height: 14px; border-radius: 50%; background: var(--bad);
  box-shadow: 0 0 10px var(--bad), inset 0 1px 1px rgba(255,255,255,.5); }

@media (prefers-reduced-motion: reduce) {
  .q-btn.glass-btn.glass-connect.is-connected::before, .q-btn.glass-btn.glass-connect.is-connected::after { animation: none; }
  .q-btn.glass-btn { transition: none; }
  .q-btn.glass-btn:hover { transform: none; }
}
"""

LOG_CLASSES = {"info": "text-grey-4", "ok": "text-green-4", "warn": "text-orange-4", "error": "text-red-4"}


# --------------------------------------------------------------------------- small helpers
def glass_button(text: str, icon: str, *, stack: bool = False) -> ui.button:
    """Glass-styled button. color=None removes Quasar's default blue text colour."""
    props = "flat unelevated no-caps" + (" stack" if stack else "")
    return ui.button(text, icon=icon, color=None).props(props).classes("glass-btn")


def set_class(element: ui.element, css_class: str, enabled: bool) -> None:
    """Add or remove one CSS class depending on ``enabled``."""
    if enabled:
        element.classes(add=css_class)
    else:
        element.classes(remove=css_class)


# --------------------------------------------------------------------------- page
class ControlPanel:
    """One instance per open browser page: builds the UI and owns its state."""

    def __init__(self) -> None:
        # ---- state (all per browser page) ----
        self.pressed: set[str] = set()                  # hold-type variables this browser holds TRUE
        self.plc_buttons: list[ui.button] = []          # every PLC button (enabled only while online)
        self.toggle_buttons: dict[str, ui.button] = {}  # PLC variable name -> toggle button
        self.toggle_state: dict[str, bool] = {}         # last known PLC value of each toggle
        self.labels: dict[str, str] = {}                # PLC variable name -> log label ("Clamp 3")
        self.master_btn: ui.button | None = None        # "Clamp all / Release all"
        self.online: bool | None = None                 # last seen link state; None = not checked yet

        self._build_layout()

        # Browser closed / link lost while holding a button -> release it.
        # (Affects hold buttons only; toggles keep their state in the PLC.)
        ui.context.client.on_disconnect(self.release_all)

        ui.timer(0.1, self.refresh_status, once=True)   # first status check right away ...
        ui.timer(POLL_INTERVAL_S, self.refresh_status)  # ... then keep polling
        self.log("Application ready. Press Connect to start ADS communication.")

    # ---- layout -------------------------------------------------------------
    def _build_layout(self) -> None:
        with ui.column().classes("w-full items-center"):
            with ui.element("div").classes("glass-panel"):
                self._build_header()
                for spec in ROWS:
                    self._build_row(spec)
                self._build_log_panel()

    def _build_header(self) -> None:
        """Top row: connect button on the left, status dot + text on the right."""
        with ui.row().classes("w-full items-center justify-between q-mb-lg"):
            self.connect_btn = glass_button("Connect", "power").classes("glass-connect")
            self.connect_btn.on_click(self.toggle_connection)
            with ui.row().classes("items-center gap-2"):
                self.dot = ui.element("div").classes("status-dot")
                self.status = ui.label("Checking…")

    def _build_row(self, spec: RowSpec) -> None:
        """Heading (+ 'Clamp all' for toggle rows) and one button per matching PLC variable."""
        with ui.row().classes("w-full items-center justify-between q-mt-md q-mb-sm"):
            ui.label(spec.title).classes("text-subtitle1 text-weight-medium glass-sub")
            if spec.mode == "toggle":
                self.master_btn = glass_button("Clamp all", "lock").classes("glass-wide")
                self.master_btn.on_click(self.toggle_all)
                self.plc_buttons.append(self.master_btn)

        with ui.element("div").classes("glass-grid"):
            for var in (v for v in config.variables if spec.key in v.name):
                btn = glass_button(var.display_name, spec.icon, stack=False)
                self.labels[var.name] = f"{spec.prefix} {var.display_name}"
                self.plc_buttons.append(btn)

                if spec.mode == "toggle":
                    self.toggle_buttons[var.name] = btn
                    btn.on_click(lambda _e, n=var.name: self.toggle(n))
                else:
                    # Several events can end a press (finger slides off, touch cancelled, ...);
                    # release() ignores the duplicates.
                    btn.on("pointerdown", lambda _e, n=var.name: self.press(n))
                    for event in ("pointerup", "pointerleave", "pointercancel"):
                        btn.on(event, lambda _e, n=var.name: self.release(n))

    def _build_log_panel(self) -> None:
        with ui.row().classes("w-full items-center justify-between q-mt-lg q-mb-sm"):
            ui.label("Log").classes("text-subtitle1 text-weight-medium glass-sub")
            clear_btn = glass_button("Clear", "delete_sweep").classes("glass-wide")
            clear_btn.on_click(lambda: self.log_el.clear())
        self.log_el = ui.log(max_lines=300).classes("glass-log w-full")

    # ---- logging / error reporting -----------------------------------------
    def log(self, text: str, level: str = "info") -> None:
        """Append a time-stamped, colour-coded line to the log panel."""
        line = f"{datetime.now():%H:%M:%S}  {text}"
        try:
            self.log_el.push(line, classes=LOG_CLASSES.get(level, ""))
        except TypeError:  # older NiceGUI without the classes argument
            self.log_el.push(line)

    def report_error(self, exc: Exception, label: str = "", timeout: int = NOTIFY_MS) -> None:
        """Show an error pop-up AND write it to the log."""
        ui.notify(str(exc), type="negative", position="top", timeout=timeout)
        self.log(f"{label}: {exc}" if label else str(exc), "error")

    async def attempt(self, label: str, action: Awaitable[None]) -> bool:
        """Await a PLC action; on AdsError report it and return False, else True."""
        try:
            await action
        except AdsError as exc:
            self.report_error(exc, label)
            return False
        return True

    # ---- hold buttons -------------------------------------------------------
    async def press(self, name: str) -> None:
        # Register BEFORE awaiting: if the pointer-up arrives while the write is still
        # in flight, release() must see the button as held, otherwise the PLC would stay TRUE.
        # The ADS worker thread is FIFO, so TRUE is always written before FALSE.
        self.pressed.add(name)
        if await self.attempt(self.labels[name], plc.write_async(name, True)):
            self.log(f"{self.labels[name]} pressed")
        else:
            self.pressed.discard(name)  # nothing was written, so there is nothing to release

    async def release(self, name: str) -> None:
        if name not in self.pressed:  # ignore duplicate up/leave/cancel events
            return
        self.pressed.discard(name)
        if await self.attempt(self.labels[name], plc.write_async(name, False)):
            self.log(f"{self.labels[name]} released")

    async def release_all(self) -> None:
        """Release every held button with ONE batched ADS write."""
        names = list(self.pressed)
        if not names:
            return
        self.pressed.clear()
        if await self.attempt("Release", plc.write_many_async({n: False for n in names})):
            self.log(f"Released {len(names)} held button(s)")

    # ---- toggle buttons -----------------------------------------------------
    @property
    def all_clamped(self) -> bool:
        return bool(self.toggle_buttons) and all(self.toggle_state.get(n, False) for n in self.toggle_buttons)

    def apply_states(self, states: dict[str, bool]) -> None:
        """Show PLC values on the toggle buttons. Only touches the UI for values that changed."""
        changed = False
        for name, on in states.items():
            if self.toggle_state.get(name) != on:
                self.toggle_state[name] = on
                set_class(self.toggle_buttons[name], "is-on", on)
                changed = True
        if changed:
            self.update_master()

    def update_master(self) -> None:
        """Master button shows 'Release all' (green) when every clamp is on, else 'Clamp all'."""
        if self.master_btn is None:
            return
        all_on = self.all_clamped
        self.master_btn.set_text("Release all" if all_on else "Clamp all")
        set_class(self.master_btn, "is-on", all_on)

    async def toggle(self, name: str) -> None:
        new = not self.toggle_state.get(name, False)
        if await self.attempt(self.labels[name], plc.write_async(name, new)):
            self.apply_states({name: new})
            self.log(f"{self.labels[name]} -> {'ON' if new else 'OFF'}", "ok" if new else "info")

    async def toggle_all(self) -> None:
        """Not all clamps on -> switch ALL on.  All clamps on -> switch ALL off."""
        target = not self.all_clamped
        states = {name: target for name in self.toggle_buttons}
        if await self.attempt("Clamp all", plc.write_many_async(states)):  # one ADS round-trip
            self.apply_states(states)
            self.log(f"All {len(states)} clamps -> {'ON' if target else 'OFF'}", "ok" if target else "info")

    # ---- connection / status ------------------------------------------------
    async def poll_plc(self) -> tuple[bool, dict[str, bool]]:
        """Return (link is alive, current toggle values).

        When toggles exist ONE batched read answers both questions, so a poll
        costs a single ADS round-trip. A failed read means the link is down.
        """
        if not self.toggle_buttons:
            return await plc.connected_async(), {}
        try:
            values = await plc.read_many_async(list(self.toggle_buttons))
        except AdsError:
            return False, {}
        return True, {name: bool(value) for name, value in values.items()}

    async def refresh_status(self) -> None:
        online, values = await self.poll_plc()

        if online != self.online:  # connection widgets only change when the state flips
            self.set_online(online)

        # Offline -> show every toggle as OFF; online -> mirror the real PLC values.
        self.apply_states(values if online else {name: False for name in self.toggle_buttons})

    def set_online(self, online: bool) -> None:
        """Update every widget that depends on the link state."""
        if self.online is not None or online:  # don't log "offline" at start-up
            self.log("PLC online" if online else "PLC offline", "ok" if online else "warn")
        self.online = online

        colour = "var(--ok)" if online else "var(--bad)"
        self.dot.style(f"background: {colour}; box-shadow: 0 0 10px {colour}, inset 0 1px 1px rgba(255,255,255,.5)")
        self.status.set_text(f"PLC connected ({config.ams_id}:{config.port})" if online else "PLC offline")
        self.connect_btn.set_text("Disconnect" if online else "Connect")
        set_class(self.connect_btn, "is-connected", online)  # rotating glowing ring
        for btn in self.plc_buttons:
            btn.set_enabled(online)

    async def toggle_connection(self) -> None:
        self.connect_btn.disable()  # no double clicks while connecting
        try:
            if await plc.connected_async():
                self.log("Disconnecting from PLC...")
                await self.release_all()  # never leave a hold button TRUE in the PLC
                await plc.disconnect_async()
                ui.notify("Disconnected from PLC", type="info", position="top")
            else:
                self.log(f"Connecting to {config.ams_id}:{config.port} ...")
                await plc.connect_async()
                ui.notify("Connected to PLC", type="positive", position="top")
        except AdsError as exc:
            self.report_error(exc, timeout=5000)
        finally:
            self.connect_btn.enable()
            await self.refresh_status()


@ui.page("/")
def index() -> None:
    ui.add_css(CSS)
    ui.query("body").classes("q-pa-md")
    ControlPanel()


app.on_shutdown(plc.close)  # close the link and stop the ADS worker thread

if __name__ in {"__main__", "__mp_main__"}:  # guard required when packaged as .exe
    ui.run(title="Roll magazine control", port=8080, reload=True, native=True, favicon="./asset/Detective.ico", fullscreen=False)