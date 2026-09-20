"""Mod Organizer 2 Python plugin lifecycle and GUI-thread controller loop."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from .input_state import ControllerMapping, InputAction, InputProcessor
from .ui_bridge import StrictMo2UiBridge, UiBridgeUnavailable
from .xinput import XInputBackend, XInputState

try:
    import mobase  # type: ignore
except ImportError:
    class _IPlugin:
        def __init__(self) -> None: pass

    class _VersionInfo:
        def __init__(self, *args: Any) -> None: self.args = args

    class _Setting:
        def __init__(self, key: str, description: str, default: Any) -> None:
            self.key, self.description, self.default = key, description, default

    class _Mobase:
        IPlugin = _IPlugin
        VersionInfo = _VersionInfo
        PluginSetting = _Setting
        ReleaseType = type("ReleaseType", (), {"FINAL": 0})

    mobase = _Mobase()  # type: ignore


LOGGER = logging.getLogger("MO2-XInput-Controller")
PLUGIN_NAME = "XInput Controller Support"


class XInputControllerPlugin(mobase.IPlugin):
    """Always-on MO2 service; all reads and UI mutations happen on Qt's GUI thread."""

    def __init__(self) -> None:
        super().__init__()
        self._organizer: Any = None
        self._window: Any = None
        self._bridge: Optional[StrictMo2UiBridge] = None
        self._timer: Any = None
        self._backend: Optional[XInputBackend] = None
        self._processor = InputProcessor()
        self._active_controller: Optional[int] = None
        self._last_controller: Optional[int] = None
        self._next_auto_scan = 0.0
        self._reconnect_interval = 1.0
        self._was_connected = False
        self._ready_latched = False
        self._last_error: Optional[str] = None
        self._plugin_enabled = True

    def name(self) -> str:
        return PLUGIN_NAME

    def localizedName(self) -> str:
        return PLUGIN_NAME

    def author(self) -> str:
        return "KylerNyhagen / KylerN45"

    def description(self) -> str:
        return "Map XInput controllers to MO2's executable selector and Run button."

    def version(self) -> Any:
        release = getattr(getattr(mobase, "ReleaseType", None), "FINAL", 0)
        return mobase.VersionInfo(0, 1, 0, release)

    def settings(self) -> list[Any]:
        return [
            mobase.PluginSetting("controller_index", "Controller index (-1 = automatic, 0-3 = fixed)", -1),
            mobase.PluginSetting("run_buttons", "Comma-separated controls for Run", "A"),
            mobase.PluginSetting("next_tool_buttons", "Comma-separated controls for next executable", "DPadDown,DPadRight,RB"),
            mobase.PluginSetting("previous_tool_buttons", "Comma-separated controls for previous executable", "DPadUp,DPadLeft,LB"),
            mobase.PluginSetting("repeat_delay_ms", "Milliseconds before held navigation repeats", 350),
            mobase.PluginSetting("repeat_interval_ms", "Milliseconds between held navigation repeats", 120),
            mobase.PluginSetting("left_stick_deadzone", "Left-stick activation threshold (0-32767)", 7849),
            mobase.PluginSetting("poll_interval_ms", "GUI polling interval in milliseconds", 30),
            mobase.PluginSetting("reconnect_interval_ms", "Disconnected-controller scan interval in milliseconds", 1000),
            mobase.PluginSetting("wrap_selection", "Wrap executable selection at the ends", True),
            mobase.PluginSetting("left_stick_navigation", "Enable left-stick up/down executable navigation", True),
        ]

    def isActive(self) -> bool:
        return self._plugin_enabled

    def init(self, organizer: Any) -> bool:
        self._organizer = organizer
        on_ui = getattr(organizer, "onUserInterfaceInitialized", None)
        if callable(on_ui):
            on_ui(self._on_user_interface_initialized)
        else:
            LOGGER.warning("MO2 did not expose onUserInterfaceInitialized")
        on_settings = getattr(organizer, "onPluginSettingChanged", None)
        if callable(on_settings):
            on_settings(self._on_plugin_setting_changed)
        on_enabled = getattr(organizer, "onPluginEnabled", None)
        if callable(on_enabled):
            try:
                on_enabled(self.name(), self._on_plugin_enabled)
            except TypeError:
                pass
        on_disabled = getattr(organizer, "onPluginDisabled", None)
        if callable(on_disabled):
            try:
                on_disabled(self.name(), self._on_plugin_disabled)
            except TypeError:
                pass
        self._reconfigure()
        return True

    def _setting(self, key: str, default: Any) -> Any:
        if self._organizer is None:
            return default
        try:
            value = self._organizer.pluginSetting(self.name(), key)
        except Exception:
            return default
        return default if value is None else value

    def _reconfigure(self) -> None:
        try:
            index = max(-1, min(3, int(self._setting("controller_index", -1))))
            repeat_delay = self._clamp_ms(self._setting("repeat_delay_ms", 350), 0, 5000) / 1000.0
            repeat_interval = self._clamp_ms(self._setting("repeat_interval_ms", 120), 10, 5000) / 1000.0
            deadzone = self._clamp_ms(self._setting("left_stick_deadzone", 7849), 1, 32767)
            press = deadzone / 32767.0
            release = (deadzone * 0.75) / 32767.0
            self._backend = XInputBackend(index)
            self._processor = InputProcessor(ControllerMapping.from_values(
                str(self._setting("run_buttons", "A")),
                str(self._setting("next_tool_buttons", "DPadDown,DPadRight,RB")),
                str(self._setting("previous_tool_buttons", "DPadUp,DPadLeft,LB")),
                repeat_delay, repeat_interval, press, release,
                bool(self._setting("left_stick_navigation", True)),
            ))
            self._active_controller = None
            self._last_controller = None
            self._next_auto_scan = 0.0
            self._was_connected = False
            self._ready_latched = False
            self._reconnect_interval = self._clamp_ms(
                self._setting("reconnect_interval_ms", 1000), 250, 5000
            ) / 1000.0
        except (TypeError, ValueError) as exc:
            self._last_error = str(exc)
            LOGGER.error("Invalid XInput Controller settings: %s", exc)

    def _on_plugin_setting_changed(self, plugin_name: str, setting: str, old: Any, new: Any) -> None:
        if plugin_name != self.name():
            return
        self._reconfigure()
        if self._bridge is not None:
            self._bridge.wrap_tools = bool(self._setting("wrap_selection", True))
        self._ready_latched = False
        self._update_timer_state()

    @staticmethod
    def _clamp_ms(value: Any, minimum: int, maximum: int) -> int:
        try:
            return max(minimum, min(maximum, int(float(value))))
        except (TypeError, ValueError):
            return minimum

    def _on_plugin_enabled(self, *_args: Any) -> None:
        self._plugin_enabled = True
        self._ready_latched = False
        self._update_timer_state()

    def _on_plugin_disabled(self, *_args: Any) -> None:
        self._plugin_enabled = False
        self._ready_latched = False
        self._processor.reset()
        self._update_timer_state()

    def _on_user_interface_initialized(self, window: Any) -> None:
        self._window = window
        bridge = StrictMo2UiBridge(
            window, bool(self._setting("wrap_selection", True))
        )
        try:
            bridge.validate()
        except UiBridgeUnavailable as exc:
            self._last_error = str(exc)
            LOGGER.warning("MO2 2.5.2 UI controls were not found: %s", exc)
            self._bridge = None
            return
        self._bridge = bridge
        destroyed = getattr(window, "destroyed", None)
        if destroyed is not None and callable(getattr(destroyed, "connect", None)):
            destroyed.connect(self.shutdown)
        try:
            from PyQt6.QtWidgets import QApplication
        except ImportError:
            from PyQt5.QtWidgets import QApplication
        application = QApplication.instance()
        if application is not None:
            application.aboutToQuit.connect(self.shutdown)
        self._create_timer()
        self._update_timer_state()

    def _create_timer(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            try:
                self._timer.timeout.disconnect(self._poll)
            except (TypeError, RuntimeError):
                pass
            self._timer.deleteLater()
        try:
            from PyQt6.QtCore import QTimer
        except ImportError:
            from PyQt5.QtCore import QTimer
        self._timer = QTimer(self._window)
        self._timer.setInterval(self._clamp_ms(self._setting("poll_interval_ms", 30), 16, 250))
        self._timer.timeout.connect(self._poll)

    def _update_timer_state(self) -> None:
        if self._timer is None:
            return
        self._timer.setInterval(self._clamp_ms(self._setting("poll_interval_ms", 30), 16, 250))
        if self.isActive():
            self._timer.start()
        else:
            self._timer.stop()
            self._processor.reset()

    def _read_controller(self, now: float) -> tuple[Optional[XInputState], Optional[int]]:
        backend = self._backend
        if backend is None:
            return None, None
        configured = backend.user_index
        if configured >= 0:
            if self._active_controller is None and now < self._next_auto_scan:
                return None, None
            try:
                state = backend.get_state(configured)
            except Exception as exc:
                self._last_error = str(exc)
                LOGGER.warning("XInput read failed: %s", exc)
                state = None
            if state is None:
                self._active_controller = None
                self._next_auto_scan = now + self._reconnect_interval
                return None, None
            self._active_controller = configured
            return state, configured
        # Automatic mode stays on the first connected controller and only scans
        # all four slots sparsely after it disconnects.
        if self._active_controller is not None:
            try:
                state = backend.get_state(self._active_controller)
            except Exception as exc:
                self._last_error = str(exc)
                state = None
            if state is not None:
                return state, self._active_controller
            self._active_controller = None
        if now < self._next_auto_scan:
            return None, None
        self._next_auto_scan = now + self._reconnect_interval
        for index in range(4):
            try:
                state = backend.get_state(index)
            except Exception:
                state = None
            if state is not None:
                self._active_controller = index
                return state, index
        return None, None

    def _poll(self) -> None:
        if not self.isActive() or self._bridge is None:
            return
        now = time.monotonic()
        state, controller = self._read_controller(now)
        connected = state is not None
        if connected != self._was_connected or (connected and controller != self._last_controller):
            self._processor.neutral_rearm(state)
            self._was_connected = connected
            self._last_controller = controller
            self._ready_latched = False
        if not self._bridge.navigation_ready():
            self._processor.neutral_rearm(state)
            self._ready_latched = False
            return
        if not self._ready_latched:
            self._processor.neutral_rearm(state)
            self._ready_latched = True
            return
        for action in self._processor.process(state, now):
            # Re-check on every action so a modal/focus transition cannot replay
            # a queued Run action.
            if not self._bridge.navigation_ready():
                self._processor.neutral_rearm(state)
                self._ready_latched = False
                return
            try:
                if action is InputAction.RUN:
                    self._bridge.run_selected_tool()
                elif action is InputAction.TOOL_NEXT:
                    self._bridge.select_next_tool()
                elif action is InputAction.TOOL_PREVIOUS:
                    self._bridge.select_previous_tool()
            except UiBridgeUnavailable as exc:
                self._last_error = str(exc)
                LOGGER.warning("MO2 UI bridge unavailable: %s", exc)
                self._processor.neutral_rearm(state)
                self._ready_latched = False
                return

    def shutdown(self, *_args: Any) -> None:
        if self._timer is not None:
            self._timer.stop()
            try:
                self._timer.timeout.disconnect(self._poll)
            except (TypeError, RuntimeError):
                pass
            self._timer.deleteLater()
            self._timer = None
        self._bridge = None
        self._window = None
        self._processor.reset()

    def __del__(self) -> None:
        try:
            self.shutdown()
        except Exception:
            pass


def createPlugin() -> XInputControllerPlugin:
    return XInputControllerPlugin()
