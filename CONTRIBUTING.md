# Contributing

Contributions should keep the runtime dependency-free and compatible with Mod
Organizer 2.5.2's Python 3.12 and PyQt6 environment.

Before opening a pull request, run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m compileall -q src build_package.py
python build_package.py
```

Controller behavior belongs in the Qt-free input state machine. MO2 widget
access belongs in `ui_bridge.py`, and must remain strict and fail closed.
