# idfkit plugin

The agentic plugin for [idfkit](https://idfkit.com) — EnergyPlus building energy
modeling for AI coding assistants. It bundles everything an agent needs to create,
validate, simulate, and reason about building energy models, and installs across
Claude Code, Cursor, Copilot, Gemini, Codex, and any MCP-capable client.

## What's in the box

| Layer | What it does |
|---|---|
| **MCP server** (`uvx idfkit-mcp`) | Tools and `idfkit://…` resources to load, query, edit, validate, and simulate IDF / epJSON models. |
| **`developing-with-idfkit` skill** | Discovers the idfkit installed in your project and loads **version-matched** reference docs for writing Python against the library. |
| **Workflow skills** | Task playbooks that orchestrate the MCP tools: `simulate`, `validate`, `new-model`, `load-model`, `energy-audit`, `weather`, `upgrade-version`, `idf-conventions`, `docs`. |
| **Agents** | Focused sub-agents: `energy-modeler`, `envelope-analyst`, `hvac-designer`. |
| **Commands & hooks** | `/quick-sim` slash command; context hooks that nudge agents toward the structured MCP tools when they touch `.idf` / `.epJSON` / `.epw` / `.ddy` files. |
| **LSP** | EnergyPlus language support via `.lsp.json`. |

## Two contexts, two surfaces

The plugin deliberately separates two kinds of work:

- **Writing Python code _with_ idfkit** (`import idfkit`) → the **`developing-with-idfkit`
  skill**. It resolves the idfkit installed in your project and loads the reference
  set that matches that exact version, so guidance never drifts from the API your
  code runs against. This works **without the MCP server** — it's pure library
  authoring.
- **Interacting with an IDF model _through_ the assistant** → the **MCP server** plus
  the **workflow skills**. Here the agent calls tools (`load_model`, `run_simulation`,
  …) rather than writing idfkit code.

The reference documentation lives **inside the idfkit pip package** (>=0.13, at
`idfkit/.agents/skills/developing-with-idfkit/`), not in this repo. The skill just
discovers and routes to it — install once, and every project automatically gets the
docs matched to its pinned idfkit version.

## Installation

### Claude Code — full plugin (recommended)

Installs the MCP server, skills, agents, commands, and hooks together:

```
/plugin marketplace add idfkit/idfkit-plugin
/plugin install idfkit@idfkit
```

### Cross-agent skills — `npx skills`

[`skills`](https://github.com/vercel-labs/skills) is a cross-agent installer
(Claude Code, Cursor, Copilot, Gemini CLI, Codex, …). Install the package-authoring
skill at the user level so it works across every project:

```bash
npx skills add idfkit/idfkit-plugin -s developing-with-idfkit -g
```

`-s` picks a specific skill; `-g` installs globally (drop it to install into the
current project's `.<agent>/skills/`). Omit `-s` to add the workflow skills too —
those pair with the MCP server below.

### GitHub Copilot

```bash
gh skill install idfkit/idfkit-plugin developing-with-idfkit --scope user
```

### Cursor

```bash
gh skill install idfkit/idfkit-plugin developing-with-idfkit --agent cursor --scope user
```

### Gemini CLI

```bash
gemini skills install https://github.com/idfkit/idfkit-plugin.git
```

### OpenAI Codex

From inside a Codex session, run `$skill-installer` and point it at
`idfkit/idfkit-plugin`. The repo also ships a `.codex-plugin/` manifest.

### MCP server — any MCP-capable client

For Claude Desktop, ChatGPT, or other MCP clients, add the server directly:

```json
{
  "mcpServers": {
    "idfkit": { "command": "uvx", "args": ["idfkit-mcp"] }
  }
}
```

## Requirements

- **Python 3.10+** with **idfkit >= 0.13** installed in your project — required for
  the `developing-with-idfkit` skill to find version-matched references. Older
  idfkit falls back to [docs.idfkit.com](https://docs.idfkit.com).
- **[uv](https://docs.astral.sh/uv/)** (`uvx`) to run the `idfkit-mcp` server.
- **EnergyPlus** installed on the host to run simulations (idfkit discovers it via
  `$ENERGYPLUS_DIR`, `$PATH`, or standard install locations).

## How discovery works

The `developing-with-idfkit` skill runs
[`scripts/discover.py`](skills/developing-with-idfkit/scripts/discover.py), which:

1. Detects the active interpreter, in priority order: `$VIRTUAL_ENV` → `./.venv` →
   `../.venv` → `<git-root>/.venv` → `$CONDA_PREFIX` → `pipenv` → `poetry` → `pdm` →
   `uv` → system `python3` / `python`.
2. Runs `import idfkit; print(idfkit.__path__[0])` to locate the installed package.
3. Loads `<idfkit_path>/.agents/skills/developing-with-idfkit/SKILL.md` and routes
   into its `references/`.
4. Falls back with actionable instructions when idfkit is missing (`pip install
   idfkit`) or predates bundled skills (upgrade, or use docs.idfkit.com).

## License

MIT — see [LICENSE](LICENSE).
