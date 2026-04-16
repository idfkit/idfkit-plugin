---
name: simulate
description: Run an EnergyPlus simulation on the loaded model and analyze the results
disable-model-invocation: true
argument-hint: "[model-path]"
---

# Run EnergyPlus Simulation

Simulate the model: $ARGUMENTS

## Steps

1. **Pre-check** — Read the `idfkit://model/summary` resource to confirm a model is loaded. If a file path was provided, use `load_model` first.

2. **Validate** — Run `validate_model` and `check_model_integrity`. If there are critical errors, report them and ask the user whether to proceed or fix first.

3. **Weather check** — Confirm a weather file is available:
   - Check if the model has a Site:Location or weather file assigned
   - If not, ask for the building location and use `search_weather_stations` + `download_weather_file`

4. **Run simulation** — Use `run_simulation` with appropriate parameters:
   - `weather_file`: path to EPW file
   - `design_day`: true for sizing runs
   - `annual`: true for full-year simulation
   - Report progress and any warnings during the run

5. **Analyze results** — Read the `idfkit://simulation/results` resource for the overview:
   - **Energy consumption**: Total site/source energy, by end-use category
   - **Energy intensity**: kWh/m² (or kBtu/ft²)
   - **Peak loads**: Heating and cooling design loads
   - **Unmet hours**: Hours where setpoints weren't met (target: < 300 heating + cooling)
   - **Errors**: Any severe errors or warnings from the simulation

6. **Peak load analysis** — Use `analyze_peak_loads` to decompose facility and zone peaks into components and flag QA issues.

7. **Detailed analysis** — Use `query_timeseries` and `query_simulation_table` for specific metrics:
   - Monthly energy breakdown
   - Zone temperature profiles
   - System performance metrics
   - Use `list_output_variables` to see available time series data
   - Use `list_simulation_reports` to see available tabular reports

8. **Interactive review** — Use `view_simulation_report` to browse the full tabular report interactively.

9. **Export if requested** — Use `export_timeseries` to save results to CSV

Present results in a clear, organized format with the most important metrics highlighted.
