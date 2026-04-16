---
name: quick-sim
description: One-shot workflow — load a model, validate, simulate, and report results
disable-model-invocation: true
argument-hint: "<model-path>"
---

# Quick Simulation

Run a complete simulation workflow for: $ARGUMENTS

1. Load the model with `load_model`
2. Read the `idfkit://model/summary` resource for a brief overview
3. Validate with `validate_model` and `check_model_integrity` — report any issues but continue if non-critical
4. Check for weather data — if no weather file is configured, search for one based on the model's Site:Location
5. Run `run_simulation` with annual=true
6. Read the `idfkit://simulation/results` resource and present:
   - Total energy consumption and intensity (kWh/m2)
   - Energy breakdown by end-use
   - Peak loads
   - Unmet hours
   - Any simulation errors or warnings
7. Use `view_simulation_report` to open the interactive report viewer for deeper exploration
8. Ask user if they want to fix any issues and re-run, or if they want to explore specific results in more detail
