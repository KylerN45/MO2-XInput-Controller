import unittest

from mo2_xinput_controller.input_state import (
    Button,
    Control,
    ControllerMapping,
    InputAction,
    InputProcessor,
)
from mo2_xinput_controller.xinput import (
    XInputState, XINPUT_GAMEPAD_A, XINPUT_GAMEPAD_DPAD_LEFT,
    XINPUT_GAMEPAD_DPAD_RIGHT,
    XINPUT_GAMEPAD_LEFT_SHOULDER,
)


def snapshot(buttons: int) -> XInputState:
    return XInputState(0, buttons, 0, 0, 0, 0, 0, 0)


class InputProcessorTests(unittest.TestCase):
    def test_run_is_edge_triggered(self):
        processor = InputProcessor()
        self.assertEqual(processor.process(snapshot(XINPUT_GAMEPAD_A), 0.0), [InputAction.RUN])
        self.assertEqual(processor.process(snapshot(XINPUT_GAMEPAD_A), 0.1), [])
        self.assertEqual(processor.process(snapshot(0), 0.2), [])
        self.assertEqual(processor.process(snapshot(XINPUT_GAMEPAD_A), 0.3), [InputAction.RUN])

    def test_tool_direction_repeats_after_delay(self):
        processor = InputProcessor(ControllerMapping(repeat_delay=0.3, repeat_interval=0.1))
        self.assertEqual(processor.process(snapshot(XINPUT_GAMEPAD_DPAD_RIGHT), 0.0), [InputAction.TOOL_NEXT])
        self.assertEqual(processor.process(snapshot(XINPUT_GAMEPAD_DPAD_RIGHT), 0.29), [])
        self.assertEqual(processor.process(snapshot(XINPUT_GAMEPAD_DPAD_RIGHT), 0.31), [InputAction.TOOL_NEXT])
        self.assertEqual(processor.process(snapshot(XINPUT_GAMEPAD_DPAD_RIGHT), 0.35), [])
        self.assertEqual(processor.process(snapshot(XINPUT_GAMEPAD_DPAD_RIGHT), 0.42), [InputAction.TOOL_NEXT])

    def test_direction_change_is_immediate_and_opposites_cancel(self):
        processor = InputProcessor()
        self.assertEqual(
            processor.process(snapshot(XINPUT_GAMEPAD_DPAD_RIGHT), 0.0),
            [InputAction.TOOL_NEXT],
        )
        both = XINPUT_GAMEPAD_DPAD_RIGHT | XINPUT_GAMEPAD_DPAD_LEFT
        self.assertEqual(processor.process(snapshot(both), 0.1), [])
        self.assertEqual(
            processor.process(snapshot(XINPUT_GAMEPAD_DPAD_LEFT), 0.2),
            [InputAction.TOOL_PREVIOUS],
        )

    def test_neutral_rearm_requires_every_mapped_input_to_be_released(self):
        processor = InputProcessor()
        both = XINPUT_GAMEPAD_A | XINPUT_GAMEPAD_DPAD_RIGHT
        processor.neutral_rearm(snapshot(both))
        self.assertEqual(
            processor.process(snapshot(XINPUT_GAMEPAD_DPAD_RIGHT), 0.1), []
        )
        self.assertEqual(processor.process(snapshot(0), 0.2), [])
        self.assertEqual(
            processor.process(snapshot(XINPUT_GAMEPAD_DPAD_RIGHT), 0.3),
            [InputAction.TOOL_NEXT],
        )

    def test_repeat_does_not_catch_up_after_clock_jump(self):
        processor = InputProcessor(
            ControllerMapping(repeat_delay=0.3, repeat_interval=0.1)
        )
        held = snapshot(XINPUT_GAMEPAD_DPAD_RIGHT)
        self.assertEqual(processor.process(held, 0.0), [InputAction.TOOL_NEXT])
        self.assertEqual(processor.process(held, 10.0), [InputAction.TOOL_NEXT])
        self.assertEqual(processor.process(held, 10.01), [])

    def test_disconnect_resets_held_state(self):
        processor = InputProcessor()
        processor.process(snapshot(XINPUT_GAMEPAD_DPAD_RIGHT), 0.0)
        self.assertEqual(processor.process(None, 0.1), [])
        self.assertEqual(processor.process(snapshot(XINPUT_GAMEPAD_DPAD_RIGHT), 0.2), [InputAction.TOOL_NEXT])

    def test_mapping_ignores_unknown_button_and_uses_action_fallback(self):
        mapping = ControllerMapping.from_values("NotAButton", "bad,DPadRight", "DPadLeft", left_stick_navigation=False)
        self.assertEqual(mapping.run_controls, (Control.A,))
        self.assertEqual(mapping.tool_next_controls, (Control.DPAD_RIGHT,))

    def test_multiple_controls_and_shoulder_are_supported(self):
        mapping = ControllerMapping.from_values("A,Start", "RB", "LB")
        processor = InputProcessor(mapping)
        self.assertEqual(processor.process(snapshot(XINPUT_GAMEPAD_LEFT_SHOULDER), 0.0), [InputAction.TOOL_PREVIOUS])

    def test_stick_hysteresis_holds_until_release_threshold(self):
        processor = InputProcessor(ControllerMapping.from_values("LSUp", "DPadRight", "DPadLeft", left_stick_navigation=False))
        high = XInputState(0, 0, 0, 0, 0, 20000, 0, 0)
        middle = XInputState(0, 0, 0, 0, 0, 16000, 0, 0)
        low = XInputState(0, 0, 0, 0, 0, 14000, 0, 0)
        self.assertEqual(processor.process(high, 0.0), [InputAction.RUN])
        self.assertEqual(processor.process(middle, 0.1), [])
        self.assertEqual(processor.process(low, 0.2), [])


if __name__ == "__main__":
    unittest.main()
