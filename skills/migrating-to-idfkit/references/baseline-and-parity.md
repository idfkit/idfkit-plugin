# Baseline and parity

The regression baseline is the proof of the whole migration. Capture it first, with the old stack, before any production code changes.

## What to capture (per configuration)

Pick about three configurations that exercise the paths consumers use (for example: a plain multi-storey model; core/perimeter zoning with a conditioned basement and an attic; neighbour shading with the overheating analysis on). Build them from the same fixtures the tests use.

- The consumer-facing results: e.g. `energy_and_peak`, every overheating frame, the hourly frame (all variables consumers may request, not a subset).
- **Per-zone geometry from EnergyPlus itself**: the `InputVerificationandResultsSummary` → `Zone Summary` table read with the standard library `sqlite3` (area, volume, gross wall area above plus below ground, window glass area). Library-independent, and catches geometry drift before any energy number moves.
- **The IDF EnergyPlus actually ran** (from the run directory), for diffing object by object when a value drifts, and for reproducing `Output:*` objects.
- **Zone names in file order** for a grid of geometry variants (zoning × basement × attic × storeys × shading), parsed by regex from IDF text, plus shading object counts. No simulation needed.
- **Name-independent per-surface records** (zone, surface type, boundary condition, boundary zone, construction, rounded area and centroid) for the same grid, while the old geometry library is still installed. This survives the dependency removal and pins geometry parity beyond counts.

Write the fixtures with a committed capture script, and verify every parquet round-trips exactly at capture time (empty frames and `None` keys don't). After the old stack is removed, keep the script with a header explaining how to run it ad hoc (`uv run --with archetypal==<version> python scripts/...`, or loading old module versions from a git commit).

## Before trusting it: sanity-check the physics

Read, per configuration: annual heating and cooling (kWh/m² of conditioned area), the largest zone design cooling capacity (`ComponentSizes`), the zone air temperature range, and the EnergyPlus warning count. Expect heating clearly above zero, cooling in tens of kWh/m² (not thousands), capacities in kW (not MW), and no huge-flow sizing warnings. If the numbers are absurd, the fixtures are wrong (placeholder setpoints are the classic case): fix the seed, recapture from the old stack, and recheck.

## Determinism

Run the capture with a fixed `PYTHONHASHSEED` and confirm order-sensitive objects (sizing periods) appear in the order the new code will use. Record the seed in the capture script header.

## The parity test

- Labels, shapes and index/column structure: exact.
- Per-zone geometry: `rtol=1e-9`, `atol=0.01` (EnergyPlus prints two decimals).
- Energy, peak, overheating and hourly values: `rtol=1e-3`, `atol=1e-6`.
- Skip on every EnergyPlus version other than the capture version; add a smoke test that runs on every CI version and checks result labels only.
- Output objects: compare each `Output:*` type in both directions in a canonical, orderable form, ignoring blanks and schema defaults.
- When a value misses: stop; diff the new model against the captured IDF one object type at a time (swap objects in until the numbers match) to find the cause; write it up; get the user's sign-off before changing anything.

## Byte-identical IDF snapshots (refactors that must not change the model)

For changes after parity that should not alter the written model at all (retiring mirror classes, renames, moving writers between modules), the simulation tolerance is too loose a gate. Before touching code, write a script that builds every model the tests build, plus variants that reach the writers the plain configurations skip (systems off, natural ventilation, economizers, heat recovery, conditioned basements and attics), without simulating, and writes each with `idfkit.write_idf(doc)` (sorted order) for the oldest and newest supported EnergyPlus versions. Run it twice to confirm it is deterministic. After every step, rebuild and `diff -r`: it must be empty. Fix the port on any difference, never the snapshot. To confirm the snapshots really came from the old code, regenerate them from the old commit at the end and compare again. Note the branches the variants do not reach.

## Benchmarking at the end

Same machine, same EnergyPlus, same model, both stacks in separate checkouts: import time, first build in a fresh process (repeat ×3), median of later builds, median of full runs including reading results, and the equality of the headline results. Report the numbers with their caveats (one model, one machine, warm caches).
