---
name: migrating-to-idfkit
description: "Port a Python codebase from archetypal, eppy or geomeppy to idfkit's native API (not its eppy-compatible methods) without silently changing simulation results. Runs a staged, test-gated migration: inventory every call, map the public interface and its downstream consumers, freeze a regression baseline under the old stack, port module by module in dependency order, then remove the old dependencies. Use whenever someone wants to replace, drop or migrate off archetypal, eppy or geomeppy (IDF, idfobjects, newidfobject, getobject, add_block, intersect_match, set_wwr, Sql.timeseries_by_name, Schedule.from_values, EnergyPlusVersion), move an EnergyPlus Python package or pipeline to idfkit, or asks whether results will stay the same after such a switch, even if they never say 'migration'. Not for upgrading an IDF file to a newer EnergyPlus version (upgrade-version) or for writing new idfkit code from scratch (developing-with-idfkit)."
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/scripts/inventory.py:*) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/inventory.py:*)
---

# Migrating a codebase to idfkit

This skill runs a library swap on an EnergyPlus Python codebase: archetypal, eppy and geomeppy out, idfkit's **native** API in. The goal people actually have is rarely "use idfkit". It is "use idfkit **and keep every number my users rely on**". So the work is organised around one question: how will we *prove* the results did not change?

That proof is the backbone of the process: freeze outputs under the old stack first, port, then compare at an agreed tolerance. Everything else (the order of work, the review gates, the pitfalls list) exists to keep that proof honest.

## Skills this one leans on

- **superpowers:using-superpowers**: load it first. This migration is a multi-week-of-work change compressed into one session, and its phases map onto superpowers' process skills: `brainstorming` → `writing-plans` → `subagent-driven-development` (or `executing-plans`) → `requesting-code-review` → `finishing-a-development-branch`. Follow those skills for the mechanics; this skill supplies the domain content at each stage. If the superpowers plugin isn't installed, follow the same phases inline: a design doc the user approves, a written plan, implement-then-review per task, a final whole-branch review.
- **developing-with-idfkit**: the version-matched idfkit API reference. Invoke that skill (it runs its own discovery against the project) once idfkit is installed in the project being migrated; if it isn't available as a skill but the plugin is installed whole, its script is at `${CLAUDE_SKILL_DIR}/../developing-with-idfkit/scripts/discover.py --project-dir <repo>`. Read the topic files (`document-and-objects`, `geometry-builders-and-zoning`, `schedule-evaluation`, `result-parsing`, `simulation-execution`, `version-migration`, …) before writing code against them. Hand the same instruction to every implementer subagent you dispatch.

Bundled with this skill:

- `references/api-mapping.md`: archetypal/eppy/geomeppy call → idfkit native equivalent, with the behavioural differences that matter. Read before planning and give it to implementers.
- `references/pitfalls.md`: the traps that cost real migrations days (silent result changes, nondeterminism, test fixtures that were never physical). Read before planning; point reviewers at it.
- `references/baseline-and-parity.md`: how to capture a baseline that is worth trusting and compare against it. Read before writing the first task.
- `scripts/inventory.py`: deterministic inventory of old-library usage. Run it first.

## Phase 1: Recon (before saying anything substantive)

