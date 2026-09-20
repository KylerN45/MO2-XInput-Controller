"""Build a dependency-free MO2 plugin ZIP from the source tree."""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
PACKAGE = "mo2_xinput_controller"
VERSION = "0.1.0"


def build(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / f"MO2-XInput-Controller-v{VERSION}.zip"
    files = [
        ROOT / "README.md",
        ROOT / "LICENSE",
        ROOT / "docs" / "INSTALL.md",
    ]
    package_dir = ROOT / "src" / PACKAGE
    files.extend(sorted(package_dir.glob("*.py")))
    with ZipFile(archive, "w", ZIP_DEFLATED) as zf:
        for file in files:
            if not file.is_file():
                raise FileNotFoundError(file)
            if file.parent == package_dir:
                name = f"plugins/{PACKAGE}/{file.name}"
            else:
                name = file.relative_to(ROOT).as_posix()
            zf.write(file, name)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (destination / f"{archive.name}.sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    archive = build(args.output)
    print(archive)


if __name__ == "__main__":
    main()
