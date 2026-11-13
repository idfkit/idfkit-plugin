# Pitfalls

Each of these surfaced in a real archetypal/geomeppy → idfkit migration. Put the relevant ones into the task brief that touches the code, and name them as review risks.

## Results that change silently

- **Duplicate names.** eppy/archetypal reused an identical same-name object and replaced a different one; idfkit raises. Shared layer materials across constructions hit this immediately. Put the reuse-or-replace semantics in one helper, and make every writer (including schedule writers) go through the same rule.
- **Schedule type limits.** archetypal wrote the `ScheduleTypeLimits` object a schedule referenced; a port that only passes the name leaves schedules pointing at nothing.
- **Weekday mapping.** archetypal puts January 1 in the Monday slot of week schedules. Check the RunPeriod's start weekday: when it isn't Monday (epinterface's models start on Sunday), every weekday/weekend profile runs one day off. Tests that evaluate schedules in a year starting on Monday (2018) hide this; test in a Sunday-start year (2017). Reproduce for parity, then fix as a separate change.
- **Zone and surface names.** geomeppy and idfkit name zones differently (0-based vs 1-based storeys, and idfkit drops "Story N" for one storey); names end up as labels in stored results. Rename to the old scheme and order.
- **Block height.** geomeppy's `add_block(height=...)` is the total height; idfkit's `create_block(floor_to_floor=...)` is per storey. Pass the old perimeter depth explicitly too (idfkit defaults to 4.57 m).
- **Default constructions.** geomeppy created default constructions; idfkit only assigns a name.
- **Windows and shading.** `set_wwr` has no surface list (type and orientation only) and rejects `wwr=0`; `add_shading_block` adds a top cap (`<name> Top`) that geomeppy didn't write. Both libraries write `Shading:Site:Detailed`.
- **Output objects.** archetypal's `prep_outputs` added outputs (and an odd filter that let extra meters through). Reproduce from a captured IDF; compare per object type in both directions. idfkit's `simulate` injects `Output:SQLite` into the copy it runs if missing.
- **Eppy-shaped methods still exist.** `IDFDocument` carries eppy-compatible methods (`idfobjects`, `getobject`, `newidfobject`, …) and tolerates eppy-cased field names, so un-ported call sites keep running and read `None`. Re-run the inventory at the end and expect zero old-API hits apart from `removeidfobject`.
- **Old-library bugs.** geomeppy mis-paired surfaces for some storey heights (an outdoor wall became a partition and lost its window). Decide explicitly: reproduce, or keep the correct result and pin the difference in a test, then tell the user which inputs change.

## Nondeterminism in the old stack

- archetypal passed sizing-period names through a Python `set`, so their order followed string hashing and changed between processes (unless `PYTHONHASHSEED` was set). The order can change results. Pin the order in the new code to the baseline's, and capture the baseline with a fixed `PYTHONHASHSEED` that gives that order (check the captured IDF).

## Baselines that were never physical

- Test seeds and fixtures may be placeholders: a seed that built every schedule as a constant 0.5 `Fraction` put thermostats at 0.5 °C, so heating was zero, cooling sizing hit megawatts, and EnergyPlus warned of a maximum cooling airflow of -99998 m³/s. Parity on such a model proves little. Sanity-check the baseline (see `baseline-and-parity.md`) before trusting it; if it fails, fix the seed and recapture from the old stack.

## Environment and lifecycle

- **First build cost.** Loading a packaged base IDF and migrating it with the transition binaries cost ~37 s per fresh process (in-memory cache only). Build the base document programmatically for any version instead; it then needs no transition binaries.
- **Open SQLite handles.** `SQLResult` keeps its connection open; close it (`SimulationResult.close()`, or `with` blocks) or copy the file out before temporary directories are removed (Windows fails otherwise). If results must stay readable after a run in a temp dir, copy the `.sql` out and document it.
- **Schema differences across EnergyPlus versions.** Field names change between versions; a test hard-coding one name breaks the CI job for another version. Resolve names from the document's schema, and run no-simulation tests under each CI version.
- **Silent field filtering.** A helper that drops fields unknown to a schema hides typos on every version. Allow only explicit, version-gated absences; everything else should reach `doc.add` and fail loudly.
- **Large schedules.** Generated object names past 99 (`d_X_100`) broke a `\d\d` regex. Use `\d{2,}`.

## Process traps

- "Pre-existing" lint failures must be checked against the main branch, not against an earlier commit of the migration branch. New fixtures and formatter-version churn are the usual offenders; exclude fixture directories from file-rewriting hooks.
- A newer local `ruff` than the pre-commit pin reformats files differently; format through `pre-commit`, not the venv's ruff.
- An implementer may spawn its own reviewers or report the same result repeatedly: stop finished agents.
- Pin idfkit to the minor series the parity gate ran on.
