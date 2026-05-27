"""Tests for the developing-with-idfkit discovery script.

Stdlib-only (unittest) so it runs anywhere with `python -m unittest discover`
or under pytest, without adding a dependency to this plugin repo.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
DISCOVER = REPO_ROOT / "skills" / "developing-with-idfkit" / "scripts" / "discover.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("discover", DISCOVER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


discover = _load_module()


class FindVenvPythonTests(unittest.TestCase):
    def test_posix_layout(self):
        with mock.patch.object(Path, "is_file", autospec=True) as is_file:
            is_file.side_effect = lambda p: p.name == "python"
            root = Path("/x/.venv")
            self.assertEqual(discover.find_venv_python(root), root / "bin" / "python")

    def test_windows_layout(self):
        with mock.patch.object(Path, "is_file", autospec=True) as is_file:
            is_file.side_effect = lambda p: p.name == "python.exe"
            root = Path("/x/.venv")
            self.assertEqual(
                discover.find_venv_python(root), root / "Scripts" / "python.exe"
            )

    def test_missing(self):
        with mock.patch.object(Path, "is_file", autospec=True, return_value=False):
            self.assertIsNone(discover.find_venv_python(Path("/x/.venv")))


class DetectInterpreterTests(unittest.TestCase):
    def test_virtual_env_wins(self):
        with mock.patch.dict(os.environ, {"VIRTUAL_ENV": "/v"}, clear=True), \
             mock.patch.object(discover, "find_venv_python", return_value=Path("/v/bin/python")):
            cmd, tag = discover.detect_interpreter(Path("/proj"))
            self.assertEqual(tag, "virtual-env")
            self.assertEqual(cmd, ["/v/bin/python"])

    def test_local_venv_before_parent(self):
        seen: list[Path] = []

        def fake_find(root: Path):
            seen.append(root)
            return Path("/proj/.venv/bin/python") if root == Path("/proj/.venv") else None

        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(discover, "find_venv_python", side_effect=fake_find):
            cmd, tag = discover.detect_interpreter(Path("/proj"))
            self.assertEqual(tag, "venv-local")
            self.assertIn(Path("/proj/.venv"), seen)

    def test_uv_lockfile(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(discover, "find_venv_python", return_value=None), \
             mock.patch.object(discover, "find_git_root", return_value=None), \
             mock.patch.object(discover.shutil, "which", side_effect=lambda n: n == "uv"), \
             mock.patch.object(Path, "is_file", autospec=True,
                               side_effect=lambda p: p.name == "uv.lock"):
            cmd, tag = discover.detect_interpreter(Path("/proj"))
            self.assertEqual(tag, "uv")
            self.assertEqual(cmd, ["uv", "run", "--quiet", "python"])

    def test_system_fallback(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(discover, "find_venv_python", return_value=None), \
             mock.patch.object(discover, "find_git_root", return_value=None), \
             mock.patch.object(discover.shutil, "which",
                               side_effect=lambda n: n == "python3"), \
             mock.patch.object(Path, "is_file", autospec=True, return_value=False):
            cmd, tag = discover.detect_interpreter(Path("/proj"))
            self.assertEqual(tag, "system")
            self.assertEqual(cmd, ["python3"])

    def test_none_when_nothing_found(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(discover, "find_venv_python", return_value=None), \
             mock.patch.object(discover, "find_git_root", return_value=None), \
             mock.patch.object(discover.shutil, "which", return_value=None), \
             mock.patch.object(Path, "is_file", autospec=True, return_value=False):
            self.assertIsNone(discover.detect_interpreter(Path("/proj")))


class InstallAdviceTests(unittest.TestCase):
    def test_venv_uses_pip(self):
        advice = discover.install_advice(["/v/bin/python"], "venv-local")
        self.assertEqual(advice, "/v/bin/python -m pip install idfkit")

    def test_each_manager(self):
        cases = {
            "conda": "conda install -c conda-forge idfkit",
            "pipenv": "pipenv install idfkit",
            "poetry": "poetry add idfkit",
            "pdm": "pdm add idfkit",
            "uv": "uv add idfkit",
        }
        for tag, expected in cases.items():
            self.assertEqual(discover.install_advice(["x"], tag), expected)

    def test_system_mentions_venv(self):
        advice = discover.install_advice(["python3"], "system")
        self.assertIn("pip install idfkit", advice)
        self.assertIn("python -m venv", advice)


class CliTests(unittest.TestCase):
    def test_bad_project_dir_exits_5(self):
        result = subprocess.run(
            [sys.executable, str(DISCOVER), "--project-dir", "/no/such/dir/xyz"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 5)
        self.assertIn("not a directory", result.stderr)


if __name__ == "__main__":
    unittest.main()
