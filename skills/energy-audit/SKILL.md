---
name: energy-audit
description: "Compare two EnergyPlus model variants to quantify energy savings from proposed changes (e.g., envelope upgrades, HVAC replacements, lighting retrofits)"
disable-model-invocation: true
context: fork
argument-hint: "[baseline-model] [proposed-model]"
---

# Energy Audit — Baseline vs. Proposed Comparison

Compare models: $ARGUMENTS

## Steps

1. **Load baseline** — Use `load_model` to open the baseline (existing conditions) model. Read the `idfkit://model/summary` resource to document its configuration.

2. **Document baseline** — Record key properties:
   - Envelope: wall/roof/window U-values and SHGC (inspect Construction and Material objects)
   - HVAC: system types and efficiencies
   - Lighting: power densities per zone
   - Schedules: occupancy and operating hours
   - Weather file and location

3. **Simulate baseline** — Run `run_simulation` and read the `idfkit://simulation/results` resource. Use `analyze_peak_loads` for peak decomposition. Record:
   - Annual energy by end-use (heating, cooling, lighting, equipment, fans, pumps)
   - Peak heating and cooling loads with component breakdown
   - Unmet hours

4. **Load proposed** — Clear session with `clear_session`, then `load_model` the proposed model. Read the `idfkit://model/summary` resource.

5. **Document changes** — Compare key differences from baseline:
   - What was changed (insulation, windows, HVAC equipment, controls, etc.)
   - Quantify the parameter changes

6. **Simulate proposed** — Run `run_simulation` and read the `idfkit://simulation/results` resource. Use `analyze_peak_loads`.

7. **Compare and report**:
   - **Energy savings**: kWh and % reduction by end-use category
   - **Peak load reduction**: kW reduction in heating/cooling peaks
   - **Unmet hours**: Ensure comfort is maintained
   - **Cost implications**: If utility rates are known, estimate annual savings
   - **Simple payback**: If measure costs are provided

Present results in a clear comparison table format.
