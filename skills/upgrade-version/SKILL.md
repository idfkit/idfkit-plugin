---
name: upgrade-version
description: "Forward-migrate an EnergyPlus model to a newer version using the official IDFVersionUpdater transition toolchain (migrate_model). Forward-only."
disable-model-invocation: true
argument-hint: "[model-path] [target-version]"
---

# Upgrade EnergyPlus Model Version

Upgrade: $ARGUMENTS

> Migration runs the official EnergyPlus **Transition** programs via `migrate_model`.
> It is **forward-only** (target must be >= current) and **requires EnergyPlus installed**
> — the transition binaries ship with it. Do **not** migrate by hand-copying objects into a
> `new_model`: field reorders/renames, split or merged object types, and changed defaults make a
> manual copy silently incorrect (it can still pass schema validation while being physically wrong).

## Steps

1. **Load** — Use `load_model` with the source file. Read the `idfkit://model/summary` resource and
   note the current version.

2. **Resolve target** — If `target_version` is not given, default to the latest supported version
   (currently 26.1.0) and confirm with the user. `migrate_model` defaults to the installed
   EnergyPlus version when `target_version` is omitted.

3. **Preflight the direction** — Migration is forward-only:
   - `target == current`: nothing to do — report and stop.
   - `target < current`: **stop**. EnergyPlus Transition has no downgrade path; tell the user and exit.
   - `target > current`: proceed.

4. **Migrate** — Use `migrate_model(target_version=<target>)`. This drives the full IDFVersionUpdater
   transition chain (one binary per version step) and replaces the in-memory model on success.
   - If it fails because EnergyPlus can't be found, instruct the user to install EnergyPlus or set
     `$ENERGYPLUS_DIR` (or pass `energyplus_dir=`). Do **not** fall back to a manual object copy.

5. **Read the migration report** — Read the `idfkit://migration/report` resource for the per-step
   stdout/stderr, the transition audit, and the structural diff (object types added/removed, per-type
   field changes). Surface any transition warnings to the user.

6. **Validate** — Run `validate_model` then `check_model_integrity`. These confirm the migrated model
   is well-formed (schema + domain QA). Note that passing them does **not** guarantee a successful
   simulation — if EnergyPlus is available, a `run_simulation` smoke test is the definitive check.

7. **Save** — `migrate_model` leaves `state.file_path` pointing at the original source, so a bare
   `save_model` would overwrite it. Save to a new versioned path to preserve the source, e.g.
   `save_model(file_path="<name>_v<target>.idf")`.

8. **Report** — Summarize from authoritative sources, not guesswork:
   - source and target versions, and the transition chain that ran (from the report),
   - structural diff highlights from `idfkit://migration/report`,
   - `validate_model` / `check_model_integrity` results,
   - the saved path,
   - any transition-emitted warnings that need manual review.

**Supported range**: 8.9.0 through the latest supported version (currently 26.1.0). EnergyPlus
switched from SemVer to CalVer at 9.6.0 → 22.1.0, so there is no 10.x; the achievable range is
ultimately bounded by the transition binaries shipped with the installed EnergyPlus.
