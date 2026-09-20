"""Small, dependency-free XInput 1.x wrapper.

Only the read side of XInput is needed for the MVP.  Loading is lazy so the
module remains importable in CI, on non-Windows systems, and in MO2 when a
controller is not connected.
"""

from __future__ import annotations

import ctypes
import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, Optional

ERROR_DEVICE_NOT_CONNECTED = 1167
ERROR_SUCCESS = 0

XINPUT_GAMEPAD_DPAD_UP = 0x0001
XINPUT_GAMEPAD_DPAD_DOWN = 0x0002
XINPUT_GAMEPAD_DPAD_LEFT = 0x0004
XINPUT_GAMEPAD_DPAD_RIGHT = 0x0008
XINPUT_GAMEPAD_START = 0x0010
XINPUT_GAMEPAD_BACK = 0x0020
XINPUT_GAMEPAD_LEFT_THUMB = 0x0040
XINPUT_GAMEPAD_RIGHT_THUMB = 0x0080
XINPUT_GAMEPAD_LEFT_SHOULDER = 0x0100
XINPUT_GAMEPAD_RIGHT_SHOULDER = 0x0200
XINPUT_GAMEPAD_A = 0x1000
XINPUT_GAMEPAD_B = 0x2000
XINPUT_GAMEPAD_X = 0x4000
XINPUT_GAMEPAD_Y = 0x8000


class _XInputGamepad(ctypes.Structure):
    _fields_ = [
        ("wButtons", ctypes.c_uint16),
        ("bLeftTrigger", ctypes.c_uint8),
        ("bRightTrigger", ctypes.c_uint8),
        ("sThumbLX", ctypes.c_int16),
        ("sThumbLY", ctypes.c_int16),
        ("sThumbRX", ctypes.c_int16),
        ("sThumbRY", ctypes.c_int16),
    ]


class _XInputState(ctypes.Structure):
    _fields_ = [("dwPacketNumber", ctypes.c_uint32), ("Gamepad", _XInputGamepad)]


class XInputError(RuntimeError):
    """Raised when XInput returns an error other than disconnected."""


@dataclass(frozen=True)
class XInputState:
    """Portable snapshot of the fields exposed by ``XINPUT_STATE``."""

    packet_number: int
    buttons: int
    left_trigger: int
    right_trigger: int
    left_thumb_x: int
    left_thumb_y: int
    right_thumb_x: int
    right_thumb_y: int

    def pressed(self, mask: int) -> bool:
        return bool(self.buttons & mask)


def _load_xinput() -> Optional[Any]:
    if sys.platform != "win32":
        return None
    system_dir = _system_directory()
    for name in ("xinput1_4.dll", "xinput9_1_0.dll"):
        try:
            return ctypes.WinDLL(os.path.join(system_dir, name))
        except OSError:
            continue
    return None


def _system_directory() -> str:
    """Return Windows' System32 path without relying on DLL search order."""
    try:
        kernel32 = ctypes.WinDLL("kernel32.dll")
        kernel32.GetSystemDirectoryW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
        kernel32.GetSystemDirectoryW.restype = ctypes.c_uint32
        buffer = ctypes.create_unicode_buffer(32768)
        length = int(kernel32.GetSystemDirectoryW(buffer, len(buffer)))
        if length:
            return buffer.value[:length]
    except (AttributeError, OSError):
        pass
    return os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")


class XInputBackend:
    """Read controller state from one of the Windows XInput DLL variants.

    ``loader`` is injectable for tests and for hosts that provide a compatible
    XInput implementation.  The callable receives a DLL name and returns a
    ctypes-compatible object.
    """

    def __init__(
        self,
        user_index: int = 0,
        loader: Optional[Callable[[str], object]] = None,
    ) -> None:
        if not -1 <= user_index <= 3:
            raise ValueError("XInput user index must be between -1 and 3")
        self.user_index = user_index
        self._loader = loader
        self._dll: Optional[object] = None
        self._get_state = None
        self._load_attempted = False
        self.dll_name: Optional[str] = None

    @property
    def available(self) -> bool:
        self._ensure_loaded()
        return self._dll is not None and self._get_state is not None

    def _ensure_loaded(self) -> None:
        if self._load_attempted:
            return
        self._load_attempted = True
        if self._loader is not None:
            names = ("xinput1_4.dll", "xinput9_1_0.dll")
            for name in names:
                try:
                    dll = self._loader(os.path.join(_system_directory(), name))
                except OSError:
                    continue
                self._dll = dll
                self.dll_name = name
                break
        else:
            self._dll = _load_xinput()
            self.dll_name = "system" if self._dll is not None else None
        if self._dll is None:
            return
        try:
            function = self._dll.XInputGetState
        except AttributeError:
            self._dll = None
            return
        function.argtypes = [ctypes.c_uint32, ctypes.POINTER(_XInputState)]
        function.restype = ctypes.c_uint32
        self._get_state = function

    def get_state(self, user_index: Optional[int] = None) -> Optional[XInputState]:
        """Return a snapshot or ``None`` when no controller is connected."""

        self._ensure_loaded()
        if self._get_state is None:
            return None
        index = self.user_index if user_index is None else user_index
        if not 0 <= index <= 3:
            raise ValueError("XInput state queries require a controller index from 0 to 3")
        raw = _XInputState()
        result = int(self._get_state(index, ctypes.byref(raw)))
        if result == ERROR_DEVICE_NOT_CONNECTED:
            return None
        if result != ERROR_SUCCESS:
            raise XInputError(f"XInputGetState failed with Win32 error {result}")
        gamepad = raw.Gamepad
        return XInputState(
            packet_number=int(raw.dwPacketNumber),
            buttons=int(gamepad.wButtons),
            left_trigger=int(gamepad.bLeftTrigger),
            right_trigger=int(gamepad.bRightTrigger),
            left_thumb_x=int(gamepad.sThumbLX),
            left_thumb_y=int(gamepad.sThumbLY),
            right_thumb_x=int(gamepad.sThumbRX),
            right_thumb_y=int(gamepad.sThumbRY),
        )
