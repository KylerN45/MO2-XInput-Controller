# MO2 XInput Controller

Standalone Python plugin for Mod Organizer 2.5.2 that adds XInput controller
support to the MO2 executable selector and Run action. It does not fork or
replace MO2 and it does not inject input into the game.

## MVP controls

The defaults are:

| Controller input | MO2 action |
| --- | --- |
| A | Activate the normal MO2 Run action |
| D-pad Down/Right, RB, Left Stick Down | Select the next executable |
| D-pad Up/Left, LB, Left Stick Up | Select the previous executable |

Run is edge-triggered. Navigation repeats after a short delay while a direction
is held. Bindings are case-insensitive comma-separated lists, so they can be
changed without editing code (for example, `A,Start`). Controller index `-1`
automatically selects the lowest connected controller and remains sticky until
it disconnects. Bindings, deadzone, controller index, polling/reconnect
intervals, repeat timing, and selection wrapping are exposed through MO2's
plugin settings.

## Install

1. Download `MO2-XInput-Controller-v0.1.0.zip` from a release.
2. Close MO2 and extract the ZIP into the MO2 installation root. Confirm that
   `<MO2>\plugins\mo2_xinput_controller\__init__.py` exists.
3. Start MO2 and enable **XInput Controller Support** in Settings > Plugins.

The archive is intentionally dependency-free. It uses the Python interpreter
embedded by MO2 and loads `xinput1_4.dll`, falling back to
`xinput9_1_0.dll`. Both are loaded only from Windows' System32 directory.

## Scope and limitations

The plugin uses a strict Qt bridge. On MO2 2.5.2 it resolves the allowlisted
`executablesListBox` selector and `startButton`. This preserves
MO2's profile and virtual file system behavior. If a downstream MO2 build
renames those controls, the plugin fails closed and logs a bridge warning; it
does not start the selected executable directly.

The MVP supports A/B/X/Y, shoulders, Back/Start, the four D-pad directions,
and hysteresis-filtered cardinal directions on both sticks. Trigger/rumble,
in-game input, and simultaneous multi-controller operation remain outside this
MVP.

## Development

The runtime has no third-party dependency. From the repository root:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m compileall -q src build_package.py
python build_package.py
```

The package output is written to `dist/`. CI runs the checks on Windows with
Python 3.12, matching MO2 2.5.2's embedded interpreter.

## License

MIT. See [LICENSE](LICENSE).
