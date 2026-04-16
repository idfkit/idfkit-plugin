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

3. **Categorize issues** by severity and type:
   - **Critical errors**: Missing required fields, invalid field types, unknown object types
   - **Reference errors**: Dangling references, circular dependencies
   - **Warnings**: Values outside recommended ranges, deprecated fields
   - **Info**: Suggestions for improvement

4. **Suggest fixes** for each issue:
   - Missing references → suggest creating the missing object or updating the reference (use `get_available_references` to find valid values)
   - Invalid values → show the valid range or enum values (use `describe_object_type`)
   - Missing required fields → show what fields are needed with defaults

5. **Offer to auto-fix** simple issues:
   - Update fields with valid defaults using `update_object`
   - Create missing referenced objects using `add_object`
   - Remove orphaned references

6. **Re-validate** after fixes to confirm resolution
