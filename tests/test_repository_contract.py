"""Repository-level contract tests for the RPi satellite project."""

from __future__ import annotations

import py_compile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepositoryStructureContractTests(unittest.TestCase):
    """Validate expected project layout and lightweight repository contracts."""

    def test_required_top_level_files_exist(self) -> None:
        for relative_path in ("main.py", "config.py", "requirements.txt"):
            with self.subTest(path=relative_path):
                path = ROOT / relative_path
                self.assertTrue(path.is_file(), f"{relative_path} must exist")

    def test_required_source_groups_exist(self) -> None:
        required_groups = {
            "sensors/*.py": ROOT / "sensors",
            "output/*.py": ROOT / "output",
            "docs/*.md": ROOT / "docs",
        }

        for pattern, directory in required_groups.items():
            with self.subTest(pattern=pattern):
                self.assertTrue(directory.is_dir(), f"{directory.name}/ must exist")
                matches = sorted(ROOT.glob(pattern))
                self.assertTrue(matches, f"{pattern} must match at least one file")

    def test_debug_check_script_exists(self) -> None:
        self.assertTrue(
            (ROOT / "scripts" / "debug_check.py").is_file(),
            "scripts/debug_check.py must exist",
        )

    def test_requirements_include_external_library_candidates(self) -> None:
        requirements_path = ROOT / "requirements.txt"
        requirements = {
            line.strip().lower().replace("_", "-")
            for line in requirements_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        expected_candidates = {
            "adafruit-circuitpython-dht",
            "adafruit-circuitpython-bmp280",
            "adafruit-circuitpython-mpu6050",
            "adafruit-circuitpython-bh1750",
            "adafruit-dht",
            "bmp280",
            "rpi.gpio",
            "pyserial",
            "pynmea2",
            "smbus2",
        }

        missing = sorted(expected_candidates - requirements)
        self.assertFalse(
            missing,
            "requirements.txt is missing expected external library candidates: "
            + ", ".join(missing),
        )

    def test_all_python_files_compile(self) -> None:
        python_files = sorted(
            path for path in ROOT.rglob("*.py") if ".git" not in path.parts
        )
        self.assertTrue(python_files, "repository must contain Python files")

        with tempfile.TemporaryDirectory() as cache_dir:
            cache_root = Path(cache_dir)
            for index, path in enumerate(python_files):
                relative_path = path.relative_to(ROOT)
                cfile = cache_root / f"{index}.pyc"
                with self.subTest(path=str(relative_path)):
                    py_compile.compile(str(path), cfile=str(cfile), doraise=True)


if __name__ == "__main__":
    unittest.main()
