"""Strict, fail-closed bridge to the MO2 2.5.2 main-window controls."""

from __future__ import annotations

from typing import Any


class UiBridgeUnavailable(RuntimeError):
    pass


class StrictMo2UiBridge:
    """Only the controls from MO2 2.5.2's mainwindow.ui are accepted."""

    RUN_OBJECT_NAME = "startButton"
    TOOL_OBJECT_NAME = "executablesListBox"

    def __init__(self, parent_widget: Any, wrap_tools: bool = True) -> None:
        self.parent_widget = parent_widget
        self.wrap_tools = wrap_tools

    def _find(self, name: str) -> Any:
        if self.parent_widget is None or not callable(getattr(self.parent_widget, "findChild", None)):
            raise UiBridgeUnavailable("MO2 has not supplied its main window")
        expected_type = None
        try:
            from PyQt6.QtWidgets import QComboBox, QPushButton
            expected_type = QComboBox if name == self.TOOL_OBJECT_NAME else QPushButton
        except ImportError:
            try:
                from PyQt5.QtWidgets import QComboBox, QPushButton
                expected_type = QComboBox if name == self.TOOL_OBJECT_NAME else QPushButton
            except ImportError:
                pass
        finder = self.parent_widget.findChild
        candidates = ((expected_type, name),) if expected_type is not None else ((object, name), (name,))
        for args in candidates:
            try:
                result = finder(*args)
            except (TypeError, RuntimeError):
                continue
            if result is not None:
                if expected_type is not None and not isinstance(result, expected_type):
                    raise UiBridgeUnavailable(
                        f"MO2 control {name!r} is not a {expected_type.__name__}"
                    )
                required = (
                    ("currentIndex", "count", "setCurrentIndex")
                    if name == self.TOOL_OBJECT_NAME
                    else ("click",)
                )
                if not all(callable(getattr(result, method, None)) for method in required):
                    raise UiBridgeUnavailable(
                        f"MO2 control {name!r} does not expose the expected widget API"
                    )
                return result
        raise UiBridgeUnavailable(f"MO2 control {name!r} was not found")

    @staticmethod
    def _visible_enabled(control: Any) -> bool:
        try:
            return bool(control.isVisible() and control.isEnabled())
        except (AttributeError, RuntimeError):
            return False

    def _window_ready(self) -> bool:
        window = self.parent_widget
        try:
            if (
                window is None
                or not window.isVisible()
                or not window.isEnabled()
                or not window.isActiveWindow()
            ):
                return False
        except (AttributeError, RuntimeError):
            return False
        # This hook keeps the bridge testable without importing Qt. Real Qt
        # modal state is checked through QApplication below.
        local_modal = getattr(window, "activeModalWidget", lambda: None)()
        if local_modal is not None:
            return False
        try:
            from PyQt6.QtWidgets import QApplication
        except ImportError:
            try:
                from PyQt5.QtWidgets import QApplication
            except ImportError:
                QApplication = None
        if QApplication is not None:
            try:
                modal = QApplication.activeModalWidget()
                if modal is not None:
                    return False
                active = QApplication.activeWindow()
            except RuntimeError:
                return False
            if active is not window:
                return False
        return True

    def _selector(self, require_runnable: bool = True) -> Any:
        selector = self._find(self.TOOL_OBJECT_NAME)
        if not self._visible_enabled(selector):
            raise UiBridgeUnavailable("MO2 executable selector is disabled or hidden")
        if not callable(getattr(selector, "currentIndex", None)):
            raise UiBridgeUnavailable("MO2 executable selector is not a combo box")
        if require_runnable and int(selector.currentIndex()) <= 0:
            raise UiBridgeUnavailable("MO2 executable selector is on its non-runnable index 0")
        return selector

    def ready(self) -> bool:
        if not self._window_ready():
            return False
        try:
            self._selector()
            button = self._find(self.RUN_OBJECT_NAME)
            return self._visible_enabled(button)
        except UiBridgeUnavailable:
            return False

    def validate(self) -> None:
        """Verify that the exact MO2 2.5.2 widget surface is present."""
        self._find(self.TOOL_OBJECT_NAME)
        self._find(self.RUN_OBJECT_NAME)

    def navigation_ready(self) -> bool:
        if not self._window_ready():
            return False
        try:
            self._selector(require_runnable=False)
            return True
        except UiBridgeUnavailable:
            return False

    def run_selected_tool(self) -> None:
        if not self.ready():
            raise UiBridgeUnavailable("MO2 UI is not ready for Run")
        button = self._find(self.RUN_OBJECT_NAME)
        if not callable(getattr(button, "click", None)):
            raise UiBridgeUnavailable("MO2 startButton has no click operation")
        button.click()

    def _move_tool(self, delta: int) -> None:
        if not self.navigation_ready():
            raise UiBridgeUnavailable("MO2 window is not ready")
        selector = self._selector(require_runnable=False)
        count = int(selector.count()) if callable(getattr(selector, "count", None)) else 0
        if count <= 1:
            return
        current = int(selector.currentIndex())
        # Index zero is MO2's non-runnable/edit entry and is never selected.
        if current <= 0:
            selector.setCurrentIndex(1 if delta >= 0 else count - 1)
            return
        target = current + delta
        if self.wrap_tools:
            target = 1 + ((target - 1) % (count - 1))
        else:
            target = max(1, min(count - 1, target))
        selector.setCurrentIndex(target)

    def select_next_tool(self) -> None:
        self._move_tool(1)

    def select_previous_tool(self) -> None:
        self._move_tool(-1)
