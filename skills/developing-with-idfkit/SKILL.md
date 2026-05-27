---
name: developing-with-idfkit
description: "Use for ALL Python coding tasks that import the idfkit library: creating, parsing, querying, or editing EnergyPlus models in code; validating against the schema; tracking cross-references; building geometry and zoning; standing up HVAC (templates or hand-authored loops); evaluating schedules; computing thermal properties; downloading weather data; running EnergyPlus; and parsing simulation results. Discovers and loads version-matched reference docs from the user's installed idfkit (>=0.13). Triggers: idfkit, import idfkit, IDFObject, epJSON, .idf file, HVACTemplate, AirLoopHVAC, PlantLoop, idfkit.simulation, idfkit.weather, idfkit.schedules, idfkit.thermal, idfkit.visualization, LATEST_VERSION, building energy model in Python."
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/scripts/discover.py:*) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/discover.py:*)
---

# Developing with idfkit

idfkit (>=0.13) ships detailed, task-oriented reference documentation for writing
Python code against the library **inside its own pip package**. The bundled skill
is a routing `SKILL.md` plus a `references/` folder of focused topic docs (parsing,
reference tracking, geometry, HVAC, schedules, results, weather, and more), with
code examples that are linted and type-checked so they run as-is.

This skill discovers the idfkit installed in the **user's project** and loads the
reference set that matches that exact version — so the guidance never drifts from
the API the code will run against.

## When to use this skill

Use it when the task is **writing or debugging Python code that imports idfkit**
(`import idfkit`, `idfkit.simulation`, `idfkit.weather`, …).

This is distinct from interacting with an IDF model through the **idfkit MCP
server** (the `load_model`, `validate_model`, `run_simulation`, … tools and the
`idfkit://…` resources). For that tool-driven workflow, use the MCP server and the
workflow skills (`simulate`, `validate`, `new-model`, …) instead. The references
here are about the library API, not the MCP tool surface.

## Usage

Run the discovery script with the user's project directory:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/discover.py --project-dir <USER_PROJECT_DIR>
```

Use the literal `${CLAUDE_SKILL_DIR}` token so the command matches the `allowed-tools` permission
pattern and runs without a prompt.

The script prints either:

- **A path on stdout** (exit 0) — the bundled `SKILL.md`. Read it; it routes into
  `references/<topic>.md`. Fetch the smallest reference that covers the task rather
  than pre-loading everything.
- **An `ERROR:` block on stderr** (non-zero exit). Follow the printed instructions
  (install or upgrade idfkit, activate the right environment) and re-run.

`${CLAUDE_SKILL_DIR}` resolves to the directory containing this file; `<USER_PROJECT_DIR>` is the
absolute path to the user's project. Passing `--project-dir` matters because the
script resolves `.venv`, `../.venv`, `<git-root>/.venv`, `Pipfile`, `poetry.lock`,
`pdm.lock`, and `uv.lock` relative to it — so it inspects the user's project
environment, not this skill's install location.
