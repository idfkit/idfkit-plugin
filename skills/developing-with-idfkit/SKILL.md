---
name: developing-with-idfkit
description: "Use for ALL coding tasks that use the idfkit library, in Python (`import idfkit`) or JavaScript/TypeScript (`@idfkit/idfkit`, `@idfkit/core`, `@idfkit/schemas`, `@idfkit/weather`): creating, parsing, querying, or editing EnergyPlus models in code; validating against the schema; tracking cross-references; building geometry and zoning; standing up HVAC (templates or hand-authored loops); evaluating schedules; computing thermal properties; downloading weather data; running EnergyPlus; and parsing simulation results. Discovers and loads version-matched reference docs from the idfkit installed in the user's project. Triggers: idfkit, import idfkit, @idfkit/, IdfDocument, IDFObject, IdfObject, parseIdf, writeIdf, writeEpJson, epJSON, .idf file, HVACTemplate, AirLoopHVAC, PlantLoop, idfkit.simulation, idfkit.weather, idfkit.schedules, idfkit.thermal, idfkit.visualization, LATEST_VERSION, building energy model in Python, TypeScript, or JavaScript."
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/scripts/discover.py:*) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/discover.py:*)
---

# Developing with idfkit

idfkit has two implementations, and this skill covers both:

| Language | Install | Reference docs |
|---|---|---|
| **Python** | `idfkit` on PyPI | Bundled in the pip package (>=0.13) |
| **JavaScript / TypeScript** | `@idfkit/idfkit` on npm (`@idfkit/core` and friends) | Bundled in the npm package once a release ships them; until then the installed README and `.d.ts` declarations, plus [js.idfkit.com](https://js.idfkit.com) |

They are siblings, not ports: the JS line is a re-design (epJSON field names
verbatim, synchronous core, generated static types) and does not cover the full
Python surface. It has no simulation runner (that is
[`@idfkit/engine`](https://www.npmjs.com/package/@idfkit/engine), which takes the
IDF text `writeIdf` produces), no schedules or thermal properties, and only part
of the weather module. Do not carry a Python API into JS code or the reverse;
load the reference for the language being written.

The Python package ships detailed, task-oriented reference documentation **inside
its own pip package**: a routing `SKILL.md` plus a `references/` folder of focused
topic docs (parsing, reference tracking, geometry, HVAC, schedules, results,
weather, and more), with code examples that are linted and type-checked so they
run as-is. The npm packages are looked up at the same sub-path,
`.agents/skills/developing-with-idfkit/SKILL.md`.

This skill discovers the idfkit installed in the **user's project** and loads the
reference set that matches that exact version — so the guidance never drifts from
the API the code will run against.

## When to use this skill

Use it when the task is **writing or debugging code that uses idfkit**: Python
that imports `idfkit` (`idfkit.simulation`, `idfkit.weather`, …), or JavaScript /
TypeScript that imports `@idfkit/*`.

This is distinct from interacting with an IDF model through the **idfkit MCP
server** (the `load_model`, `validate_model`, `run_simulation`, … tools and the
`idfkit://…` resources). For that tool-driven workflow, use the MCP server and the
workflow skills (`simulate`, `validate`, `new-model`, …) instead. The references
here are about the library API, not the MCP tool surface.

## Usage

Run the discovery script with the user's project directory and the language of
the code being written:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/discover.py --project-dir <USER_PROJECT_DIR> --language <python|js>
```

Use the literal `${CLAUDE_SKILL_DIR}` token so the command matches the `allowed-tools` permission
pattern and runs without a prompt.

`--language` defaults to `auto`, which picks `js` when the project directory has a
`package.json` naming an `@idfkit/` package (or an installed one in reach) and no
Python manifest, and `python` otherwise. Pass it explicitly whenever you know the
language, and always in a project that has both.

The script prints either:

- **A path on stdout** (exit 0) — the bundled `SKILL.md`. Read it; it routes into
  `references/<topic>.md`. Fetch the smallest reference that covers the task rather
  than pre-loading everything.
- **An `ERROR:` block on stderr** (non-zero exit). Follow the printed instructions
  (install or upgrade idfkit, activate the right environment) and re-run.

For JS, an installed release that ships no bundled skill exits 2 and lists the
version-matched files to read instead: the package READMEs and the `.d.ts`
declarations, whose TSDoc documents every export. Read those, and use
https://js.idfkit.com for task-oriented guides. Prefer the installed files over
the website when they disagree; they match the version the code will run against.

`${CLAUDE_SKILL_DIR}` resolves to the directory containing this file; `<USER_PROJECT_DIR>` is the
absolute path to the user's project. Passing `--project-dir` matters because the
script resolves everything relative to it — so it inspects the user's project, not
this skill's install location:

- **Python:** `.venv`, `../.venv`, `<git-root>/.venv`, `Pipfile`, `poetry.lock`,
  `pdm.lock`, and `uv.lock`.
- **JS:** `node_modules/@idfkit/idfkit` then `node_modules/@idfkit/core`, from the
  project directory upward as Node resolves them (pnpm layouts included), and the
  lockfile that decides the install command (`pnpm`, `yarn`, `bun`, or `npm`).
