---
name: validate
description: Validate an EnergyPlus model against its schema and suggest fixes for any errors. Use after making changes to a model or before running a simulation.
argument-hint: "[object-types-filter]"
---

# Validate an EnergyPlus Model

Validate the currently loaded model. Optional filter: $ARGUMENTS

## Steps

1. **Run validation** — Use `validate_model` (optionally with `object_types` filter if the user specified specific types). Reference integrity is checked by default (`check_references=True`).

2. **Check model integrity** — Use `check_model_integrity` for domain-level QA: zones without surfaces, missing required controls, orphan schedules, boundary condition mismatches, fenestration host errors, and HVAC zone reference issues.

3. **Categorize issues** using the real `ValidationResult` shape. It reports three severities —
   **ERROR**, **WARNING**, **INFO** — and `error_count` / `warning_count` / `info_count`. Each item
   carries a `severity`, `object_type`, `object_name`, `field`, `message`, and a stable `code`:
   - `E001` — required field missing
   - `E002` — invalid type
   - `E003` — value out of range
   - `E004` — unknown reference target (a dangling reference; reported as an ERROR, not a separate tier)
   - `E010` — singleton constraint violated (more than one instance of a single-instance type)
   - `W001` — schema unavailable (validator skipped)

   `check_model_integrity` items are tagged by `severity` (error/warning/info) and `category`
   (geometry / controls / references / hvac / schedules).

4. **Suggest fixes** for each issue:
   - Missing references → suggest creating the missing object or updating the reference (use `get_available_references` to find valid values)
   - Invalid values → show the valid range or enum values (use `describe_object_type`)
   - Missing required fields → show what fields are needed with defaults

5. **Offer to auto-fix** simple issues:
   - Update fields with valid defaults using `update_object`
   - Create missing referenced objects using `add_object`
   - To fix a renamed reference, prefer `rename_object` (it updates all referrers) over remove+re-add

6. **Re-validate** after fixes to confirm resolution

7. **Note the limits** — Schema + integrity passing does **not** mean the model is simulation-ready.
   For full confidence, `save_model` → `run_simulation` → read the `idfkit://simulation/results`
   resource and resolve its `qa_flags`.
