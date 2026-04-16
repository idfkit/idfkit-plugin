---
name: upgrade-version
description: "Upgrade an EnergyPlus model from one version to another, handling object type changes and deprecated fields"
disable-model-invocation: true
argument-hint: "[model-path] [target-version]"
---

# Upgrade EnergyPlus Model Version

Upgrade: $ARGUMENTS

## Steps

1. **Load current model** — Use `load_model` with the source file. Read the `idfkit://model/summary` resource to note the current version.

2. **Identify target version** — If not specified, default to the latest supported version (25.2.0). Confirm with the user.

3. **Research changes** — Use `search_docs` and `get_doc_section` to understand what changed between versions. Key areas:
   - Renamed or removed object types
   - New required fields
   - Changed field names or semantics
   - Deprecated features

4. **Create target model** — Use `new_model` with the target version.

5. **Migrate objects** — For each object type in the source model:
   - Use `list_objects` to get all objects of that type
   - Use `describe_object_type` on the target version to verify field compatibility
   - Use `batch_add_objects` to add compatible objects
   - Flag objects that need manual attention (changed schemas, removed types)

6. **Validate** — Run `validate_model` on the new model and fix any version-specific issues.

7. **Save** — Use `save_model` to write the upgraded model.

8. **Report** — Summarize:
   - Objects migrated successfully
   - Objects that needed modification
   - Any objects that could not be migrated (removed types)
   - Recommendations for manual review

**Supported versions**: 8.9.0, 9.0.1, 9.1.0, 9.2.0, 9.3.0, 9.4.0, 9.5.0, 9.6.0, 22.1.0, 22.2.0, 23.1.0, 23.2.0, 24.1.0, 24.2.0, 25.1.0, 25.2.0
