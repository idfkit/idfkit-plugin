# idfkit plugin

The agentic plugin for [idfkit](https://idfkit.com) — EnergyPlus building energy
modeling for AI coding assistants. It bundles everything an agent needs to create,
validate, simulate, and reason about building energy models, and installs across
Claude Code, Cursor, Copilot, Gemini, Codex, and any MCP-capable client.

## What's in the box

| Layer | What it does |
|---|---|
| **MCP server** (`uvx idfkit-mcp@<version>`, pinned in `.mcp.json`) | Tools and `idfkit://…` resources to load, query, edit, validate, and simulate IDF / epJSON models. |
| **`developing-with-idfkit` skill** | Discovers the idfkit installed in your project — the Python package or the JavaScript/TypeScript `@idfkit/*` packages — and loads **version-matched** reference docs for writing code against the library. |
| **Workflow skills** | Task playbooks that orchestrate the MCP tools: `simulate`, `validate`, `new-model`, `load-model`, `energy-audit`, `weather`, `upgrade-version`, `idf-conventions`, `docs`. |
| **Agents** | Focused sub-agents: `energy-modeler`, `envelope-analyst`, `hvac-designer`. |
| **Commands & hooks** | `/quick-sim` slash command; context hooks that nudge agents toward the structured MCP tools when they touch `.idf` / `.epJSON` / `.epw` / `.ddy` files. |
| **LSP** | Python LSP for idfkit-based code (`idfkit-lsp`) via `.lsp.json`. |

> **Note on the LSP.** `idfkit-lsp` is a language server for *Python code that
> imports idfkit* — it does **not** provide an IDF/epJSON language server. Because
> it registers `.py` → `python`, the host attaches it to **every** Python file in
> the project, where it coexists with (and may compete with) your primary Python
> LSP such as Pylance, pyright, or ruff-lsp. If your editor supports scoping a
> server by workspace or activation pattern, narrow it to idfkit projects.

## Two contexts, two surfaces

The plugin deliberately separates two kinds of work:

- **Writing code _with_ idfkit** (`import idfkit` in Python, `@idfkit/*` in
  JavaScript/TypeScript) → the **`developing-with-idfkit` skill**. It resolves the
  idfkit installed in your project and loads the reference set that matches that
  exact version, so guidance never drifts from the API your code runs against.
  This works **without the MCP server** — it's pure library authoring.
- **Interacting with an IDF model _through_ the assistant** → the **MCP server** plus
  the **workflow skills**. Here the agent calls tools (`load_model`, `run_simulation`,
  …) rather than writing idfkit code.

The reference documentation lives **inside the installed package**, not in this
repo: in the idfkit pip package (>=0.13) at
`idfkit/.agents/skills/developing-with-idfkit/`, and at the same sub-path of
`@idfkit/idfkit` or `@idfkit/core` on npm. The skill just discovers and routes to
it — install once, and every project automatically gets the docs matched to its
pinned idfkit version. Until an idfkit-js release bundles that skill, the JS side
routes to the installed package's README and `.d.ts` declarations (version-matched)
and to [js.idfkit.com](https://js.idfkit.com).

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

For Claude Desktop, ChatGPT, or other MCP clients, add the server directly, pinned
to the version the plugin's own [`.mcp.json`](.mcp.json) names:

```json
{
  "mcpServers": {
    "idfkit": { "command": "uvx", "args": ["idfkit-mcp@<version>"] }
  }
}
```

Pin a version. Without one, `uvx` runs whatever is newest on the day, so a release
reaches your client the moment it publishes, reviewed by nobody in between. The
plugin itself always pins, and you type no version when you install it.

## Requirements

- For the `developing-with-idfkit` skill, either:
  - **Python 3.10+** with **idfkit >= 0.13** installed in your project. Older
    idfkit falls back to [docs.idfkit.com](https://docs.idfkit.com).
  - **`@idfkit/idfkit`** (or `@idfkit/core`) installed under the project's
    `node_modules/`. The script itself still runs on Python; it needs no Node.
- **[uv](https://docs.astral.sh/uv/)** (`uvx`) to run the `idfkit-mcp` server.
- **EnergyPlus** installed on the host to run simulations (idfkit discovers it via
  `$ENERGYPLUS_DIR`, `$PATH`, or standard install locations).

## How discovery works

The `developing-with-idfkit` skill runs
[`scripts/discover.py`](skills/developing-with-idfkit/scripts/discover.py). Its
`--language` flag picks `python` or `js`; the default, `auto`, picks `js` when the
project's `package.json` names an `@idfkit/` package (or one is installed) and no
Python manifest is present.

For **Python**, it:

1. Detects the active interpreter, in priority order: `$VIRTUAL_ENV` → `./.venv` →
   `../.venv` → `<git-root>/.venv` → `$CONDA_PREFIX` → `pipenv` → `poetry` → `pdm` →
   `uv` → system `python3` / `python`.
2. Runs `import idfkit; print(idfkit.__path__[0])` to locate the installed package.
3. Loads `<idfkit_path>/.agents/skills/developing-with-idfkit/SKILL.md` and routes
   into its `references/`.
4. Falls back with actionable instructions when idfkit is missing (`pip install
   idfkit`) or predates bundled skills (upgrade, or use docs.idfkit.com).

For **JavaScript/TypeScript**, it:

1. Walks `node_modules/` up from the project directory, as Node resolves a bare
   specifier, for `@idfkit/idfkit` and then `@idfkit/core` (following pnpm's
   symlinks). Yarn Plug'n'Play installs are not resolved.
2. Loads `<package>/.agents/skills/developing-with-idfkit/SKILL.md` from the first
   package that has one.
3. Falls back with the install command for the project's package manager (by
   lockfile) when nothing is installed, or with the installed READMEs, `.d.ts`
   declarations, and js.idfkit.com when the installed release bundles no skill.

## License

MIT — see [LICENSE](LICENSE).
