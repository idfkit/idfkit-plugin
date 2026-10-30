# AGENTS.md

Guidance for AI coding agents (Claude Code, Cursor, Copilot, …) working in this
repository.

## Repository overview

This repo is the **idfkit agentic plugin** — the harness that brings idfkit to AI
clients. It packages an MCP server reference, an LSP config, skills, agents,
commands, and hooks (see [README.md](README.md) for the full layout).

It does **not** contain the idfkit library reference documentation. That content
ships inside the idfkit pip package (>=0.13) at
`idfkit/.agents/skills/developing-with-idfkit/`, and for idfkit-js at the same
sub-path of the `@idfkit/idfkit` or `@idfkit/core` npm package, and is
version-matched to each release. New or updated **library reference content**
belongs upstream in idfkit or idfkit-js, not here.

## Where things live

| Concern | Location | Edit here? |
|---|---|---|
| Library API reference docs | idfkit pip package / `@idfkit/*` npm packages (`.agents/skills/developing-with-idfkit/`) | No — contribute upstream |
| Discovery of those docs | `skills/developing-with-idfkit/SKILL.md` + `scripts/discover.py` | Yes |
| Tool-driven workflow playbooks | `skills/{simulate,validate,new-model,…}/SKILL.md` | Yes |
| Sub-agents | `agents/*.md` | Yes |
| Slash commands | `commands/*.md` | Yes |
| Context hooks | `hooks/hooks.json`, `scripts/*.sh` | Yes |
| MCP server wiring | `.mcp.json` (`uvx idfkit-mcp@<version>`, pinned) | Yes, by review |
| LSP wiring | `.lsp.json` (`uvx --from idfkit-lsp==<version> --prerelease=allow`, pinned) | Yes, by review |
| Claude plugin / marketplace | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Yes |

## Discovery contract

`skills/developing-with-idfkit/scripts/discover.py` resolves the bundled reference
skill for one of two languages, chosen by `--language` (`python`, `js`, or `auto`,
the default: `js` when the project directory's `package.json` names an `@idfkit/`
package or one is installed in reach, and no Python manifest is present).

For Python, by:

1. Detecting the active interpreter, in priority order: `$VIRTUAL_ENV` → `./.venv`
   → `../.venv` → `<git-root>/.venv` → `$CONDA_PREFIX` → `pipenv` (if `Pipfile`) →
   `poetry` (if `poetry.lock`) → `pdm` (if `pdm.lock`) → `uv` (if `uv.lock`) →
   system `python3` / `python`.
2. Running `import idfkit; print(idfkit.__path__[0])` to locate the package.
3. Loading `<idfkit_path>/.agents/skills/developing-with-idfkit/SKILL.md`.
4. Falling back to `pip install idfkit` when missing (exit 1), an upgrade prompt
   when the installed idfkit predates bundled skills (exit 2), or
   https://docs.idfkit.com as a last resort.

For JavaScript/TypeScript, by:

1. Walking `node_modules/` up from the project directory for `@idfkit/idfkit`,
   then `@idfkit/core` (also from the facade's resolved path, for pnpm). No Node
   interpreter is run.
2. Loading `<package>/.agents/skills/developing-with-idfkit/SKILL.md` from the
   first package that has it.
3. Falling back to the lockfile's install command (exit 1), or, when the installed
   release bundles no skill, to its READMEs and `.d.ts` declarations plus
   https://js.idfkit.com (exit 2). No idfkit-js release bundles the skill yet, so
   exit 2 is the normal JS outcome until one does.

Exit codes are part of the contract and mean the same in both languages (0
success, 1 not installed, 2 installed but no bundled skill, 3 no Python
interpreter, 4 layout changed upstream, 5 bad argument). Preserve them — changes to
interpreter detection order, the package-path lookup, or fallback behavior should
be explicit and reviewed.

## Design boundary: references vs. tools

Keep the two surfaces separate:

- **`developing-with-idfkit`** is for writing code against the library, in Python
  or JavaScript/TypeScript. It is MCP-free and discovers version-matched docs from
  the user's installed idfkit.
- **The MCP server and workflow skills** are for interacting with IDF models through
  tools. Do not duplicate library reference content into the workflow skills, and do
  not route library references through the MCP — that coupling is intentionally
  avoided so library authoring works without spinning up the server.

## Delivery paths and the consumer register

This plugin hands idfkit to a person's editor, so what it pins is what they run.
It is `idfkit-plugin` in the consumer register, `governance/consumers.toml` in
idfkit-conformance (feature 004 of the unification), with role `delivers`,
depending on `idfkit-mcp` and `idfkit-lsp`, and adopting in wave 2 after them.

- **`.mcp.json` pins idfkit-mcp exactly** (`idfkit-mcp@X.Y.Z`). Never remove the
  version: an unpinned `uvx idfkit-mcp` runs whatever is newest on the day, so a
  release would reach users unreviewed. The user still types no version; the
  level is committed here. The idfkit level follows from that release's own pin.
- **`.lsp.json` pins idfkit-lsp exactly** (`--from idfkit-lsp==X.Y.Z`), on the
  same terms as `.mcp.json`. `--prerelease=allow` follows the pin while
  idfkit-lsp depends on a pre-release of idfkit, because uv installs a
  pre-release of an indirect dependency only when told to. Keep the flag after
  the pin, so the level stays at `args[1]` where the consumer register reads it,
  and drop it once idfkit-lsp depends on a stable idfkit.
- **Both files are CODEOWNERS-reviewed**, because changing either changes what
  every user runs.
- **The self-check.** The `consumer-register` job in `tests.yml` calls
  `check-consumer.yml` at a pinned governance tag and fails if the register no
  longer describes this repository.
- **Adoption.** `bump-idfkit.yml` refuses to adopt an idfkit level until
  idfkit-mcp has published a release pinning it, naming it, then moves the pin
  in `.mcp.json` and opens a pull request. `rehearse-candidate.yml` rehearses
  through the two servers, since this repository holds no code that calls idfkit.
