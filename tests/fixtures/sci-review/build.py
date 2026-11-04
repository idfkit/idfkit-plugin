"""Build the building-energy fixture repository for the sci-review extension.

The fixture is a git repository whose ``main`` branch holds correct baseline code and
whose ``feature`` branch adds the seeded building-energy defects and their correct
look-alikes, in Python, TypeScript and one IDF model. ``manifest.json`` beside this
script lists every seeded entry with its file, line and a unique anchor substring.

Usage::

    python3 tests/fixtures/sci-review/build.py --out DIR

``DIR`` must not exist or must be empty. Before writing anything, the script checks
that every anchor of the manifest occurs exactly once in its file on the ``feature``
branch and lies on the stated line; it exits with status 1 when a check fails.

Standard library only. Reviewing the fixture with the extension installed is a manual
step described in the sci-review quickstart (SC-012).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.json"

GIT_IDENTITY = ("-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false")


@dataclass(frozen=True)
class Entry:
    """One seeded defect or look-alike of the manifest."""

    id: str
    file: str
    line: int
    anchor: str
    description: str
    language: str
    kind: str


# ---------------------------------------------------------------------------
# Baseline (main)
# ---------------------------------------------------------------------------

README = """\
# Building-energy fixture

Fixture repository for the sci-review building-energy extension. Do not use this code.
"""

PROFILES_PY_MAIN = '''\
"""Hour-of-day profiles of EnergyPlus hourly output, read with idfkit."""

from idfkit.simulation import SQLResult


def total_energy_kwh(sql: SQLResult, meter: str) -> float:
    """Annual total of an hourly meter, in kWh; EnergyPlus reports joules."""
    ts = sql.get_timeseries(meter, frequency="Hourly")
    return sum(ts.values) / 3.6e6
'''

UNITS_PY_MAIN = '''\
"""Energy unit conversions for comparing simulated meters with utility bills."""

from idfkit.simulation import SQLResult

J_PER_KWH = 3.6e6


def meter_kwh(sql: SQLResult, meter: str, frequency: str = "Monthly") -> list[float]:
    """Values of an EnergyPlus meter in kWh; EnergyPlus reports joules."""
    return [j / J_PER_KWH for j in sql.get_timeseries(meter, frequency=frequency).values]
'''

CLIMATE_PY_MAIN = '''\
"""Climate indicators from EPW weather files, read with idfkit."""

from idfkit.weather import load_epw


def annual_mean_dry_bulb(path: str) -> float:
    """Mean dry-bulb temperature over every record of the file, in degrees Celsius."""
    temps = load_epw(path).hours.dry_bulb_temperature
    return sum(temps) / len(temps)
'''

PROFILES_TS_MAIN = """\
// Hour-of-day profiles of EPW weather data, read with idfkit.
import { parseEpw } from '@idfkit/weather';

/** Number of hourly records in the file: 8760, or 8784 in a leap year. */
export function recordCount(text: string): number {
  return parseEpw(text).hours.rowCount;
}
"""

UNITS_TS_MAIN = """\
// Energy unit conversions for EnergyPlus meters and utility bills.
import type { WeatherFile } from '@idfkit/weather';

export interface Site {
  weather: WeatherFile;
  billKbtu: number[];
}

export const J_PER_KWH = 3.6e6;

/** An EnergyPlus meter value converted from joules to kWh. */
export const joulesToKwh = (joules: number): number => joules / J_PER_KWH;
"""

CLIMATE_TS_MAIN = """\
// Climate indicators from EPW weather files, read with idfkit.
import { parseEpw } from '@idfkit/weather';

/** Mean dry-bulb temperature over every record of the file, in degrees Celsius. */
export function annualMeanDryBulb(text: string): number {
  const t = parseEpw(text).hours.dryBulbTemperature;
  return t.reduce((a, b) => a + b, 0) / t.length;
}
"""

IDF_HEAD = """\
Version,
  26.2;                       !- Version Identifier

Building,
  Small Office,               !- Name
  0,                          !- North Axis {deg}
  Suburbs,                    !- Terrain
  0.04,                       !- Loads Convergence Tolerance Value {W}
  0.4,                        !- Temperature Convergence Tolerance Value {deltaC}
  FullExterior,               !- Solar Distribution
  25,                         !- Maximum Number of Warmup Days
  6;                          !- Minimum Number of Warmup Days

Timestep,
  4;                          !- Number of Timesteps per Hour

