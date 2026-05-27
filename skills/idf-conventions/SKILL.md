---
name: idf-conventions
description: EnergyPlus modeling conventions, naming patterns, and best practices with idfkit. Loaded automatically when working with IDF, epJSON, or idfkit Python code.
user-invocable: false
paths: "**/*.idf, **/*.epJSON, **/*.epjson, **/*.py"
---

# EnergyPlus Modeling Conventions (idfkit)

## idfkit MCP Tools & Resources

This skill assumes the idfkit MCP server is available. Don't rely on a memorized tool count — consult
the **live tool list** and the server's own startup instructions for the authoritative set. The tools
span schema introspection, model read/write, validation + integrity, simulation + analysis, weather,
documentation, and version migration.

Structured state is exposed as read-only `idfkit://…` resources you can read at any time, including:

- `idfkit://model/summary` — version, zones, object counts, and groups for the loaded model
- `idfkit://model/objects/{object_type}/{name}` — all field values for a specific object
- `idfkit://model/references/{name}` — bidirectional references (who references this object and what it references)
- `idfkit://schema/{object_type}` — full field schema for an object type
- `idfkit://docs/{object_type}` — I/O Reference, Engineering Reference, and search URLs
- `idfkit://simulation/results` — energy metrics, errors, and tables from the last simulation
- `idfkit://simulation/peak-loads` — peak heating/cooling load decomposition with QA flags
- `idfkit://simulation/report` — full tabular simulation report organized by section and table
- `idfkit://migration/report` — per-step transition output and structural diff after `migrate_model`

The server may expose more — treat its live instructions as authoritative rather than this list.

## Key Conventions

### Object Naming
- Use descriptive, meaningful names (e.g., "South Wall Zone 1" not "Wall1")
- Object names are case-sensitive and must be unique within their type
- Type lookups are case-insensitive (both "Zone" and "zone" work)

### Field Names
- idfkit uses snake_case Python field names: `direction_of_relative_north`, `ceiling_height`
- The MCP tools accept these snake_case names in the `fields` parameter
- Extensible groups use a structured array under a wrapper key — e.g. `BuildingSurface:Detailed` takes `vertices: [{vertex_x_coordinate, vertex_y_coordinate, vertex_z_coordinate}, …]`. (Flat numbered keys like `vertex_1_x_coordinate` are a deprecated compat shim that emits warnings — don't use them.) Check `describe_object_type`'s `extensible_group` for the exact key and item fields.

### Workflow Best Practices
1. **Always call `describe_object_type` before creating objects** — know valid fields, constraints, and defaults
2. **Use `batch_add_objects` for multiple objects** — minimizes round-trips vs individual `add_object` calls
3. **Use `get_available_references` for reference fields** — ensures valid values (e.g., zone names, schedule names)
4. **Validate after modifications** — call `validate_model` to catch schema violations and dangling references
5. **Run `check_model_integrity` before simulation** — catches domain-level issues (zones without surfaces, orphan schedules, boundary mismatches, HVAC reference errors)
6. **Check references before removing objects** — `remove_object` blocks if the object is referenced (use `force=True` only when intentional)
7. **Use `rename_object` instead of remove+add** — it automatically updates all references
8. **Read resources for object data** — use `idfkit://model/objects/{type}/{name}` to inspect objects and `idfkit://model/references/{name}` to check references

### Version Support
- Supported EnergyPlus versions: 8.9.0 through the latest supported (currently 26.1.0); idfkit exposes the newest as `LATEST_VERSION`
- Default version for new models: the latest supported version
- Schemas are bundled — no EnergyPlus installation needed for editing or schema validation; only simulation and version migration require an EnergyPlus install

### Common Object Categories
- **Simulation Parameters**: SimulationControl, Timestep, RunPeriod, Building
- **Location/Climate**: Site:Location, SizingPeriod:DesignDay
- **Schedules**: ScheduleTypeLimits, Schedule:Compact, Schedule:Year
- **Geometry**: Zone, BuildingSurface:Detailed, FenestrationSurface:Detailed
- **Materials**: Material, Material:NoMass, WindowMaterial:Glazing
- **Constructions**: Construction
- **Internal Loads**: People, Lights, ElectricEquipment
- **HVAC**: ZoneHVAC:*, AirLoopHVAC, PlantLoop, Coil:*, Fan:*
- **Output**: Output:Variable, Output:Meter, OutputControl:Table:Style

### Documentation
- Read `idfkit://docs/{object_type}` resource to get docs.idfkit.com URLs for any object type
- Use `search_docs` to find documentation by keyword
- Use `get_doc_section` to read full documentation sections
