---
name: load-model
description: Load an IDF or epJSON file and provide a structured summary of the building energy model. Use when opening, inspecting, or starting work on an existing EnergyPlus model.
argument-hint: "[file-path]"
---

# Load and Summarize an EnergyPlus Model

Load the model at: $ARGUMENTS

## Steps

1. **Load** — Use `load_model` with the file path. If no path is provided, ask the user which file to open.

2. **Summarize** — Use `get_model_summary` to get the overview, then present:
   - **Version**: EnergyPlus version
   - **Building**: Name, north axis, terrain
   - **Zones**: Count and names
   - **Geometry**: Surface counts by type (walls, roofs, floors, windows)
   - **Constructions**: Materials and construction layers
   - **HVAC**: System types present (air loops, plant loops, zone equipment)
   - **Schedules**: Key schedule types
   - **Output**: What outputs are configured
   - **Weather**: Assigned weather file (if any)
   - **Simulation period**: RunPeriod and sizing periods

3. **Highlight issues** — If anything looks incomplete or unusual (e.g., no HVAC, no weather file, missing output variables), mention it proactively.

4. **Suggest next steps** — Based on the model state, suggest what the user might want to do next (validate, simulate, add systems, etc.).
