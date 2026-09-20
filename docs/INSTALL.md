# Installation and troubleshooting

## Installation

The release ZIP mirrors the MO2 installation root. Close MO2, extract the ZIP
into that root, and verify
`<MO2>\plugins\mo2_xinput_controller\__init__.py`. Do not install the ZIP as a
mod and do not extract it inside `<MO2>\plugins`, which would create a nested
`plugins\plugins` path. Restart MO2 after installing because Python plugins are
discovered at startup.

The plugin is independent of the managed game. It only controls the MO2
window, and clicking `startButton` continues to launch through MO2's VFS.

## Verify the bridge

Open Settings > Plugins and confirm **XInput Controller Support** is enabled.
The plugin polls quietly in the background. Press A with a controller
connected: it should have the same effect as clicking Run. D-pad Left/Right
changes the selected item in the executable list.

If no action occurs, check the following:

* The controller is visible in Windows' Game Controllers panel.
* The controller index is `-1` for automatic selection or the correct fixed
index (0-3).
* `executablesListBox` is on an executable entry (index 0 is deliberately
  skipped) and `startButton` is enabled.
* The MO2 log contains no `MO2-XInput-Controller` bridge warning.

The plugin does not emulate keyboard or mouse input. This is deliberate: a
renamed or missing MO2 control must not result in an unrelated UI action.

## Building a release archive

Run `python build_package.py`. The script emits the ZIP and a SHA-256 sidecar
under `dist/`. It includes only the module plugin under
`plugins/mo2_xinput_controller`, documentation, and the license.
