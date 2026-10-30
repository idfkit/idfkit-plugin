"""Tests for the developing-with-idfkit discovery script.

Stdlib-only (unittest) so it runs anywhere with `python -m unittest discover`
or under pytest, without adding a dependency to this plugin repo.

Filesystem-dependent behavior is exercised against real temp directories rather
than by patching ``pathlib.Path`` methods — that keeps the tests correct and
identical across POSIX and Windows.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
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

    def test_parent_venv(self):
        project = Path("/proj/sub")

        def fake_find(root: Path):
            return Path("/proj/.venv/bin/python") if root == project.parent / ".venv" else None

        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(discover, "find_venv_python", side_effect=fake_find):
            cmd, tag = discover.detect_interpreter(project)
            self.assertEqual(tag, "venv-parent")
            self.assertEqual(cmd, [str(Path("/proj/.venv/bin/python"))])

    def test_git_root_venv(self):
        project = Path("/repo/a/b")
        git_root = Path("/repo")

        def fake_find(root: Path):
            return Path("/repo/.venv/bin/python") if root == git_root / ".venv" else None

        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(discover, "find_venv_python", side_effect=fake_find), \
             mock.patch.object(discover, "find_git_root", return_value=git_root):
            cmd, tag = discover.detect_interpreter(project)
            self.assertEqual(tag, "venv-git-root")
            self.assertEqual(cmd, [str(Path("/repo/.venv/bin/python"))])

    def test_conda_env(self):
        conda_prefix = "/opt/conda/envs/myenv"

        def fake_find(root: Path):
            return Path(conda_prefix) / "bin" / "python" if root == Path(conda_prefix) else None

        with mock.patch.dict(
            os.environ,
            {"CONDA_PREFIX": conda_prefix, "CONDA_DEFAULT_ENV": "myenv"},
            clear=True,
        ), \
             mock.patch.object(discover, "find_venv_python", side_effect=fake_find), \
             mock.patch.object(discover, "find_git_root", return_value=None):
            cmd, tag = discover.detect_interpreter(Path("/proj"))
            self.assertEqual(tag, "conda")
            self.assertEqual(cmd, [str(Path(conda_prefix) / "bin" / "python")])

    def test_conda_base_skipped_by_default_env(self):
        # CONDA_DEFAULT_ENV == "base": skip even though a base python exists,
        # falling through to the system interpreter.
        conda_prefix = "/opt/miniconda3"

        def fake_find(root: Path):
            return Path(conda_prefix) / "bin" / "python" if root == Path(conda_prefix) else None

        with mock.patch.dict(
            os.environ,
            {"CONDA_PREFIX": conda_prefix, "CONDA_DEFAULT_ENV": "base"},
            clear=True,
        ), \
             mock.patch.object(discover, "find_venv_python", side_effect=fake_find), \
             mock.patch.object(discover, "find_git_root", return_value=None), \
             mock.patch.object(discover.shutil, "which",
                               side_effect=lambda n: n == "python3"):
            cmd, tag = discover.detect_interpreter(Path("/proj"))
            self.assertEqual(tag, "system")

    def test_conda_base_skipped_by_prefix_basename(self):
        # CONDA_PREFIX basename == "base" (CONDA_DEFAULT_ENV unset): also skip.
        conda_prefix = "/opt/conda/envs/base"

        def fake_find(root: Path):
            return Path(conda_prefix) / "bin" / "python" if root == Path(conda_prefix) else None

        with mock.patch.dict(os.environ, {"CONDA_PREFIX": conda_prefix}, clear=True), \
             mock.patch.object(discover, "find_venv_python", side_effect=fake_find), \
             mock.patch.object(discover, "find_git_root", return_value=None), \
             mock.patch.object(discover.shutil, "which",
                               side_effect=lambda n: n == "python3"):
            cmd, tag = discover.detect_interpreter(Path("/proj"))
            self.assertEqual(tag, "system")

    def test_pipenv(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _touch(project / "Pipfile")
            with mock.patch.dict(os.environ, {}, clear=True), \
                 mock.patch.object(discover, "find_venv_python", return_value=None), \
                 mock.patch.object(discover, "find_git_root", return_value=None), \
                 mock.patch.object(discover.shutil, "which", side_effect=lambda n: n == "pipenv"):
                cmd, tag = discover.detect_interpreter(project)
                self.assertEqual(tag, "pipenv")
                self.assertEqual(cmd, ["pipenv", "run", "python"])

    def test_poetry_with_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _touch(project / "poetry.lock")
            _touch(project / "pyproject.toml")
            with mock.patch.dict(os.environ, {}, clear=True), \
                 mock.patch.object(discover, "find_venv_python", return_value=None), \
                 mock.patch.object(discover, "find_git_root", return_value=None), \
                 mock.patch.object(discover.shutil, "which", side_effect=lambda n: n == "poetry"):
                cmd, tag = discover.detect_interpreter(project)
                self.assertEqual(tag, "poetry")
                self.assertEqual(cmd, ["poetry", "run", "python"])

    def test_pdm_with_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _touch(project / "pdm.lock")
            _touch(project / "pyproject.toml")
            with mock.patch.dict(os.environ, {}, clear=True), \
                 mock.patch.object(discover, "find_venv_python", return_value=None), \
                 mock.patch.object(discover, "find_git_root", return_value=None), \
                 mock.patch.object(discover.shutil, "which", side_effect=lambda n: n == "pdm"):
                cmd, tag = discover.detect_interpreter(project)
                self.assertEqual(tag, "pdm")
                self.assertEqual(cmd, ["pdm", "run", "python"])

    def test_uv_lockfile(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _touch(project / "uv.lock")
            _touch(project / "pyproject.toml")
            with mock.patch.dict(os.environ, {}, clear=True), \
                 mock.patch.object(discover, "find_venv_python", return_value=None), \
                 mock.patch.object(discover, "find_git_root", return_value=None), \
                 mock.patch.object(discover.shutil, "which", side_effect=lambda n: n == "uv"):
                cmd, tag = discover.detect_interpreter(project)
                self.assertEqual(tag, "uv")
                self.assertEqual(cmd, ["uv", "run", "--quiet", "python"])

    def test_lockfile_without_manifest_falls_through(self):
        # uv.lock present but no pyproject.toml: the uv branch must not fire;
        # detection falls through to the system interpreter.
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _touch(project / "uv.lock")  # no pyproject.toml alongside it
            with mock.patch.dict(os.environ, {}, clear=True), \
                 mock.patch.object(discover, "find_venv_python", return_value=None), \
                 mock.patch.object(discover, "find_git_root", return_value=None), \
                 mock.patch.object(discover.shutil, "which",
                                   side_effect=lambda n: n in {"uv", "python3"}):
                cmd, tag = discover.detect_interpreter(project)
                self.assertEqual(tag, "system")

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


class MainExitCodeTests(unittest.TestCase):
    """Drive main() with a faked interpreter + subprocess to exercise the
    import-result branches (exit 0/1/2/4) deterministically and cross-platform.
    """

    def _run_main(self, *, returncode, stdout, stderr=""):
        fake_proc = subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=stderr,
        )
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", ["discover.py", "--language", "python"]), \
             mock.patch.object(discover, "detect_interpreter",
                               return_value=(["python3"], "system")), \
             mock.patch.object(discover.subprocess, "run", return_value=fake_proc), \
             contextlib.redirect_stdout(out), \
             contextlib.redirect_stderr(err):
            code = discover.main()
        return code, out.getvalue(), err.getvalue()

    def test_exit_0_prints_skill_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp)
            skill = pkg / ".agents" / "skills" / "developing-with-idfkit" / "SKILL.md"
            _touch(skill)
            code, out, _ = self._run_main(returncode=0, stdout=f"{pkg}\n")
            self.assertEqual(code, 0)
            self.assertEqual(out.strip(), str(skill.resolve()))

    def test_exit_4_when_layout_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp)
            # .agents/skills exists with some entry, but the documented
            # developing-with-idfkit/SKILL.md is absent.
            _touch(pkg / ".agents" / "skills" / "some-other-skill" / "SKILL.md")
            code, _, err = self._run_main(returncode=0, stdout=f"{pkg}\n")
            self.assertEqual(code, 4)
            self.assertIn("some-other-skill", err)
            self.assertIn(discover.DOCS_FALLBACK, err)

    def test_exit_2_when_idfkit_too_old(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp)  # installed idfkit, but no .agents/skills/ at all
            code, _, err = self._run_main(returncode=0, stdout=f"{pkg}\n")
            self.assertEqual(code, 2)
            self.assertIn("predates bundled skills", err)
            self.assertIn(discover.DOCS_FALLBACK, err)

    def test_exit_1_when_not_installed(self):
        code, _, err = self._run_main(
            returncode=1,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'idfkit'",
        )
        self.assertEqual(code, 1)
        self.assertIn("not installed", err)



def _js_package(root: Path, name: str, version: str = "1.2.3") -> Path:
    pkg = root / "node_modules" / name
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "package.json").write_text(
        json.dumps({"name": name, "version": version}), encoding="utf-8"
    )
    return pkg


class DetectLanguageTests(unittest.TestCase):
    def test_package_json_with_idfkit_dep_is_js(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "package.json").write_text(
                json.dumps({"dependencies": {"@idfkit/idfkit": "^0.5.0"}}),
                encoding="utf-8",
            )
            self.assertEqual(discover.detect_language(project), "js")

    def test_installed_package_is_js(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _js_package(project, "@idfkit/core")
            self.assertEqual(discover.detect_language(project), "js")

    def test_python_manifest_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _touch(project / "pyproject.toml")
            _js_package(project, "@idfkit/core")
            self.assertEqual(discover.detect_language(project), "python")

    def test_unrelated_package_json_is_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "package.json").write_text(
                json.dumps({"dependencies": {"react": "^18"}}), encoding="utf-8"
            )
            self.assertEqual(discover.detect_language(project), "python")

    def test_malformed_package_json_is_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "package.json").write_text("{not json", encoding="utf-8")
            self.assertEqual(discover.detect_language(project), "python")


class FindJsPackagesTests(unittest.TestCase):
    def test_resolves_from_ancestor_node_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = _js_package(root, "@idfkit/core")
            project = root / "apps" / "web"
            project.mkdir(parents=True)
            found = discover.find_js_packages(project)
            self.assertEqual(found, {"@idfkit/core": pkg.resolve()})

    def test_core_resolved_beside_facade(self):
        # pnpm layout: only the facade is linked into the project; core sits
        # beside it in the store.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = root / "store"
            facade = _js_package(store, "@idfkit/idfkit")
            core = _js_package(store, "@idfkit/core")
            project = root / "project"
            (project / "node_modules" / "@idfkit").mkdir(parents=True)
            link = project / "node_modules" / "@idfkit" / "idfkit"
            try:
                link.symlink_to(facade, target_is_directory=True)
            except OSError:
                self.skipTest("symlinks unavailable")
            found = discover.find_js_packages(project)
            self.assertEqual(found["@idfkit/idfkit"], facade.resolve())
            self.assertEqual(found["@idfkit/core"], core.resolve())


class JsInstallAdviceTests(unittest.TestCase):
    def test_lockfiles(self):
        cases = {
            "pnpm-lock.yaml": "pnpm add @idfkit/idfkit",
            "yarn.lock": "yarn add @idfkit/idfkit",
            "bun.lock": "bun add @idfkit/idfkit",
            "package-lock.json": "npm install @idfkit/idfkit",
        }
        for lockfile, expected in cases.items():
            with tempfile.TemporaryDirectory() as tmp:
                project = Path(tmp)
                _touch(project / lockfile)
                with mock.patch.object(discover, "find_git_root", return_value=None):
                    self.assertEqual(discover.js_install_advice(project), expected)

    def test_default_is_npm(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(discover, "find_git_root", return_value=None):
                self.assertEqual(
                    discover.js_install_advice(Path(tmp)),
                    "npm install @idfkit/idfkit",
                )


class JsExitCodeTests(unittest.TestCase):
    def _run(self, project: Path, *extra: str):
        return subprocess.run(
            [sys.executable, str(DISCOVER), "--project-dir", str(project), *extra],
            capture_output=True,
            text=True,
        )

    def test_exit_0_prints_bundled_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            pkg = _js_package(project, "@idfkit/core")
            skill = _touch(pkg / discover.SKILL_SUBPATH)
            result = self._run(project, "--language", "js")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(skill.resolve()))

    def test_facade_skill_preferred(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            facade = _js_package(project, "@idfkit/idfkit")
            core = _js_package(project, "@idfkit/core")
            facade_skill = _touch(facade / discover.SKILL_SUBPATH)
            _touch(core / discover.SKILL_SUBPATH)
            result = self._run(project, "--language", "js")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(facade_skill.resolve()))

    def test_auto_detects_js(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            pkg = _js_package(project, "@idfkit/core")
            skill = _touch(pkg / discover.SKILL_SUBPATH)
            result = self._run(project)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(skill.resolve()))

    def test_exit_1_when_not_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _touch(project / "pnpm-lock.yaml")
            result = self._run(project, "--language", "js")
            self.assertEqual(result.returncode, 1)
            self.assertIn("not installed", result.stderr)
            self.assertIn("pnpm add @idfkit/idfkit", result.stderr)

    def test_exit_2_points_at_version_matched_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            pkg = _js_package(project, "@idfkit/core", version="0.7.0")
            readme = _touch(pkg / "README.md")
            dts = _touch(pkg / "dist" / "index.d.ts")
            result = self._run(project, "--language", "js")
            self.assertEqual(result.returncode, 2)
            self.assertIn("ships no bundled skill", result.stderr)
            self.assertIn("@idfkit/core 0.7.0", result.stderr)
            self.assertIn(str(readme.resolve()), result.stderr)
            self.assertIn(str(dts.resolve()), result.stderr)
            self.assertIn(discover.JS_DOCS_FALLBACK, result.stderr)

    def test_exit_4_when_layout_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            pkg = _js_package(project, "@idfkit/core")
            _touch(pkg / ".agents" / "skills" / "some-other-skill" / "SKILL.md")
            result = self._run(project, "--language", "js")
            self.assertEqual(result.returncode, 4)
            self.assertIn("some-other-skill", result.stderr)

    def test_bad_language_exits_5(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(Path(tmp), "--language", "rust")
            self.assertEqual(result.returncode, 5)


if __name__ == "__main__":
    unittest.main()
