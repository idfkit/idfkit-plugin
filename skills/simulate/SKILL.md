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

4. **Sizing readiness** — If any equipment is autosized (the common case), the model needs a sizing
   run before/with the annual run, or capacities resolve to zero. Confirm `SizingPeriod:DesignDay`
   objects exist and `SimulationControl` enables zone/system sizing. (`check_model_integrity` checks
   that `SimulationControl` is *present*, not that its sizing flags are *on*.)

5. **Run simulation** — Use `run_simulation` with appropriate parameters:
   - `weather_file`: path to the EPW file
   - `design_day`: true to run the sizing (design-day) periods
   - `annual`: true for the full-year run
   - For an autosized model, run `design_day=true, annual=true` together so sizing feeds the annual run
   - `readvars`: true if you want standard ReadVars CSV output (`eplusout.csv`)
   - Report progress and any warnings during the run

6. **Analyze results** — Read the `idfkit://simulation/results` resource for the overview:
   - **Energy consumption**: Total site/source energy, by end-use category
   - **Energy intensity**: kWh/m² (or kBtu/ft²)
   - **Peak loads**: Heating and cooling design loads
   - **Unmet hours**: Occupied hours where setpoints weren't met — reported **separately** for heating
     and cooling. ASHRAE 90.1 G3.1.2.3 targets **≤ 300 occupied unmet hours each** (not a heating +
     cooling sum); for a baseline/proposed comparison the two models should also differ by ≤ 50 hours.
   - **QA flags / errors**: resolve `qa_flags` and any severe errors or warnings from the simulation

7. **Peak load analysis** — Read the `idfkit://simulation/peak-loads` resource and use `analyze_peak_loads` to decompose facility and zone peaks into components and flag QA issues. (This requires the SensibleHeatGainSummary and HVACSizingSummary reports to be requested in the model.)

8. **Detailed analysis** — Use `query_timeseries` and `query_simulation_table` for specific metrics:
   - Monthly energy breakdown
   - Zone temperature profiles
   - System performance metrics
   - Use `list_output_variables` to see available time series data
   - Use `list_simulation_reports` to see available tabular reports

9. **Interactive review** — Use `view_simulation_report` to browse the full tabular report interactively.

10. **Export if requested** — Use `export_timeseries` to save results to CSV

Present results in a clear, organized format with the most important metrics highlighted.
