---
name: idf-conventions
description: EnergyPlus modeling conventions, naming patterns, and best practices with idfkit. Loaded automatically when working with IDF, epJSON, or idfkit Python code.
user-invocable: false
paths: "**/*.idf, **/*.epJSON, **/*.epjson, **/*.py"
---

# EnergyPlus Modeling Conventions (idfkit)

## idfkit MCP Tools & Resources

You have access to the idfkit MCP server with 40 tools and 11 resources across 10 categories:

### Tools

**Schema** (4): `list_object_types`, `describe_object_type`, `search_schema`, `get_available_references`
**Read** (5): `load_model`, `list_objects`, `search_objects`, `convert_osm_to_idf`, `get_change_log`
**Write** (9): `new_model`, `add_object`, `batch_add_objects`, `update_object`, `remove_object`, `rename_object`, `duplicate_object`, `save_model`, `clear_session`
**Validation** (2): `validate_model` (includes reference checking via `check_references` parameter), `check_model_integrity`
**Simulation** (8): `run_simulation`, `list_output_variables`, `query_timeseries`, `query_simulation_table`, `list_simulation_reports`, `view_simulation_report`, `export_timeseries`, `analyze_peak_loads`
**Weather** (2): `search_weather_stations`, `download_weather_file`
**Documentation** (2): `search_docs`, `get_doc_section`
**Zone** (1): `get_zone_properties`
**Geometry** (1): `view_geometry`
**Schedules** (1): `view_schedules`

### Resources

Read these via MCP resource URIs for structured data:

- `idfkit://model/summary` — version, zones, object counts, and groups for the loaded model
- `idfkit://model/objects/{object_type}/{name}` — all field values for a specific object
- `idfkit://model/references/{name}` — bidirectional references (who references this object and what it references)
- `idfkit://schema/{object_type}` — full field schema for an object type
- `idfkit://docs/{object_type}` — I/O Reference, Engineering Reference, and search URLs
- `idfkit://simulation/results` — energy metrics, errors, and tables from the last simulation
- `idfkit://simulation/peak-loads` — peak heating/cooling load decomposition with QA flags
- `idfkit://simulation/report` — full tabular simulation report organized by section and table

## Key Conventions

### Object Naming
- Use descriptive, meaningful names (e.g., "South Wall Zone 1" not "Wall1")
- Object names are case-sensitive and must be unique within their type
- Type lookups are case-insensitive (both "Zone" and "zone" work)

### Field Names
- idfkit uses snake_case Python field names: `direction_of_relative_north`, `ceiling_height`
- The MCP tools accept these snake_case names in the `fields` parameter
- Extensible fields use numbered patterns: `vertex_1_x_coordinate`, `vertex_2_x_coordinate`, etc.

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
- Supported EnergyPlus versions: 8.9.0 through 25.2.0 (16 versions)
- Default version for new models: latest (25.2.0)
- Schemas are bundled — no EnergyPlus installation needed for editing, only for simulation

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
