#!/usr/bin/env python3
"""Discover the bundled agent-skills SKILL.md of the idfkit a project uses.

Usage:
    python scripts/discover.py [--project-dir PATH] [--language {auto,python,js}]

idfkit has two implementations: the Python package `idfkit` (PyPI) and the
JavaScript/TypeScript line `@idfkit/*` (npm). `--language` picks which one to
resolve; `auto` (the default) picks `js` when the project directory has a
`package.json` naming an `@idfkit/` package or an installed `@idfkit/` package
in reach, and no Python project manifest, and `python` otherwise.

Python: when --project-dir is given, the script resolves `.venv`, `../.venv`,
`<git-root>/.venv`, `Pipfile`, and the `poetry.lock`/`pdm.lock`/`uv.lock`
lockfiles (each paired with a `pyproject.toml`) relative to that path (so its
checks land on the user's project rather than on the script's installed
location). An active conda `base` environment is ignored, since `CONDA_PREFIX`
is exported merely by initializing conda.

JavaScript: the script walks `node_modules/` up from --project-dir, the way
Node resolves a bare specifier, for `@idfkit/idfkit` (the shared install name)
and then `@idfkit/core`. No Node interpreter is needed. Yarn Plug'n'Play
installs, which have no `node_modules/`, are not resolved.

Exit codes:
    0 - success; prints the absolute path to the bundled SKILL.md on stdout.
    1 - idfkit is not installed (Python: in the detected interpreter;
        JS: no `@idfkit/idfkit` or `@idfkit/core` under any `node_modules/`).
    2 - idfkit is installed but ships no bundled skill (Python: < 0.13, no
        .agents/skills/; JS: the installed release ships none). The error
        names version-matched fallbacks.
    3 - no usable Python interpreter was found (Python only).
    4 - .agents/skills/ exists but the expected developing-with-idfkit/SKILL.md
        is missing from the documented sub-path (likely upstream restructured).
        The agent should read the listed available skills directly.
    5 - invalid script argument.

On non-zero exit, a human-readable "ERROR:" block is printed on stderr.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DOCS_FALLBACK = "https://docs.idfkit.com"
JS_DOCS_FALLBACK = "https://js.idfkit.com"

# The npm packages that may carry the bundled skill, in lookup order.
# `@idfkit/idfkit` is the shared install name; `@idfkit/core` is the library
# itself and what every JS install has, directly or through the facade.
JS_PACKAGES = ("@idfkit/idfkit", "@idfkit/core")

SKILL_SUBPATH = Path(".agents") / "skills" / "developing-with-idfkit" / "SKILL.md"

# Files whose presence marks a Python project, for `--language auto`.
PYTHON_MARKERS = (
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "Pipfile",
)


def find_venv_python(venv_root: Path) -> Path | None:
    """Return the venv's Python executable, cross-platform.

    POSIX venvs put it at bin/python; Windows venvs put it at Scripts/python.exe.
    """
    for candidate in (
        venv_root / "bin" / "python",
        venv_root / "Scripts" / "python.exe",
    ):
        if candidate.is_file():
            return candidate
    return None


def find_git_root(start: Path) -> Path | None:
    """Walk up from `start` looking for a `.git` directory or file.

    Returns the directory containing `.git` (the repo root), or None if no git
    repository is found above `start`. Handles the worktree case where `.git`
    is a file pointing at the real repo dir.
    """
    for ancestor in [start, *start.parents]:
        if (ancestor / ".git").exists():
            return ancestor
    return None


def detect_interpreter(project_dir: Path) -> tuple[list[str], str] | None:
    """Pick the right Python interpreter, in documented priority order.

    Returns ``(cmd, tag)`` where ``cmd`` is the command for ``subprocess.run``
    and ``tag`` identifies which detection branch fired (``virtual-env``,
    ``venv-local``, ``venv-parent``, ``venv-git-root``, ``conda``, ``pipenv``,
    ``poetry``, ``pdm``, ``uv``, or ``system``). The tag lets callers give
    targeted install advice on exit 1 instead of a buffet of unrelated
    package-manager commands.
    """
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        py = find_venv_python(Path(venv))
        if py:
            return [str(py)], "virtual-env"

    py = find_venv_python(project_dir / ".venv")
    if py:
        return [str(py)], "venv-local"

    py = find_venv_python(project_dir.parent / ".venv")
    if py:
        return [str(py)], "venv-parent"

    # Walk up to the git repo root and look for a `.venv` there. Helpful for
    # monorepos where the project's venv lives at repo root but the agent's
    # cwd / --project-dir points deep into a subdirectory.
    git_root = find_git_root(project_dir)
    if (
        git_root is not None
        and git_root != project_dir
        and git_root != project_dir.parent
    ):
        py = find_venv_python(git_root / ".venv")
        if py:
            return [str(py)], "venv-git-root"

    conda = os.environ.get("CONDA_PREFIX")
    # CONDA_PREFIX is exported pointing at `base` whenever conda is merely
    # initialized, even with no project env active. Firing on that would advise
    # `conda install ... idfkit` into base — the anti-pattern this branch avoids.
    if (
        conda
        and Path(conda).name != "base"
        and os.environ.get("CONDA_DEFAULT_ENV") != "base"
    ):
        py = find_venv_python(Path(conda))
        if py:
            return [str(py)], "conda"

    if shutil.which("pipenv") and (project_dir / "Pipfile").is_file():
        return ["pipenv", "run", "python"], "pipenv"

    # poetry/pdm/uv only manage a project when a manifest is present. A bare
    # lockfile makes them emit "could not find a pyproject.toml" on stderr
    # instead of letting us give install advice, so require the manifest too.
    has_pyproject = (project_dir / "pyproject.toml").is_file()

    if (
        shutil.which("poetry")
        and (project_dir / "poetry.lock").is_file()
        and has_pyproject
    ):
        return ["poetry", "run", "python"], "poetry"

    if (
        shutil.which("pdm")
        and (project_dir / "pdm.lock").is_file()
        and has_pyproject
    ):
        return ["pdm", "run", "python"], "pdm"

    if (
        shutil.which("uv")
        and (project_dir / "uv.lock").is_file()
        and has_pyproject
    ):
        return ["uv", "run", "--quiet", "python"], "uv"

    for name in ("python3", "python"):
        if shutil.which(name):
            return [name], "system"

    return None


def install_advice(cmd: list[str], tag: str) -> str:
    """Return the package-manager-appropriate install command for the detected
    interpreter.

    ``detect_interpreter`` already chose a branch; we know which tool to
    suggest. Dumping every install command and asking the agent to "match the
    tool for your project" is how a poetry project gets a stray
    ``pip install idfkit`` outside the lockfile.
    """
    if tag in {"virtual-env", "venv-local", "venv-parent", "venv-git-root"}:
        # Use the venv's own python to run pip — independent of activation
        # state on the user's shell.
        return f"{cmd[0]} -m pip install idfkit"
    if tag == "conda":
        return "conda install -c conda-forge idfkit"
    if tag == "pipenv":
        return "pipenv install idfkit"
    if tag == "poetry":
        return "poetry add idfkit"
    if tag == "pdm":
        return "pdm add idfkit"
    if tag == "uv":
        return "uv add idfkit"
    # tag == "system" (or unknown — defensive)
    return (
        f"{cmd[0]} -m pip install idfkit\n"
        "    (better: create a project venv first with "
        "`python -m venv .venv && source .venv/bin/activate`)"
    )


def find_node_package(name: str, start: Path) -> Path | None:
    """Resolve an installed npm package directory the way Node does.

    Walks ``start`` and its ancestors for ``node_modules/<name>/package.json``
    and returns the package directory with symlinks resolved (pnpm links every
    package into its store, where its own dependencies sit beside it).
    """
    for ancestor in [start, *start.parents]:
        manifest = ancestor / "node_modules" / name / "package.json"
        if manifest.is_file():
            return manifest.parent.resolve()
    return None


def find_js_packages(project_dir: Path) -> dict[str, Path]:
    """Return the installed ``JS_PACKAGES`` reachable from ``project_dir``.

    ``@idfkit/core`` is also looked up from the facade's resolved location,
    since under pnpm it is not hoisted next to the project.
    """
    found: dict[str, Path] = {}
    for name in JS_PACKAGES:
        pkg = find_node_package(name, project_dir)
        if pkg is None and found:
            pkg = find_node_package(name, next(iter(found.values())))
        if pkg is not None:
            found[name] = pkg
    return found


def package_json_names_idfkit(project_dir: Path) -> bool:
    """True when ``project_dir/package.json`` declares any ``@idfkit/`` package."""
    manifest = project_dir / "package.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    for field in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ):
        deps = data.get(field)
        if isinstance(deps, dict) and any(
            str(k).startswith("@idfkit/") for k in deps
        ):
            return True
    return False


def detect_language(project_dir: Path) -> str:
    """Pick ``python`` or ``js`` for ``--language auto``.

    JS only when the project shows idfkit-js and nothing Python: a project with
    both should be resolved with an explicit ``--language``.
    """
    if any((project_dir / m).is_file() for m in PYTHON_MARKERS):
        return "python"
    if package_json_names_idfkit(project_dir) or find_js_packages(project_dir):
        return "js"
    return "python"


def js_install_advice(project_dir: Path) -> str:
    """Return the install command for the project's JS package manager,
    chosen by lockfile in ``project_dir`` or, failing that, its git root."""
    roots = [project_dir]
    git_root = find_git_root(project_dir)
    if git_root is not None and git_root != project_dir:
        roots.append(git_root)
    for root in roots:
        if (root / "pnpm-lock.yaml").is_file():
            return "pnpm add @idfkit/idfkit"
        if (root / "yarn.lock").is_file():
            return "yarn add @idfkit/idfkit"
        if (root / "bun.lock").is_file() or (root / "bun.lockb").is_file():
            return "bun add @idfkit/idfkit"
        if (root / "package-lock.json").is_file():
            return "npm install @idfkit/idfkit"
    return "npm install @idfkit/idfkit"


def package_version(pkg: Path) -> str:
    try:
        data = json.loads((pkg / "package.json").read_text(encoding="utf-8"))
        return str(data.get("version", "unknown"))
    except (OSError, ValueError, AttributeError):
        return "unknown"


def discover_js(project_dir: Path) -> int:
    packages = find_js_packages(project_dir)
    if not packages:
        print(
            "ERROR: idfkit-js is not installed in this project.\n"
            f"Searched:      node_modules/ from {project_dir} upward for\n"
            f"               {', '.join(JS_PACKAGES)}\n"
            "\n"
            f"Install with:  {js_install_advice(project_dir)}\n"
            "\n"
            "Then re-run this script. If the project is a Yarn Plug'n'Play install\n"
            "(no node_modules/), read the docs instead:\n"
            f"  {JS_DOCS_FALLBACK}",
            file=sys.stderr,
        )
        return 1

    for pkg in packages.values():
        skill = pkg / SKILL_SUBPATH
        if skill.is_file():
            print(skill)
            return 0

    for name, pkg in packages.items():
        agents_skills_dir = pkg / SKILL_SUBPATH.parent.parent
        if agents_skills_dir.is_dir():
            print(
                f"ERROR: {name}'s bundled skills directory exists, but the expected\n"
                "developing-with-idfkit/SKILL.md is missing from the documented sub-path.\n"
                "This usually means upstream idfkit-js reorganized the skill layout.\n"
                "\n"
                f"Package path: {pkg}\n"
                f"Bundled skills directory: {agents_skills_dir}\n"
                "Available entries:",
                file=sys.stderr,
            )
            for entry in sorted(agents_skills_dir.iterdir()):
                print(f"  {entry.name}", file=sys.stderr)
            print(
                "\n"
                "Read whichever skill best matches the user's task. If none match,\n"
                "fall back to the idfkit-js documentation:\n"
                f"  {JS_DOCS_FALLBACK}",
                file=sys.stderr,
            )
            return 4

    # No bundled skill. The installed package still carries version-matched
    # material: its README and its type declarations, which hold the TSDoc.
    lines = []
    for name, pkg in packages.items():
        lines.append(f"  {name} {package_version(pkg)}  ({pkg})")
    references = []
    for pkg in packages.values():
        for rel in ("README.md", "dist/index.d.ts", "dist/node.d.ts", "index.d.ts"):
            candidate = pkg / rel
            if candidate.is_file():
                references.append(f"  {candidate}")
    print(
        "ERROR: idfkit-js is installed but ships no bundled skill.\n"
        "Installed:\n" + "\n".join(lines) + "\n"
        "\n"
        "Read these version-matched files from the installed package instead\n"
        "(the .d.ts entry points re-export from sibling .d.ts files, which carry\n"
        "the TSDoc for every export):\n"
        + ("\n".join(references) if references else "  (none found)") + "\n"
        "\n"
        "and the idfkit-js documentation for task-oriented guides:\n"
        f"  {JS_DOCS_FALLBACK}",
        file=sys.stderr,
    )
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover the bundled developing-with-idfkit SKILL.md "
        "(Python idfkit or idfkit-js).",
    )
    parser.add_argument(
        "--project-dir",
        default=None,
        help="Absolute path to the user's project directory. Defaults to cwd.",
    )
    parser.add_argument(
        "--language",
        choices=("auto", "python", "js"),
        default="auto",
        help="Which idfkit to resolve: the Python package or the JS/TS @idfkit/* "
        "packages. Defaults to auto-detection from the project directory.",
    )
    try:
        args = parser.parse_args()
    except SystemExit as e:
        return 5 if e.code else 0

    if args.project_dir is not None:
        project_dir = Path(args.project_dir)
        if not project_dir.is_dir():
            print(
                f"ERROR: --project-dir is not a directory: {project_dir}",
                file=sys.stderr,
            )
            return 5
    else:
        project_dir = Path.cwd()
    project_dir = project_dir.resolve()

    language = args.language
    if language == "auto":
        language = detect_language(project_dir)
    if language == "js":
        return discover_js(project_dir)

    detection = detect_interpreter(project_dir)
    if detection is None:
        print(
            "ERROR: No Python interpreter found.\n"
            "Install Python 3.10+ (the easiest path is `uv` — see "
            "https://docs.astral.sh/uv/),\n"
            "then install idfkit (pip install idfkit) and re-run.",
            file=sys.stderr,
        )
        return 3

    cmd, tag = detection
    py_display = " ".join(cmd)

    probe = "import idfkit; print(idfkit.__path__[0])"
    try:
        result = subprocess.run(
            [*cmd, "-c", probe],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        print(
            f"ERROR: import idfkit timed out (interpreter: {py_display})",
            file=sys.stderr,
        )
        return 1
    except FileNotFoundError:
        print(
            f"ERROR: detected interpreter not found on PATH: {py_display}",
            file=sys.stderr,
        )
        return 3

    if result.returncode != 0:
        combined = (result.stderr or "") + (result.stdout or "")
        if "ModuleNotFoundError" in combined:
            advice = install_advice(cmd, tag)
            extra = ""
            if tag == "system":
                # No env-manager artifact found. The user might still have one
                # (hatch, pyenv-virtualenv, an unactivated conda env) we
                # couldn't auto-detect.
                extra = (
                    "\n\nIf your project uses an environment manager we did not\n"
                    "auto-detect (hatch, pyenv-virtualenv, an unactivated conda env),\n"
                    "ACTIVATE it first so the right Python is found, then re-run."
                )
            print(
                "ERROR: idfkit is not installed in the detected Python environment.\n"
                f"Interpreter:   {py_display}\n"
                f"Detected via:  {tag}\n"
                "\n"
                f"Install with:  {advice}\n"
                "\n"
                f"Then re-run this script.{extra}",
                file=sys.stderr,
            )
            return 1
        print(
            "ERROR: Failed to import idfkit.\n"
            f"Interpreter: {py_display}\n"
            "Output:\n"
            f"{combined}",
            file=sys.stderr,
        )
        return 1

    idfkit_path = Path(result.stdout.strip()).resolve()
    agents_skills_dir = idfkit_path / ".agents" / "skills"
    primary_skill = agents_skills_dir / "developing-with-idfkit" / "SKILL.md"

    if primary_skill.is_file():
        print(primary_skill)
        return 0

    if agents_skills_dir.is_dir():
        print(
            "ERROR: idfkit's bundled skills directory exists, but the expected\n"
            "developing-with-idfkit/SKILL.md is missing from the documented sub-path.\n"
            "This usually means upstream idfkit reorganized the skill layout.\n"
            "\n"
            f"idfkit path: {idfkit_path}\n"
            f"Bundled skills directory: {agents_skills_dir}\n"
            "Available entries:",
            file=sys.stderr,
        )
        for entry in sorted(agents_skills_dir.iterdir()):
            print(f"  {entry.name}", file=sys.stderr)
        print(
            "\n"
            "Read whichever skill best matches the user's task. If none match,\n"
            "fall back to the idfkit documentation:\n"
            f"  {DOCS_FALLBACK}",
            file=sys.stderr,
        )
        return 4

    print(
        "ERROR: idfkit is installed but predates bundled skills (< 0.13).\n"
        f"Interpreter: {py_display}\n"
        f"idfkit path: {idfkit_path}\n"
        "\n"
        "For best results, upgrade to get version-matched bundled skills:\n"
        "  pip install --upgrade idfkit\n"
        "\n"
        "If upgrading isn't an option, fall back to the idfkit documentation:\n"
        f"  {DOCS_FALLBACK}",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