1. Run `python ${CLAUDE_SKILL_DIR}/scripts/inventory.py <repo>`. It lists imports (including notebook code cells), old-API calls and constructor calls, the files that concentrate them, and the public functions, class attributes and module attributes whose annotations expose old-library types (`IDF`, `Sql`, `EpBunch`, `Schedule`), with tests listed separately. That last list is the breaking surface.
2. Find the **downstream consumers** (other repos, notebooks, services that import this package) and read what they actually call. Ask the user for them if they are not obvious; offer to clone them. In practice consumers use far less than the full public API, and often only one or two lines touch old-library objects. That changes the scope from "breaking rewrite" to "one-line migration for consumers".
3. Split the public interface into two layers and say so plainly:
   - **Inputs and computed results** (pydantic models, plain pandas frames, numbers): these can and should stay identical.
   - **Old-library objects that leak out** (`.idf`, `.sql`, callbacks typed on `IDF`, `add_to_idf(idf)` methods): these break on purpose. Plan a major version bump, and give each consumer-facing leak a project-owned replacement (in epinterface's migration, a `hourly_timeseries(names)` method instead of exposing `Sql.timeseries_by_name`), never an eppy-shaped shim.
4. Look for **mirror classes**: project classes that each copy one EnergyPlus object (pydantic models or dataclasses named `Material`, `People`, `RunPeriod`, … with eppy-style fields and an `add(idf)` method). eppy validated nothing, so codebases grew them to get typed fields. idfkit validates every field against the schema, so they become duplicates once the port lands. Count them; they are the subject of task 11.
5. Note the EnergyPlus versions CI runs, whether a base IDF file is loaded and migrated, and which old-library behaviours the code depends on implicitly (`pitfalls.md` lists what to look for).

## Phase 2: Brainstorm the contract (superpowers:brainstorming)

Ask *why* the user is migrating. The answer sets how much must stay byte-identical. Then settle, one question at a time:

- Which consumer-facing leaks get replacements and which simply break.
- Whether zone names and object names must stay identical (they usually must: they end up as labels in stored results).
- The parity tolerance, what happens when a value misses it (stop, explain, user signs off; never loosen silently), and who signs off.
- The approach. Recommend **freeze a baseline, then switch everything on one branch in dependency order**: the old model object is threaded through everything, so module-by-module bridges are throwaway work and side-by-side builders double the code. Mention the alternatives in one line each.
- Point out early that the existing unit tests are usually *not* enough. Check whether any test asserts simulated outputs (in epinterface, the only test that ran EnergyPlus asserted nothing).

Write the design doc, review it yourself (or with a fresh subagent), and get the user's approval, as brainstorming requires.

## Phase 3: Plan (superpowers:writing-plans)

Use this task order; adapt names to the codebase. Each task's tests must be green when it lands, except the expected red window described below.

1. **Baseline capture (old stack still installed).** See `baseline-and-parity.md`. Includes a sanity check that the baseline models are physically plausible, and a new consumer-facing method implemented on the old stack so the regression test already uses the final API.
2. **Dependency + settings.** Add idfkit (pin a minor series, e.g. `>=1.2,<1.3`, because parity is only proven for the version you test). Replace `EnergyPlusVersion` with version tuples and `find_energyplus`. Which EnergyPlus version to use by default is a contract decision; in epinterface the newest installed version the code had per-version tables for worked, where the newest installed one crashed.
3. **Results reading.** Replace archetypal `Sql` with idfkit `SQLResult` plus small project-owned frame builders that reproduce the old frame shape exactly. This can land while the old stack still builds models, so the suite stays green.
4. **Document and schedule helpers.** Build the base document programmatically (`new_document(version)` plus `doc.add`); do not load-and-migrate a packaged IDF. Add a value-schedule writer that reproduces the old schedule objects exactly. These are new modules; nothing is rewired yet.
5. **Object writers** (the lowest layer that takes the model object).
6. **Components** that call those writers.
7. **Geometry** (zones, surfaces, windows, shading, matching, rotation).
8. **Build, simulate, run**: the regression test turns green again here.
9. **Legacy paths** (older builders, CLIs, notebooks, scripts).
10. **Remove the old dependencies**, declare transitive deps they used to provide, changelog with the breaking list and the consumer migration snippet, version bump.
11. **Retire mirror classes** (if recon found them), once parity holds. Replace each with direct `doc.add(type, name, **snake_case_fields)` calls at its call sites, and keep only real helpers (reuse-or-replace writer, version-renamed field lookup, domain libraries). Carry every non-schema default over explicitly. Gate it with byte-identical IDF snapshots (`baseline-and-parity.md`), not the simulation tolerance: the written model must not change at all. Domain models that consumers use (components stored in a database, say) are not mirrors; keep them.

Tasks 5-8 share the model object, so between them, tests of not-yet-ported modules fail. Say this in the plan as an explicit ruling ("tests of ported code and unrelated tests must pass; end-to-end tests may fail until task 8") so neither implementers nor reviewers chase it.

Put the pitfalls that apply to a task *in that task's text*: implementers only see their own brief.

## Phase 4: Execute (superpowers:subagent-driven-development)

Recommend subagent-driven execution: tasks hand each other exact signatures, and during the red window only per-task review catches a wrong turn. Things that made it work:

- Brief every implementer to read `api-mapping.md` and the relevant developing-with-idfkit references, to use the native API only, and to stop and report rather than loosen a tolerance or reproduce a bug by guessing.
- Give reviewers **named risks** for the task, drawn from `pitfalls.md` (duplicate-name semantics, type-limits objects, weekday mapping, zone naming, units, output objects, connection lifetime), and the reference artefacts (captured IDFs, fixtures) to check against.
- Use stronger models for geometry and build/simulate tasks and their reviews; they need judgement.
- When an implementer finds the old library doing something wrong (wrong surface pairing, nondeterministic ordering), decide explicitly between reproducing it for parity and fixing it, record the decision, and pin the difference in a test. Do not let it slide by silently. Fixes that change results become separate follow-ups unless the user wants them now.

## Phase 5: Finish

Before offering merge or PR options (superpowers:finishing-a-development-branch):

- Run the final whole-branch review and give it the consumer's actual call sites to walk.
- Re-run `inventory.py` and expect zero old-library imports and no old-API calls apart from idfkit's own `removeidfobject` and `copyidfobject` (idfkit's other eppy-shaped methods would otherwise keep un-ported code running silently).
- Check pre-commit and CI **against the main branch**, not against an earlier commit of the migration branch. Formatter churn and new fixtures are the usual culprits.
- Search every written IDF for `np.` (tests and snapshots): numpy scalars reach the IDF text as `np.float64(...)` only for some values (see `pitfalls.md`).
- Run the suite (or at least no-simulation tests) under every EnergyPlus version CI uses; field names differ across schema versions. `idfkit check --targets …` lints models across versions.
- Benchmark old against new on the same machine and the same model: import time, first build in a fresh process, later builds, and a full run. Report results equality alongside. The first build in a fresh process is where a base-file migration hides (tens of seconds).
- List every decision made on the user's behalf, each with its cost if wrong, and the follow-ups that change results (they need their own baseline and sign-off).
