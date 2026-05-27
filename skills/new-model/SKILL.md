---
name: new-model
description: Create a new EnergyPlus building energy model from scratch using idfkit
disable-model-invocation: true
argument-hint: "[building-description]"
---

# Create a New EnergyPlus Model

Create a new building energy model based on: $ARGUMENTS

## Steps

1. **Gather requirements** — Ask about (if not provided):
   - Building type (office, residential, retail, school, etc.)
   - Location (city/country for weather data)
   - Approximate floor area and number of stories
   - Key systems (HVAC type, lighting, etc.)

2. **Weather data** — Use `search_weather_stations` to find the closest weather station, then `download_weather_file` to get EPW + DDY files

3. **Create model** — Use `new_model` (defaults to the latest EnergyPlus version). This seeds **only**
   Version, Building, SimulationControl, and GlobalGeometryRules. You must still add Timestep,
   RunPeriod, and Site:Location yourself (see below) — `check_model_integrity` requires Timestep and
   RunPeriod, and Site:Location is needed for solar geometry but is *not* caught by either QA gate.

4. **Build the model** using `batch_add_objects` for efficiency. Add in this order:
   - **Site & controls**: Site:Location (site lat/long/elevation/time zone), Timestep, RunPeriod
   - **Schedules**: ScheduleTypeLimits and Schedule:Compact for occupancy, lighting, equipment, HVAC (every schedule needs a referenced ScheduleTypeLimits)
   - **Materials and Constructions**: Wall/roof/floor materials and Construction objects
   - **Zones**: Thermal zones matching the building layout
   - **Surfaces**: BuildingSurface:Detailed for walls, floors, roofs with proper vertices (use the structured `vertices` array)
   - **Fenestration**: FenestrationSurface:Detailed for windows/doors
   - **Internal loads**: People, Lights, ElectricEquipment per zone
   - **Infiltration**: ZoneInfiltration:DesignFlowRate per zone (a zero-infiltration model is not credible)
   - **HVAC**: Zone equipment, air loops, plant loops as needed — plus ZoneControl:Thermostat + ThermostatSetpoint:DualSetpoint (without thermostats, zones are uncontrolled and unmet-hours are meaningless), and Sizing:Zone / Sizing:System whenever equipment is autosized
   - **Sizing periods**: SizingPeriod:DesignDay. There is **no DDY auto-import** — read the downloaded `.ddy` file and hand-author the design-day objects (or copy their values), then ensure SimulationControl enables zone/system sizing
   - **Output**: Output:Variable and Output:Meter for key metrics

5. **Validate** — Run `validate_model`, then `check_model_integrity`, and fix any errors. Schema +
   integrity passing does **not** guarantee a successful run; for full confidence continue the QA loop:
   `save_model` → `run_simulation` → read `idfkit://simulation/results` → fix → repeat until `qa_flags`
   is empty.

6. **Save** — Use `save_model` to write the IDF/epJSON file

Always call `describe_object_type` before adding unfamiliar object types to know the required fields and valid values.
