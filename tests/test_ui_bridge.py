import unittest

from mo2_xinput_controller.ui_bridge import StrictMo2UiBridge, UiBridgeUnavailable


class FakeAction:
    def __init__(self):
        self.triggered = 0
        self.visible = True
        self.enabled = True

    def isVisible(self): return self.visible
    def isEnabled(self): return self.enabled
    def click(self): self.triggered += 1


class FakeList:
    def __init__(self, count=3):
        self.index = 0
        self._count = count
        self.visible = True
        self.enabled = True

    def isVisible(self): return self.visible
    def isEnabled(self): return self.enabled
    def count(self): return self._count
    def currentIndex(self): return self.index
    def setCurrentIndex(self, index): self.index = index


class FakeWindow:
    def __init__(self):
        self.action = FakeAction()
        self.tools = FakeList()
        self.visible = True
        self.enabled = True
        self.active = True
        self.modal = None

    def isVisible(self): return self.visible
    def isEnabled(self): return self.enabled
    def isActiveWindow(self): return self.active
    def activeModalWidget(self): return self.modal

    def findChild(self, _kind, name):
        return {"startButton": self.action, "executablesListBox": self.tools}.get(name)


class UiBridgeTests(unittest.TestCase):
    def test_runs_allowlisted_action_and_wraps_tool_selection(self):
        window = FakeWindow()
        window.tools.index = 1
        bridge = StrictMo2UiBridge(window)
        bridge.run_selected_tool()
        self.assertEqual(window.action.triggered, 1)
        bridge.select_previous_tool()
        self.assertEqual(window.tools.index, 2)
        bridge.select_next_tool()
        self.assertEqual(window.tools.index, 1)

    def test_navigation_can_leave_index_zero_without_selecting_it(self):
        window = FakeWindow()
        bridge = StrictMo2UiBridge(window)
        bridge.select_next_tool()
        self.assertEqual(window.tools.index, 1)
        bridge.select_previous_tool()
        self.assertEqual(window.tools.index, 2)

    def test_background_or_modal_window_is_rejected(self):
        window = FakeWindow()
        window.active = False
        bridge = StrictMo2UiBridge(window)
        self.assertFalse(bridge.navigation_ready())
        window.active = True
        window.modal = object()
        self.assertFalse(bridge.navigation_ready())

    def test_missing_controls_fail_closed(self):
        with self.assertRaises(UiBridgeUnavailable):
            StrictMo2UiBridge(FakeWindow())._find("unknown")

    def test_wrong_widget_shape_fails_closed(self):
        window = FakeWindow()
        window.action = FakeList()
        with self.assertRaises(UiBridgeUnavailable):
            StrictMo2UiBridge(window).validate()


if __name__ == "__main__":
    unittest.main()
