import unittest
from unittest.mock import patch

from mo2_xinput_controller.input_state import InputAction
from mo2_xinput_controller.plugin import XInputControllerPlugin
from mo2_xinput_controller.xinput import XInputState


class Organizer:
    def pluginSetting(self, _plugin, key):
        return {"enabled": False}.get(key)


class Backend:
    user_index = 2
    calls = 0

    def get_state(self, index):
        self.last_index = index
        self.calls += 1
        return XInputState(0, 0 if self.calls == 1 else 0x1000, 0, 0, 0, 0, 0, 0)


class DisconnectedBackend:
    user_index = 2

    def __init__(self):
        self.calls = 0

    def get_state(self, _index):
        self.calls += 1
        return None


class Bridge:
    def __init__(self):
        self.calls = 0
        self.available = True

    def navigation_ready(self): return self.available
    def run_selected_tool(self): self.calls += 1
    def select_next_tool(self): pass
    def select_previous_tool(self): pass


class PluginTests(unittest.TestCase):
    def test_metadata_and_settings_are_available_without_mo2(self):
        plugin = XInputControllerPlugin()
        self.assertEqual(plugin.name(), "XInput Controller Support")
        self.assertTrue(plugin.description())
        self.assertGreaterEqual(len(plugin.settings()), 8)
        keys = [setting.key for setting in plugin.settings()]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertNotIn("enabled", keys)

    def test_disabled_plugin_does_not_create_gui_timer(self):
        plugin = XInputControllerPlugin()
        self.assertTrue(plugin.init(Organizer()))
        self.assertIsNone(plugin._timer)
        plugin.shutdown()

    def test_configuration_accepts_multi_control_mapping(self):
        plugin = XInputControllerPlugin()
        plugin._reconfigure()
        self.assertEqual(plugin._processor.mapping.run_controls[0].value, "A")
        plugin.shutdown()

    def test_fixed_controller_arms_once_and_does_not_rearm_every_poll(self):
        plugin = XInputControllerPlugin()
        plugin._backend = Backend()
        plugin._bridge = Bridge()
        plugin._poll()
        plugin._poll()
        plugin._poll()
        self.assertEqual(plugin._backend.last_index, 2)
        self.assertEqual(plugin._bridge.calls, 1)

    def test_modal_transition_neutral_rearms_without_catchup(self):
        plugin = XInputControllerPlugin()
        plugin._backend = Backend()
        plugin._bridge = Bridge()
        plugin._poll()
        plugin._bridge.available = False
        plugin._poll()
        plugin._bridge.available = True
        plugin._poll()
        self.assertEqual(plugin._bridge.calls, 0)

    def test_fixed_disconnected_controller_uses_sparse_reconnect_scans(self):
        plugin = XInputControllerPlugin()
        plugin._backend = DisconnectedBackend()
        plugin._bridge = Bridge()
        plugin._reconnect_interval = 1.0
        with patch(
            "mo2_xinput_controller.plugin.time.monotonic",
            side_effect=(1.0, 1.1, 2.1),
        ):
            plugin._poll()
            plugin._poll()
            plugin._poll()
        self.assertEqual(plugin._backend.calls, 2)


if __name__ == "__main__":
    unittest.main()
