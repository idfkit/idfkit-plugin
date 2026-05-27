# AGENTS.md

Guidance for AI coding agents (Claude Code, Cursor, Copilot, …) working in this
repository.

## Repository overview

This repo is the **idfkit agentic plugin** — the harness that brings idfkit to AI
clients. It packages an MCP server reference, an LSP config, skills, agents,
commands, and hooks (see [README.md](README.md) for the full layout).

It does **not** contain the idfkit library reference documentation. That content
ships inside the idfkit pip package (>=0.13) at
`idfkit/.agents/skills/developing-with-idfkit/` and is version-matched to each
release. New or updated **library reference content** belongs upstream in the
idfkit package, not here.

## Where things live

| Concern | Location | Edit here? |
|---|---|---|
| Library API reference docs | idfkit pip package (`idfkit/.agents/skills/developing-with-idfkit/`) | No — contribute upstream |
| Discovery of those docs | `skills/developing-with-idfkit/SKILL.md` + `scripts/discover.py` | Yes |
| Tool-driven workflow playbooks | `skills/{simulate,validate,new-model,…}/SKILL.md` | Yes |
| Sub-agents | `agents/*.md` | Yes |
| Slash commands | `commands/*.md` | Yes |
| Context hooks | `hooks/hooks.json`, `scripts/*.sh` | Yes |
| MCP server wiring | `.mcp.json` (`uvx idfkit-mcp`) | Yes |
| Claude plugin / marketplace | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Yes |

## Discovery contract

`skills/developing-with-idfkit/scripts/discover.py` resolves the bundled reference
skill by:

1. Detecting the active interpreter, in priority order: `$VIRTUAL_ENV` → `./.venv`
   → `../.venv` → `<git-root>/.venv` → `$CONDA_PREFIX` → `pipenv` (if `Pipfile`) →
   `poetry` (if `poetry.lock`) → `pdm` (if `pdm.lock`) → `uv` (if `uv.lock`) →
   system `python3` / `python`.
2. Running `import idfkit; print(idfkit.__path__[0])` to locate the package.
3. Loading `<idfkit_path>/.agents/skills/developing-with-idfkit/SKILL.md`.
4. Falling back to `pip install idfkit` when missing (exit 1), an upgrade prompt
   when the installed idfkit predates bundled skills (exit 2), or
   https://docs.idfkit.com as a last resort.

Exit codes are part of the contract (0 success, 1 not installed, 2 too old, 3 no
interpreter, 4 layout changed upstream, 5 bad argument). Preserve them — changes to
interpreter detection order, the package-path lookup, or fallback behavior should
be explicit and reviewed.

## Design boundary: references vs. tools

Keep the two surfaces separate:

- **`developing-with-idfkit`** is for writing Python code against the library. It is
  MCP-free and discovers version-matched docs from the user's installed idfkit.
- **The MCP server and workflow skills** are for interacting with IDF models through
  tools. Do not duplicate library reference content into the workflow skills, and do
  not route library references through the MCP — that coupling is intentionally
  avoided so library authoring works without spinning up the server.