SimulationControl,
  No,                         !- Do Zone Sizing Calculation
  No,                         !- Do System Sizing Calculation
  No,                         !- Do Plant Sizing Calculation
  No,                         !- Run Simulation for Sizing Periods
  Yes;                        !- Run Simulation for Weather File Run Periods

RunPeriod,
  Annual,                     !- Name
  1,                          !- Begin Month
  1,                          !- Begin Day of Month
  ,                           !- Begin Year
  12,                         !- End Month
  31,                         !- End Day of Month
  ;                           !- End Year

GlobalGeometryRules,
  UpperLeftCorner,            !- Starting Vertex Position
  Counterclockwise,           !- Vertex Entry Direction
  Relative;                   !- Coordinate System

Material,
  Brick 100mm,                !- Name
  MediumRough,                !- Roughness
  0.1,                        !- Thickness {m}
  0.89,                       !- Conductivity {W/m-K}
  1920,                       !- Density {kg/m3}
  790;                        !- Specific Heat {J/kg-K}

Construction,
  Exterior Wall,              !- Name
  Brick 100mm;                !- Outside Layer

Zone,
  Office;                     !- Name

BuildingSurface:Detailed,
  Office South Wall,          !- Name
  Wall,                       !- Surface Type
  Exterior Wall,              !- Construction Name
  Office,                     !- Zone Name
  ,                           !- Space Name
  Outdoors,                   !- Outside Boundary Condition
  ,                           !- Outside Boundary Condition Object
  SunExposed,                 !- Sun Exposure
  WindExposed,                !- Wind Exposure
  ,                           !- View Factor to Ground
  4,                          !- Number of Vertices
  0, 0, 3,                    !- Vertex 1 Xcoordinate, Ycoordinate, Zcoordinate {m}
  0, 0, 0,                    !- Vertex 2
  10, 0, 0,                   !- Vertex 3
  10, 0, 3;                   !- Vertex 4
"""

# ---------------------------------------------------------------------------
# Additions on the feature branch: seeded defects and look-alikes
# ---------------------------------------------------------------------------

PROFILES_PY_FEATURE = (
    PROFILES_PY_MAIN.replace(
        "from idfkit.simulation import SQLResult\n",
        "from datetime import timedelta\n\nfrom idfkit.simulation import SQLResult\n",
    )
    + '''

def lighting_profile_kwh(sql: SQLResult, zone: str) -> list[float]:
    """Mean lighting energy for each clock hour, in kWh; hour 0 is 00:00 to 01:00."""
    ts = sql.get_timeseries("Zone Lights Electricity Energy", zone, frequency="Hourly")
    profile = [0.0] * 24
    for t, v in zip(ts.timestamps, ts.values):
        profile[t.hour] += v / 3.6e6
    days = len(ts.values) / 24
    return [p / days for p in profile]


def cooling_profile_kwh(sql: SQLResult, zone: str) -> list[float]:
    """Mean sensible cooling energy for each clock hour, in kWh; hour 0 is 00:00 to 01:00."""
    ts = sql.get_timeseries("Zone Air System Sensible Cooling Energy", zone, frequency="Hourly")
    step = timedelta(hours=1)
    profile = [0.0] * 24
    for t, v in zip(ts.timestamps, ts.values):
        profile[(t - step).hour] += v / 3.6e6
    days = len(ts.values) / 24
    return [p / days for p in profile]
'''
)

UNITS_PY_FEATURE = (
    UNITS_PY_MAIN.replace(
        "J_PER_KWH = 3.6e6\n",
        "J_PER_KWH = 3.6e6\nKWH_PER_KBTU = 3.412\n",
    )
    + '''

def bill_kwh(bill_kbtu: list[float]) -> list[float]:
    """Utility bill quantities converted from kBtu to kWh."""
    return [b * KWH_PER_KBTU for b in bill_kbtu]


def site_kbtu(kwh: float) -> float:
    """Site energy converted from kWh to kBtu."""
    return kwh * 3.412141633


def calibration_error(sql: SQLResult, bill_kbtu: list[float]) -> list[float]:
    """Monthly relative error of the simulated electricity meter against the utility bill."""
    simulated = meter_kwh(sql, "Electricity:Facility")
    return [(s - b) / b for s, b in zip(simulated, bill_kwh(bill_kbtu))]
'''
)

CLIMATE_PY_FEATURE = (
    CLIMATE_PY_MAIN
    + '''

def heating_degree_hours(path: str, base_c: float = 18.0) -> float:
    """Heating degree-hours of the file's year, in K h."""
    temps = load_epw(path).hours.dry_bulb_temperature[:8760]
    return sum(max(0.0, base_c - t) for t in temps)


