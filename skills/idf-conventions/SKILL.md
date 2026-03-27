---
name: idf-conventions
description: EnergyPlus modeling conventions, naming patterns, and best practices with idfkit. Loaded automatically when working with IDF, epJSON, or idfkit Python code.
user-invocable: false
paths: "**/*.idf, **/*.epJSON, **/*.epjson, **/*.py"
---

# EnergyPlus Modeling Conventions (idfkit)

## idfkit MCP Tools

You have access to the idfkit MCP server with 32 tools across 7 categories:

**Schema**: `list_object_types`, `describe_object_type`, `search_schema`, `get_available_references`
**Read**: `load_model`, `list_objects`, `search_objects`, `get_object`, `get_references`, `get_model_summary`, `convert_osm_to_idf`
**Write**: `new_model`, `add_object`, `batch_add_objects`, `update_object`, `remove_object`, `rename_object`, `duplicate_object`, `save_model`, `clear_session`
**Validation**: `validate_model`, `check_references`
**Simulation**: `run_simulation`, `list_output_variables`, `query_timeseries`, `export_timeseries`, `get_results_summary`
**Weather**: `search_weather_stations`, `download_weather_file`
**Documentation**: `lookup_documentation`, `search_docs`, `get_doc_section`

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
5. **Check references before removing objects** — `remove_object` blocks if the object is referenced (use `force=True` only when intentional)
6. **Use `rename_object` instead of remove+add** — it automatically updates all references

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
- Use `lookup_documentation` to get docs.idfkit.com URLs for any object type
- Use `search_docs` to find documentation by keyword
- Use `get_doc_section` to read full documentation sections
