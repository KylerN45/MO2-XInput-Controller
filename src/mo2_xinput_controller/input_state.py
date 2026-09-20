"""XInput control mapping and GUI-safe edge/repeat state machine."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from .xinput import (
    XINPUT_GAMEPAD_A, XINPUT_GAMEPAD_B, XINPUT_GAMEPAD_BACK,
    XINPUT_GAMEPAD_DPAD_DOWN, XINPUT_GAMEPAD_DPAD_LEFT,
    XINPUT_GAMEPAD_DPAD_RIGHT, XINPUT_GAMEPAD_DPAD_UP,
    XINPUT_GAMEPAD_LEFT_SHOULDER, XINPUT_GAMEPAD_RIGHT_SHOULDER,
    XINPUT_GAMEPAD_START, XINPUT_GAMEPAD_X, XINPUT_GAMEPAD_Y, XInputState,
)

LOGGER = logging.getLogger("MO2-XInput-Controller")


class Control(str, Enum):
    A = "A"
    B = "B"
    X = "X"
    Y = "Y"
    LB = "LB"
    RB = "RB"
    BACK = "Back"
    START = "Start"
    DPAD_UP = "DPadUp"
    DPAD_DOWN = "DPadDown"
    DPAD_LEFT = "DPadLeft"
    DPAD_RIGHT = "DPadRight"
    LEFT_STICK_UP = "LSUp"
    LEFT_STICK_DOWN = "LSDown"
    LEFT_STICK_LEFT = "LSLeft"
    LEFT_STICK_RIGHT = "LSRight"
    RIGHT_STICK_UP = "RSUp"
    RIGHT_STICK_DOWN = "RSDown"
    RIGHT_STICK_LEFT = "RSLeft"
    RIGHT_STICK_RIGHT = "RSRight"


Button = Control
BUTTON_MASKS = {
    Control.A: XINPUT_GAMEPAD_A, Control.B: XINPUT_GAMEPAD_B,
    Control.X: XINPUT_GAMEPAD_X, Control.Y: XINPUT_GAMEPAD_Y,
    Control.LB: XINPUT_GAMEPAD_LEFT_SHOULDER, Control.RB: XINPUT_GAMEPAD_RIGHT_SHOULDER,
    Control.BACK: XINPUT_GAMEPAD_BACK, Control.START: XINPUT_GAMEPAD_START,
    Control.DPAD_UP: XINPUT_GAMEPAD_DPAD_UP, Control.DPAD_DOWN: XINPUT_GAMEPAD_DPAD_DOWN,
    Control.DPAD_LEFT: XINPUT_GAMEPAD_DPAD_LEFT, Control.DPAD_RIGHT: XINPUT_GAMEPAD_DPAD_RIGHT,
}


class InputAction(str, Enum):
    RUN = "run"
    TOOL_NEXT = "tool_next"
    TOOL_PREVIOUS = "tool_previous"


@dataclass(frozen=True)
class ControllerMapping:
    run_controls: Tuple[Control, ...] = (Control.A,)
    tool_next_controls: Tuple[Control, ...] = (Control.DPAD_DOWN, Control.DPAD_RIGHT, Control.RB, Control.LEFT_STICK_DOWN)
    tool_previous_controls: Tuple[Control, ...] = (Control.DPAD_UP, Control.DPAD_LEFT, Control.LB, Control.LEFT_STICK_UP)
    repeat_delay: float = 0.35
    repeat_interval: float = 0.16
    stick_press_threshold: float = 0.55
    stick_release_threshold: float = 0.45

    def __post_init__(self) -> None:
        if self.repeat_delay < 0 or self.repeat_interval <= 0:
            raise ValueError("repeat_delay must be >= 0 and repeat_interval > 0")
        if not 0 <= self.stick_release_threshold < self.stick_press_threshold <= 1:
            raise ValueError("stick release threshold must be below press threshold")

    @staticmethod
    def parse_controls(value: str, fallback: Tuple[Control, ...]) -> Tuple[Control, ...]:
        aliases = {
            "LeftShoulder": "LB", "RightShoulder": "RB",
            "LeftStickUp": "LSUp", "LeftStickDown": "LSDown",
            "LeftStickLeft": "LSLeft", "LeftStickRight": "LSRight",
            "RightStickUp": "RSUp", "RightStickDown": "RSDown",
            "RightStickLeft": "RSLeft", "RightStickRight": "RSRight",
            "LStickUp": "LSUp", "LStickDown": "LSDown",
            "LStickLeft": "LSLeft", "LStickRight": "LSRight",
            "RStickUp": "RSUp", "RStickDown": "RSDown",
            "RStickLeft": "RSLeft", "RStickRight": "RSRight",
        }
        controls: List[Control] = []
        for raw in value.split(","):
            raw_name = raw.strip()
            key = "".join(ch for ch in raw_name.lower() if ch.isalnum())
            canonical = {
                "a": "A", "b": "B", "x": "X", "y": "Y", "lb": "LB", "leftshoulder": "LB",
                "rb": "RB", "rightshoulder": "RB", "back": "Back", "start": "Start",
                "dpadup": "DPadUp", "dpaddown": "DPadDown", "dpadleft": "DPadLeft", "dpadright": "DPadRight",
                "lsup": "LSUp", "lsdown": "LSDown", "lsleft": "LSLeft", "lsright": "LSRight",
                "leftstickup": "LSUp", "leftstickdown": "LSDown", "leftstickleft": "LSLeft", "leftstickright": "LSRight",
                "rsup": "RSUp", "rsdown": "RSDown", "rsleft": "RSLeft", "rsright": "RSRight",
                "rightstickup": "RSUp", "rightstickdown": "RSDown", "rightstickleft": "RSLeft", "rightstickright": "RSRight",
            }.get(key)
            name = canonical or aliases.get(raw_name, raw_name)
            if not name:
                continue
            try:
                control = Control(name)
            except ValueError:
                LOGGER.warning("Ignoring unknown controller control %r", raw_name)
                continue
            if control not in controls:
                controls.append(control)
        if not controls:
            LOGGER.warning("No valid controller controls in %r; using fallback %s", value, fallback)
            return fallback
        return tuple(controls)

    @classmethod
    def from_values(cls, run_controls: str = "A", tool_next_controls: str = "DPadDown,DPadRight,RB,LSDown",
                    tool_previous_controls: str = "DPadUp,DPadLeft,LB,LSUp", repeat_delay: float = 0.35,
                    repeat_interval: float = 0.16, stick_press_threshold: float = 0.55,
                    stick_release_threshold: float = 0.45, left_stick_navigation: bool = True) -> "ControllerMapping":
        default_next = (Control.DPAD_DOWN, Control.DPAD_RIGHT, Control.RB, Control.LEFT_STICK_DOWN)
        default_previous = (Control.DPAD_UP, Control.DPAD_LEFT, Control.LB, Control.LEFT_STICK_UP)
        if not left_stick_navigation:
            default_next = tuple(c for c in default_next if c is not Control.LEFT_STICK_DOWN)
            default_previous = tuple(c for c in default_previous if c is not Control.LEFT_STICK_UP)
        next_controls = list(cls.parse_controls(tool_next_controls, default_next))
        previous_controls = list(cls.parse_controls(tool_previous_controls, default_previous))
        if left_stick_navigation:
            if Control.LEFT_STICK_DOWN not in next_controls:
                next_controls.append(Control.LEFT_STICK_DOWN)
            if Control.LEFT_STICK_UP not in previous_controls:
                previous_controls.append(Control.LEFT_STICK_UP)
        else:
            next_controls = [c for c in next_controls if c is not Control.LEFT_STICK_DOWN]
            previous_controls = [c for c in previous_controls if c is not Control.LEFT_STICK_UP]
        return cls(cls.parse_controls(run_controls, (Control.A,)), tuple(next_controls), tuple(previous_controls), repeat_delay, repeat_interval,
                    stick_press_threshold, stick_release_threshold)


class InputProcessor:
    def __init__(self, mapping: Optional[ControllerMapping] = None) -> None:
        self.mapping = mapping or ControllerMapping()
        self._previous: dict[Control, bool] = {}
        self._direction = 0
        self._next_repeat_at: Optional[float] = None
        self._requires_neutral = False

    def reset(self) -> None:
        self._previous.clear()
        self._direction = 0
        self._next_repeat_at = None
        self._requires_neutral = False

    def neutral_rearm(self, state: Optional[XInputState]) -> None:
        self.reset()
        if state is not None:
            self._previous = self._controls(state)
            self._direction = self._navigation_direction(self._previous)
            self._requires_neutral = self._any_mapped_input(self._previous)

    def _any_mapped_input(self, controls: dict[Control, bool]) -> bool:
        mapped = (
            self.mapping.run_controls
            + self.mapping.tool_next_controls
            + self.mapping.tool_previous_controls
        )
        return any(controls.get(control, False) for control in mapped)

    def _navigation_direction(self, controls: dict[Control, bool]) -> int:
        next_pressed = any(
            controls.get(control, False) for control in self.mapping.tool_next_controls
        )
        previous_pressed = any(
            controls.get(control, False)
            for control in self.mapping.tool_previous_controls
        )
        if next_pressed == previous_pressed:
            return 0
        return 1 if next_pressed else -1

    def _controls(self, state: XInputState) -> dict[Control, bool]:
        controls = {control: state.pressed(mask) for control, mask in BUTTON_MASKS.items()}
        press, release = self.mapping.stick_press_threshold, self.mapping.stick_release_threshold

        def axis(value: int, positive: bool, previous: bool) -> bool:
            magnitude = value / 32767.0
            active = magnitude >= press if positive else magnitude <= -press
            if previous and not active:
                active = magnitude >= release if positive else magnitude <= -release
            return active

        axes = ((Control.LEFT_STICK_UP, state.left_thumb_y, True),
                (Control.LEFT_STICK_DOWN, state.left_thumb_y, False),
                (Control.LEFT_STICK_RIGHT, state.left_thumb_x, True),
                (Control.LEFT_STICK_LEFT, state.left_thumb_x, False),
                (Control.RIGHT_STICK_UP, state.right_thumb_y, True),
                (Control.RIGHT_STICK_DOWN, state.right_thumb_y, False),
                (Control.RIGHT_STICK_RIGHT, state.right_thumb_x, True),
                (Control.RIGHT_STICK_LEFT, state.right_thumb_x, False))
        for control, value, positive in axes:
            controls[control] = axis(value, positive, self._previous.get(control, False))
        return controls

    def process(self, state: Optional[XInputState], now: float) -> List[InputAction]:
        if state is None:
            self.reset()
            return []
        current = self._controls(state)

        # Startup, reconnect, focus regain, and modal close all pass through
        # neutral_rearm().  Do not act until every mapped control has been
        # released at least once, even when opposing directions cancel.
        if self._requires_neutral:
            self._previous = current
            self._direction = self._navigation_direction(current)
            if not self._any_mapped_input(current):
                self._requires_neutral = False
                self._direction = 0
            return []

        actions: List[InputAction] = []

        run_pressed = any(
            current.get(control, False) for control in self.mapping.run_controls
        )
        run_was_pressed = any(
            self._previous.get(control, False) for control in self.mapping.run_controls
        )
        if run_pressed and not run_was_pressed:
            actions.append(InputAction.RUN)

        direction = self._navigation_direction(current)
        if direction == 0:
            self._next_repeat_at = None
        elif direction != self._direction:
            actions.append(
                InputAction.TOOL_NEXT
                if direction > 0
                else InputAction.TOOL_PREVIOUS
            )
            self._next_repeat_at = now + self.mapping.repeat_delay
        elif self._next_repeat_at is not None and now >= self._next_repeat_at:
            actions.append(
                InputAction.TOOL_NEXT
                if direction > 0
                else InputAction.TOOL_PREVIOUS
            )
            # Deliberately schedule from "now" rather than catching up after a
            # stalled UI thread with a burst of actions.
            self._next_repeat_at = now + self.mapping.repeat_interval

        self._previous = current
        self._direction = direction
        return actions
