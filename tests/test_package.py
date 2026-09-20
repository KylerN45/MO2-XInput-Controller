import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import build_package


class PackageTests(unittest.TestCase):
    def test_archive_uses_mo2_module_plugin_layout(self):
        with TemporaryDirectory() as directory:
            archive = build_package.build(Path(directory))
            with ZipFile(archive) as zf:
                names = set(zf.namelist())
        self.assertIn("plugins/mo2_xinput_controller/__init__.py", names)
        self.assertIn("plugins/mo2_xinput_controller/plugin.py", names)
        self.assertNotIn("mo2_xinput_controller_plugin.py", names)
        self.assertTrue(all(name.startswith("plugins/mo2_xinput_controller/") or name.startswith("docs/") or "/" not in name for name in names))


if __name__ == "__main__":
    unittest.main()