def tmy_hourly_means(path: str) -> list[float]:
    """Mean dry-bulb temperature for each clock hour of a typical year; other years are rejected."""
    temps = load_epw(path).hours.dry_bulb_temperature
    if len(temps) != 8760:
        raise ValueError(f"expected a typical year of 8760 hours, got {len(temps)}")
    return [sum(temps[h::24]) / 365 for h in range(24)]


def wall_heat_loss_w(u_value: float, area_m2: float, t_in_c: float, t_out_c: float) -> float:
    """Steady conduction through a wall, in W."""
    return u_value * area_m2 * (t_in_c - t_out_c)
'''
)

PROFILES_TS_FEATURE = (
    PROFILES_TS_MAIN
    + """
/** Mean dry-bulb temperature for each clock hour; index 0 is 00:00 to 01:00. */
export function hourlyMeanDryBulb(text: string): number[] {
  const { hours } = parseEpw(text);
  const sum = new Array<number>(24).fill(0);
  for (let i = 0; i < hours.rowCount; i++) {
    sum[hours.hour[i] % 24] += hours.dryBulbTemperature[i];
  }
  return sum.map((s) => s / (hours.rowCount / 24));
}

/** Mean global horizontal radiation for each clock hour, in Wh/m2; index 0 is 00:00 to 01:00. */
export function hourlyMeanGlobalHorizontal(text: string): number[] {
  const { hours } = parseEpw(text);
  const sum = new Array<number>(24).fill(0);
  for (let i = 0; i < hours.rowCount; i++) {
    sum[hours.hour[i] - 1] += hours.globalHorizontalRadiation[i];
  }
  return sum.map((s) => s / (hours.rowCount / 24));
}
"""
)

UNITS_TS_FEATURE = (
    UNITS_TS_MAIN
    + """
/** Utility bill quantities converted from kBtu to kWh. */
export function billedKwh(site: Site): number[] {
  return site.billKbtu.map((kbtu) => kbtu / 0.29307107);
}

/** Site energy converted from kWh to kBtu. */
export const kwhToKbtu = (kwh: number): number => kwh / 0.29307107;
"""
)

CLIMATE_TS_FEATURE = (
    CLIMATE_TS_MAIN
    + """
/** Heating degree-hours of the file's year, in K h. */
export function heatingDegreeHours(text: string, baseC = 18): number {
  const t = parseEpw(text).hours.dryBulbTemperature;
  let total = 0;
  for (let i = 0; i < 8760; i++) total += Math.max(0, baseC - t[i]);
  return total;
}

/** Daily mean dry-bulb temperatures, one for each day of the file's year. */
export function dailyMeans(text: string): number[] {
  const { hours } = parseEpw(text);
  const days = hours.rowCount / 24;
  const means: number[] = [];
  for (let d = 0; d < days; d++) {
    let sum = 0;
    for (let h = 0; h < 24; h++) sum += hours.dryBulbTemperature[d * 24 + h];
    means.push(sum / 24);
  }
  return means;
}
"""
)

IDF_FEATURE_SURFACES = """
BuildingSurface:Detailed,
  Office North Wall,          !- Name
  Wall,                       !- Surface Type
  Exterior Wall Insulated,    !- Construction Name
  Office,                     !- Zone Name
  ,                           !- Space Name
  Outdoors,                   !- Outside Boundary Condition
  ,                           !- Outside Boundary Condition Object
  SunExposed,                 !- Sun Exposure
  WindExposed,                !- Wind Exposure
  ,                           !- View Factor to Ground
  4,                          !- Number of Vertices
  10, 8, 3,                   !- Vertex 1 Xcoordinate, Ycoordinate, Zcoordinate {m}
  10, 8, 0,                   !- Vertex 2
  0, 8, 0,                    !- Vertex 3
  0, 8, 3;                    !- Vertex 4

BuildingSurface:Detailed,
  Office East Wall,           !- Name
  Wall,                       !- Surface Type
  exterior wall,              !- Construction Name
  Office,                     !- Zone Name
  ,                           !- Space Name
  Outdoors,                   !- Outside Boundary Condition
  ,                           !- Outside Boundary Condition Object
  SunExposed,                 !- Sun Exposure
  WindExposed,                !- Wind Exposure
  ,                           !- View Factor to Ground
  4,                          !- Number of Vertices
  10, 0, 3,                   !- Vertex 1 Xcoordinate, Ycoordinate, Zcoordinate {m}
  10, 0, 0,                   !- Vertex 2
  10, 8, 0,                   !- Vertex 3
  10, 8, 3;                   !- Vertex 4
"""

MAIN_FILES: dict[str, str] = {
    "README.md": README,
    "src/bem/profiles.py": PROFILES_PY_MAIN,
    "src/bem/units.py": UNITS_PY_MAIN,
    "src/bem/climate.py": CLIMATE_PY_MAIN,
    "src/bem/profiles.ts": PROFILES_TS_MAIN,
    "src/bem/units.ts": UNITS_TS_MAIN,
    "src/bem/climate.ts": CLIMATE_TS_MAIN,
    "models/office.idf": IDF_HEAD,
}

FEATURE_FILES: dict[str, str] = {
    "src/bem/profiles.py": PROFILES_PY_FEATURE,
    "src/bem/units.py": UNITS_PY_FEATURE,
    "src/bem/climate.py": CLIMATE_PY_FEATURE,
    "src/bem/profiles.ts": PROFILES_TS_FEATURE,
    "src/bem/units.ts": UNITS_TS_FEATURE,
    "src/bem/climate.ts": CLIMATE_TS_FEATURE,
    "models/office.idf": IDF_HEAD + IDF_FEATURE_SURFACES,
}


def load_manifest(path: Path = MANIFEST) -> list[Entry]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Entry(**item) for item in data["entries"]]


def check_anchors(entries: list[Entry], files: dict[str, str]) -> list[str]:
    """Return one message per entry whose anchor is missing, repeated or on another line."""
    problems: list[str] = []
    for entry in entries:
        if entry.kind not in ("defect", "lookalike"):
            problems.append(f"{entry.id}: kind {entry.kind!r} is neither 'defect' nor 'lookalike'")
        text = files.get(entry.file)
        if text is None:
            problems.append(f"{entry.id}: file {entry.file} is not written on the feature branch")
            continue
        count = text.count(entry.anchor)
        if count != 1:
            problems.append(f"{entry.id}: anchor {entry.anchor!r} occurs {count} times in {entry.file}")
            continue
        line = text[: text.index(entry.anchor)].count("\n") + 1
        if line != entry.line:
            problems.append(f"{entry.id}: anchor is on line {line} of {entry.file}, manifest says {entry.line}")
    ids = [entry.id for entry in entries]
    for duplicate in sorted({i for i in ids if ids.count(i) > 1}):
        problems.append(f"{duplicate}: id is listed more than once")
    return problems


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *GIT_IDENTITY, *args], cwd=repo, check=True, capture_output=True, text=True)


def write_files(repo: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


def build(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    git(out, "init", "--quiet")
    git(out, "symbolic-ref", "HEAD", "refs/heads/main")
    write_files(out, MAIN_FILES)
    git(out, "add", "--all")
    git(out, "commit", "--quiet", "-m", "Baseline: correct building-energy helpers and model")
    git(out, "checkout", "--quiet", "-b", "feature")
    write_files(out, FEATURE_FILES)
    git(out, "add", "--all")
    git(out, "commit", "--quiet", "-m", "Add profiles, bill conversion, degree-hours and two walls")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=Path, help="directory to create the repository in")
    args = parser.parse_args(argv)

    entries = load_manifest()
    problems = check_anchors(entries, FEATURE_FILES)
    if problems:
        for problem in problems:
            print(f"manifest check failed: {problem}", file=sys.stderr)
        return 1

    out: Path = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        print(f"{out} exists and is not empty", file=sys.stderr)
        return 1
    build(out)

    on_disk = {relative: (out / relative).read_text(encoding="utf-8") for relative in FEATURE_FILES}
    problems = check_anchors(entries, on_disk)
    if problems:
        for problem in problems:
            print(f"built repository check failed: {problem}", file=sys.stderr)
        return 1

    defects = sum(1 for e in entries if e.kind == "defect")
    print(f"built {out} (branches main and feature); {defects} defects and {len(entries) - defects} look-alikes")
    print(f"anchors check passed for {len(entries)} manifest entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
