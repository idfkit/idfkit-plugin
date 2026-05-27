"""Tests for the developing-with-idfkit discovery script.

Stdlib-only (unittest) so it runs anywhere with `python -m unittest discover`
or under pytest, without adding a dependency to this plugin repo.

Filesystem-dependent behavior is exercised against real temp directories rather
than by patching ``pathlib.Path`` methods — that keeps the tests correct and
identical across POSIX and Windows.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
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


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


class FindVenvPythonTests(unittest.TestCase):
    def test_posix_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            venv = Path(tmp) / ".venv"
            expected = _touch(venv / "bin" / "python")
            self.assertEqual(discover.find_venv_python(venv), expected)

    def test_windows_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            venv = Path(tmp) / ".venv"
            expected = _touch(venv / "Scripts" / "python.exe")
            self.assertEqual(discover.find_venv_python(venv), expected)

    def test_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(discover.find_venv_python(Path(tmp) / ".venv"))


class DetectInterpreterTests(unittest.TestCase):
    def test_virtual_env_wins(self):
        with mock.patch.dict(os.environ, {"VIRTUAL_ENV": "/v"}, clear=True), \
             mock.patch.object(discover, "find_venv_python", return_value=Path("/v/bin/python")):
            cmd, tag = discover.detect_interpreter(Path("/proj"))
            self.assertEqual(tag, "virtual-env")
            self.assertEqual(cmd, [str(Path("/v/bin/python"))])

    def test_local_venv_before_parent(self):
        project = Path("/proj")

        def fake_find(root: Path):
            return Path("/proj/.venv/bin/python") if root == project / ".venv" else None

        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(discover, "find_venv_python", side_effect=fake_find):
            cmd, tag = discover.detect_interpreter(project)
            self.assertEqual(tag, "venv-local")
            self.assertEqual(cmd, [str(Path("/proj/.venv/bin/python"))])

    def test_uv_lockfile(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _touch(project / "uv.lock")
            with mock.patch.dict(os.environ, {}, clear=True), \
                 mock.patch.object(discover, "find_venv_python", return_value=None), \
                 mock.patch.object(discover, "find_git_root", return_value=None), \
                 mock.patch.object(discover.shutil, "which", side_effect=lambda n: n == "uv"):
                cmd, tag = discover.detect_interpreter(project)
                self.assertEqual(tag, "uv")
                self.assertEqual(cmd, ["uv", "run", "--quiet", "python"])

    def test_system_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)  # no lockfiles present
            with mock.patch.dict(os.environ, {}, clear=True), \
                 mock.patch.object(discover, "find_venv_python", return_value=None), \
                 mock.patch.object(discover, "find_git_root", return_value=None), \
                 mock.patch.object(discover.shutil, "which",
                                   side_effect=lambda n: n == "python3"):
                cmd, tag = discover.detect_interpreter(project)
                self.assertEqual(tag, "system")
                self.assertEqual(cmd, ["python3"])

    def test_none_when_nothing_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            with mock.patch.dict(os.environ, {}, clear=True), \
                 mock.patch.object(discover, "find_venv_python", return_value=None), \
                 mock.patch.object(discover, "find_git_root", return_value=None), \
                 mock.patch.object(discover.shutil, "which", return_value=None):
                self.assertIsNone(discover.detect_interpreter(project))


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
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist"
            result = subprocess.run(
                [sys.executable, str(DISCOVER), "--project-dir", str(missing)],
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 5)
        self.assertIn("not a directory", result.stderr)


if __name__ == "__main__":
    unittest.main()
