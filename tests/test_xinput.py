import ctypes
import unittest

import mo2_xinput_controller.xinput as module
from mo2_xinput_controller.xinput import XInputBackend, XInputError


class FakeFunction:
    def __init__(self, result=0, buttons=0x1000):
        self.result = result
        self.buttons = buttons
        self.calls = []
        self.argtypes = None
        self.restype = None

    def __call__(self, index, pointer):
        self.calls.append(index)
        if self.result == 0:
            raw = ctypes.cast(pointer, ctypes.POINTER(module._XInputState)).contents
            raw.dwPacketNumber = 7
            raw.Gamepad.wButtons = self.buttons
            raw.Gamepad.bLeftTrigger = 8
            raw.Gamepad.sThumbRX = -12
        return self.result


class FakeDll:
    def __init__(self, function):
        self.XInputGetState = function


class XInputTests(unittest.TestCase):
    def test_reads_state_and_falls_back_to_first_loadable_dll(self):
        function = FakeFunction()
        calls = []

        def loader(name):
            calls.append(name)
            if not name.endswith("xinput9_1_0.dll"):
                raise OSError(name)
            return FakeDll(function)

        backend = XInputBackend(loader=loader)
        state = backend.get_state()
        self.assertEqual([name.rsplit("\\", 1)[-1] for name in calls], ["xinput1_4.dll", "xinput9_1_0.dll"])
        self.assertEqual(function.calls, [0])
        self.assertEqual(state.packet_number, 7)
        self.assertEqual(state.left_trigger, 8)
        self.assertEqual(state.right_thumb_x, -12)

    def test_device_disconnected_is_not_an_exception(self):
        function = FakeFunction(module.ERROR_DEVICE_NOT_CONNECTED)
        backend = XInputBackend(loader=lambda _name: FakeDll(function))
        self.assertIsNone(backend.get_state())

    def test_other_win32_errors_are_reported(self):
        function = FakeFunction(5)
        backend = XInputBackend(loader=lambda _name: FakeDll(function))
        with self.assertRaises(XInputError):
            backend.get_state()

    def test_user_index_is_validated(self):
        with self.assertRaises(ValueError):
            XInputBackend(user_index=4)

    def test_unavailable_backend_only_attempts_dll_loading_once(self):
        calls = []

        def loader(name):
            calls.append(name)
            raise OSError(name)

        backend = XInputBackend(loader=loader)
        self.assertIsNone(backend.get_state())
        self.assertIsNone(backend.get_state())
        self.assertEqual(len(calls), 2)

    def test_ctypes_layout_matches_xinput_structures(self):
        self.assertEqual(ctypes.sizeof(module._XInputGamepad), 12)
        self.assertEqual(ctypes.sizeof(module._XInputState), 16)


if __name__ == "__main__":
    unittest.main()
