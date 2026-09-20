"""XInput Controller support for Mod Organizer 2.

The package is intentionally dependency-free at runtime.  Mod Organizer's
embedded Python provides ``mobase`` and Qt; the controller backend itself
uses only :mod:`ctypes` and the Windows XInput DLL.
"""

from .input_state import (
    Button,
    Control,
    ControllerMapping,
    InputAction,
    InputProcessor,
)
from .xinput import XInputBackend, XInputState
from .plugin import XInputControllerPlugin


def createPlugin() -> XInputControllerPlugin:
    """MO2 module-plugin entry point."""
    return XInputControllerPlugin()

__all__ = [
    "Button",
    "Control",
    "ControllerMapping",
    "InputAction",
    "InputProcessor",
    "XInputBackend",
    "XInputState",
    "XInputControllerPlugin",
    "createPlugin",
]

__version__ = "0.1.0"
