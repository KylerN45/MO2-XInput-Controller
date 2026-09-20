"""Minimal offline PEP 517 backend so the project declares no build deps."""

from __future__ import annotations

import zipfile
from pathlib import Path


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    wheel = Path(wheel_directory) / "mo2_xinput_controller-0.1.0-py3-none-any.whl"
    root = Path(__file__).resolve().parent
    with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in (root / "src" / "mo2_xinput_controller").glob("*.py"):
            zf.write(file, f"mo2_xinput_controller/{file.name}")
        zf.writestr("mo2_xinput_controller-0.1.0.dist-info/METADATA", "Metadata-Version: 2.1\nName: mo2-xinput-controller\nVersion: 0.1.0\n")
        zf.writestr("mo2_xinput_controller-0.1.0.dist-info/WHEEL", "Wheel-Version: 1.0\nGenerator: offline\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        zf.writestr("mo2_xinput_controller-0.1.0.dist-info/RECORD", "")
    return wheel.name


def build_sdist(sdist_directory, config_settings=None):
    raise NotImplementedError("Use build_package.py for the MO2 plugin archive")
