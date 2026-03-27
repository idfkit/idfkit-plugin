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

3. **Create model** — Use `new_model` (defaults to latest EnergyPlus version). This seeds Version, Building, SimulationControl, and GlobalGeometryRules automatically.

4. **Build the model** using `batch_add_objects` for efficiency. Add in this order:
   - **Schedules**: ScheduleTypeLimits and Schedule:Compact for occupancy, lighting, equipment, HVAC
   - **Materials and Constructions**: Wall/roof/floor materials and Construction objects
   - **Zones**: Thermal zones matching the building layout
   - **Surfaces**: BuildingSurface:Detailed for walls, floors, roofs with proper vertices
   - **Fenestration**: FenestrationSurface:Detailed for windows/doors
   - **Internal loads**: People, Lights, ElectricEquipment per zone
   - **HVAC**: Zone equipment, air loops, plant loops as needed
   - **Output**: Output:Variable and Output:Meter for key metrics
   - **Sizing and RunPeriod**: SizingPeriod:DesignDay (from DDY), RunPeriod for annual

5. **Validate** — Run `validate_model` and fix any errors

6. **Save** — Use `save_model` to write the IDF/epJSON file

Always call `describe_object_type` before adding unfamiliar object types to know the required fields and valid values.
