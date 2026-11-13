#!/usr/bin/env python3
"""Inventory archetypal / eppy / geomeppy usage in a Python codebase.

Usage: python inventory.py <repo-root> [--json]

Reports, without importing the project:
- files (and notebooks) that import the old libraries,
- call counts per old-library API (attribute calls such as `.newidfobject(`),
- constructor calls of names imported from the old libraries (`IDF(`, `Sql(`, ...),
- the files where those calls concentrate,
- public functions, class attributes and module attributes whose annotations
  expose old-library types: the breaking surface for downstream consumers
  (tests are listed separately).

Re-run it at the end of a migration: old-library imports should be gone, and the
only old-API name left should be `removeidfobject`, which is idfkit's own method.

Standard library only, so it runs before any dependency is installed.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

OLD_LIBS = ("archetypal", "eppy", "geomeppy")

# Attribute calls that indicate old-library model/results usage. Names such as
# simulate/rotate/scale/translate can also match the project's own methods.
OLD_CALLS = (
    "idfobjects", "getobject", "newidfobject", "removeidfobject", "removeallidfobjects",
    "copyidfobject", "addidfobject", "addidfobjects", "saveas", "idfstr", "simulate",
    "sql_file", "simulation_files", "as_version", "add_block", "add_shading_block",
    "intersect_match", "set_wwr", "set_default_constructions", "bounding_box",
    "translate", "rotate", "scale", "to_year_week_day", "to_epbunch", "from_epbunch",
    "from_values", "constant_schedule", "add_year_to_idf", "timeseries_by_name",
    "tabular_data_by_name", "total_building_area",
)
OLD_TYPES = ("IDF", "Sql", "EpBunch", "Schedule", "ScheduleTypeLimits", "EnergyPlusVersion", "EnergyDataFrame")
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".tox", ".mypy_cache", ".ruff_cache"}
CALL_RE = re.compile(r"\.(%s)\b" % "|".join(OLD_CALLS))
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+(%s)\b[\w.]*" % "|".join(OLD_LIBS), re.M)


def iter_sources(root: Path):
    """Yield (relative path, kind, source) for .py files and notebook code."""
    for path in sorted(root.rglob("*")):
        rel_parts = path.relative_to(root).parts
        if SKIP_DIRS.intersection(rel_parts) or not path.is_file():
            continue
        if path.suffix == ".py":
            yield str(path.relative_to(root)), "py", path.read_text(encoding="utf-8", errors="replace")
        elif path.suffix == ".ipynb":
            try:
                nb = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue
            cells = [
                "".join(c.get("source", [])) if isinstance(c.get("source"), list) else c.get("source", "")
                for c in nb.get("cells", [])
                if c.get("cell_type") == "code"
            ]
            # Drop IPython magics so the code parses.
            code = "\n".join(line for cell in cells for line in cell.splitlines() if not line.lstrip().startswith(("%", "!")))
            yield str(path.relative_to(root)), "ipynb", code


def is_test(rel: str) -> bool:
    parts = Path(rel).parts
    return "tests" in parts or "test" in parts or Path(rel).name.startswith("test_")


def imported_old_names(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Return (old modules imported, names bound from old libraries)."""
    modules, names = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in OLD_LIBS:
                    modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in OLD_LIBS:
            modules.add(node.module)
            names.update(a.asname or a.name for a in node.names)
    return modules, names


def mentions(node: ast.AST | None, types: set[str]) -> bool:
    if node is None:
        return False
    text = ast.unparse(node)
    return any(re.search(rf"\b{re.escape(t)}\b", text) for t in types)


def surface_entries(tree: ast.Module, types: set[str]):
    """Public functions/methods, class attributes and module attributes exposing `types`."""
    def visit(body, owner: str | None):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
                if mentions(node.returns, types) or any(mentions(a.annotation, types) for a in args):
                    yield node.lineno, f"{owner}.{node.name}" if owner else node.name, "function"
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                yield from visit(node.body, node.name)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
                if not name.startswith("_") and mentions(node.annotation, types):
                    kind = "class attribute" if owner else "module attribute"
                    yield node.lineno, f"{owner}.{name}" if owner else name, kind
    yield from visit(tree.body, None)


def scan(root: Path) -> dict:
    importers: dict[str, list[str]] = {}
    calls: Counter[str] = Counter()
    constructors: Counter[str] = Counter()
    per_file: dict[str, int] = defaultdict(int)
    surface: list[dict] = []
    unparsable: list[str] = []

    for rel, kind, src in iter_sources(root):
        try:
            tree = ast.parse(src)
            modules, bound = imported_old_names(tree)
        except SyntaxError:
            tree = None
            modules = {m.group(0).split()[-1] for m in IMPORT_RE.finditer(src)}
            bound = set()
            if modules or CALL_RE.search(src):
                unparsable.append(rel)
        if modules:
            importers[rel] = sorted(modules)
        for m in CALL_RE.finditer(src):
            calls[m.group(1)] += 1
            per_file[rel] += 1
        if tree is None or not bound:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in bound:
                constructors[node.func.id] += 1
                per_file[rel] += 1
        types = bound.intersection(OLD_TYPES)
        if types and kind == "py":
            for line, name, what in surface_entries(tree, types):
                surface.append({"file": rel, "line": line, "name": name, "kind": what, "test": is_test(rel)})

    surface.sort(key=lambda d: (d["file"], d["line"]))
    return {
        "importers": importers,
        "calls": dict(calls.most_common()),
        "constructor_calls": dict(constructors.most_common()),
        "hotspots": sorted(({"file": f, "calls": n} for f, n in per_file.items()), key=lambda d: (-d["calls"], d["file"])),
        "breaking_surface": [s for s in surface if not s["test"]],
        "test_surface": [s for s in surface if s["test"]],
        "unparsable": unparsable,
    }


def print_report(report: dict) -> None:
    print(f"Files importing {', '.join(OLD_LIBS)}: {len(report['importers'])}")
    for f, mods in report["importers"].items():
        print(f"  {f}: {', '.join(mods)}")
    print("\nOld-library attribute calls (name: count):")
    for name, n in report["calls"].items():
        print(f"  {name}: {n}")
    print("\nConstructor/function calls of names imported from the old libraries:")
    for name, n in report["constructor_calls"].items():
        print(f"  {name}(: {n}")
    print("\nHotspots (files by old-library call count):")
    for h in report["hotspots"][:15]:
        print(f"  {h['calls']:4d}  {h['file']}")
    print(f"\nBreaking surface: public API exposing old-library types ({len(report['breaking_surface'])}):")
    for s in report["breaking_surface"]:
        print(f"  {s['file']}:{s['line']}  {s['name']}  [{s['kind']}]")
    print(f"\nTest code exposing old-library types: {len(report['test_surface'])} (see --json)")
    if report["unparsable"]:
        print("\nCould not parse (regex counts only):", ", ".join(report["unparsable"]))
    print(
        "\nNote: attribute names such as simulate/rotate/scale/translate also match the project's own methods; "
        "confirm hotspots by reading them."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = parser.parse_args()
    if not args.root.is_dir():
        print(f"not a directory: {args.root}", file=sys.stderr)
        return 2
    report = scan(args.root.resolve())
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
