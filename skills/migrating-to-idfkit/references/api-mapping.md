# archetypal / eppy / geomeppy → idfkit native API

Checked against idfkit 1.2. Signatures drift between releases: re-verify each row you rely on in the version-matched developing-with-idfkit references for the project's installed idfkit.

**What "native" means.** `IDFDocument` itself mixes in eppy-shaped methods (`idfobjects`, `getobject`, `newidfobject`, `copyidfobject`, `addidfobject`, `removeallidfobjects`, `saveas`, `run`, …) from `idfkit._compat`, so old call sites can keep "working" after `IDF` is replaced, and strict mode even tolerates eppy-cased field names (`zone.X_Origin` reads `None` instead of raising). Do not call those methods, and do not write project-level wrappers that mimic them. Two are exceptions, because idfkit uses them as its own primitives: `doc.removeidfobject(obj)` (its documented removal method) and `doc.copyidfobject(obj, new_name=...)` (its copy method; idfkit's own `DesignDayManager.apply_to_model` copies design days with it). (`idfkit.compat` is something else: the cross-version linter, `idfkit check --targets …`, which is useful for the multi-version CI step.)

## Contents

1. Documents and objects
2. Versions and EnergyPlus discovery
3. Geometry (geomeppy)
4. Schedules (archetypal)
5. Simulation (archetypal `IDF.simulate`)
6. Results (archetypal `Sql`)
7. Dependencies archetypal used to bring in

## 1. Documents and objects

| Old | idfkit | Notes |
|---|---|---|
| `IDF(path, as_version=...)` | `idfkit.load_idf(path)`; `idfkit.migrate(...)` only for user-supplied files | For a base/template model, build it with `idfkit.new_document(version)` + `doc.add(...)` instead of loading and migrating a packaged file (see pitfalls: first-build cost). `new_document` pre-adds Version, Building, SimulationControl and GlobalGeometryRules: remove or replace them to match the old base model. |
| `idf.idfobjects["ZONE"]` | `doc["Zone"]` | Type names match case-insensitively; collections iterate in insertion order. |
| `idf.getobject("ZONE", name)` | `doc["Zone"].get(name)` | Case-insensitive, like eppy. |
| `idf.newidfobject("ZONE", Name=..., ...)` | `doc.add("Zone", name, {field: value})` | Validates against the schema; unknown field names raise. **Duplicate names (case-insensitive) raise `DuplicateObjectError`**, and adding a second singleton raises too, whereas archetypal returned the existing identical object and replaced a different one. Reproduce that in one helper if the code relies on it. |
| `obj.Zone_Name` | `obj.zone_name` | snake_case epJSON field names. Some names differ across EnergyPlus versions (e.g. Lights `watts_per_zone_floor_area` up to 23.2, `watts_per_floor_area` from 24.1); resolve per document schema. |
| extensible fields (`obj.Zone_1_Name`, …) | the object's extensible wrapper (e.g. `zones=[{"zone_name": ...}]`) | See the document-and-objects reference. |
| `idf.removeidfobject(obj)` | `doc.removeidfobject(obj)` | idfkit's own documented method. Removing and re-adding an object drops idfkit's reference-index edges pointing at it. |
| `idf.copyidfobject(obj)` / `idf.addidfobject(other_doc_obj)` | `doc.copyidfobject(obj, new_name=...)` | Copies across documents too (e.g. design days from a DDY document). Copying within the same document needs `new_name`. Don't rebuild a copy from `obj.to_dict()`: it includes `"name"`, which `doc.add` rejects as a field. |
| `idf.saveas(path)` / `idf.idfstr()` | `idfkit.save_idf(doc, path)` / `idfkit.write_idf(doc)` (returns a string) | Both default to `ordering="sorted"` by object type, which matters when diffing against an eppy-written file. |
| object counts, deep copies | `doc.keys()`, `doc.all_objects` (a property), `doc.copy()` (deep copy) | |

## 2. Versions and EnergyPlus discovery

| Old | idfkit | Notes |
|---|---|---|
| `archetypal.EnergyPlusVersion(...)`, `.latest()` | version tuples; `idfkit.version_string(t)`; `idfkit.find_closest_version`; `idfkit.simulation.find_energyplus(version=...)` | `version=` is keyword-only and matches an **exact** (major, minor, patch); a two-part string gets patch 0, so `"24.1"` won't find a 24.1.1 install. Which version to default to (newest installed? newest supported?) is a contract decision for the brainstorm. Raise a clear error for unsupported majors instead of a `KeyError` in some per-major table. |

## 3. Geometry (geomeppy)

| Old | idfkit | Behavioural differences |
|---|---|---|
| `idf.add_block(name, coordinates, height, num_stories, zoning, perim_depth, below_ground_stories, …)` | `idfkit.zoning.create_block(doc, name, footprint, floor_to_floor, num_stories, *, zoning=ZoningScheme.BY_STOREY / CORE_PERIMETER, perimeter_depth=…, base_elevation=…)` | **geomeppy `height` is the total block height; idfkit `floor_to_floor` is per storey**: `floor_to_floor = height / num_stories`. Copying the argument across makes storeys N times too tall. idfkit's `perimeter_depth` defaults to 4.57 m (ASHRAE); pass the old value explicitly. No below-ground storeys and no negative `base_elevation`: build the storey at 0 and move its surfaces down. **Zone names differ**: geomeppy storeys are 0-based (`Block X Storey 0`), idfkit's 1-based (`X Story 1 Core`), and idfkit drops "Story N" for a one-storey block. Rename with `doc.rename("Zone", old, new)` to the old scheme and order if names reach stored results. |
| `idf.intersect_match()` | `idfkit.surface_matching.intersect_and_match(doc, MatchOptions(...))` (or the thin wrapper `idfkit.intersect_match(doc)`) | Default `snap_tol` is 0.1 mm, which moved diagonal walls off exact corners; `snap_tol=1e-9` gave exact parity. `max_thickness=0.5` m can pair planes geomeppy would not. Acts on the whole document. |
| `idf.set_wwr(wwr, construction, force=True, surfaces=[...])` | `idfkit.set_wwr(doc, wwr, *, construction=…, surface_type="Wall", orientation=…, tolerance=…)` | **No surface list**: it filters only by surface type and orientation, and only touches `Outdoors` walls. Write a small window helper, or remove windows on excluded walls (attics, basements) afterwards. `wwr` must be strictly between 0 and 1: `0.0` raises (geomeppy-era code often used 0 to strip windows). Windows are named `{wall}_Window`. Check window glass area per zone against the baseline. |
| `idf.add_shading_block(...)` | `idfkit.add_shading_block(doc, name, footprint, height, base_z)` | Both write `Shading:Site:Detailed`; idfkit also adds a top cap named `<name> Top` that geomeppy did not. Remove it for parity. |
| `idf.set_default_constructions()` | `idfkit.set_default_constructions(doc, "Default Construction")` | geomeppy **created** `Project Wall/Partition/Floor/Flat Roof/Ceiling/Door` + `Project External Window` (with `DefaultMaterial` / `DefaultGlazing`) and chose one per surface type. idfkit fills only surfaces whose construction is empty, with one name for every type, and creates nothing: anything not reassigned later points at an undefined construction. |
| `idf.rotate(angle)`, `translate`, `scale(..., axes=)` | `rotate_building(doc, angle_deg, anchor)`, `translate_building(doc, offset)`, `scale_building(doc, (fx, fy, fz), anchor)` | Both rotate counter-clockwise. idfkit's anchor defaults to the origin; geomeppy anchored on the floors' bounding-box centre, so pass it explicitly. |
| `idf.bounding_box()` | `idfkit.bounding_box(doc)` | idfkit uses `BuildingSurface:Detailed` only and returns `((minx, miny), (maxx, maxy))` or `None`; geomeppy used floors and returned a polygon. |
| `geomeppy.Polygon3D`, `Vector2D` | `idfkit.Polygon3D`, `idfkit.Vector3D`, `calculate_surface_area`, … | |

## 4. Schedules (archetypal)

| Old | idfkit | Notes |
|---|---|---|
| `Schedule.from_values(...).to_year_week_day()` / `add_year_to_idf` | parity: a project-owned writer of the same Year/Week/Day objects; later: `idfkit.create_compact_schedule_from_values(doc, name, values, year, type_limits)` | archetypal fills weeks positionally (**January 1 always lands in the Monday slot**), uses 52 weeks with the last block stretched to Dec 31 and drops day 365, and **writes the ScheduleTypeLimits object itself**. Reproduce all of that for parity. `create_compact_schedule_from_values` keys days by calendar date (`For: AllDays`), which fixes the weekday shift but changes results: do it as a separate, signed-off change, and pass a non-leap `year` (the default 2024 expects 8784 values). |
| `Schedule.constant_schedule(...)` | `idfkit.create_constant_schedule` (or the parity writer if names/types must match) | |
| `ScheduleTypeLimits(...)` | `idfkit.create_schedule_type_limits(doc, name, lower, upper, numeric_type, unit_type)` | |
| `Schedule.Values`, `.bounds` | `idfkit.schedules.values(obj, year=<non-leap>, document=doc)` or the component's own value list | |

## 5. Simulation (archetypal `IDF.simulate`)

| Old | idfkit | Notes |
|---|---|---|
| `IDF(..., epw=..., prep_outputs=..., output_directory=...)` + `idf.simulate()` | `idfkit.simulation.simulate(doc, weather, *, output_dir=..., energyplus=find_energyplus(version=...))` → `SimulationResult` | It returns `success=False` instead of raising: check it, and raise with the `.err` text (`result.err_path`, `result.errors`). It runs a copy of `doc` with `Output:SQLite` (SimpleAndTabular) injected if missing, so the IDF in the run directory can differ from `doc`. `result.sql`, `result.sql_path`. |
| `prep_outputs=True/list` | explicit `doc.add` of output objects | archetypal silently added Output:SQLite, summary reports, table style, variable dictionary, and extra meters/variables. Reproduce the exact `Output:*` set from a captured old-stack IDF and test it (say whether you compare `doc` or the IDF that ran). |
| `idf.sql_file`, `idf.simulation_files` | `result.sql_path`, `result.err_path`, run directory | |

## 6. Results (archetypal `Sql`)

| Old | idfkit | Notes |
|---|---|---|
| `Sql(path)` | `SQLResult(path)` or `result.sql` | **Opens the SQLite connection and keeps it open** until `close()`, context-manager exit or garbage collection (`result.sql` opens lazily; `SimulationResult.close()` / `with simulate(...) as result:` closes it). Close it, or copy the file out, before a `TemporaryDirectory` is removed, or cleanup fails on Windows. |
| `sql.timeseries_by_name(names, "Hourly")` | a project-owned frame builder over `sql.query(...)` | `SQLResult.get_timeseries` returns the first matching key only and raises `KeyError` on an unknown variable; archetypal returned all keys, and an empty frame for unknown names. archetypal's frame: column levels `IndexGroup / KeyValue / Name`, `DatetimeIndex` in year 2018 minus `Interval` minutes, warmup excluded, environment type 3. Values are raw EnergyPlus units in both; archetypal also attached a `.units` mapping. |
| `sql.tabular_data_by_name(report, table)` | `SQLResult.get_tabular_data(report_name, table_name, …)`, pivoted to `RowName × (ColumnName, Units)` | |

## 7. Dependencies archetypal used to bring in

Removing archetypal can remove packages the codebase imports directly without declaring them (seen: `networkx`, `tqdm`, `pyyaml`; check `matplotlib` for notebooks). Grep the code's imports against the declared dependencies before re-locking.
