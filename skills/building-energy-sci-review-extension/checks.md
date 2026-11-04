# Domain checks: idfkit model validation

The building physicist runs these checks during the independent round, for every EnergyPlus model file in the review scope. They reuse idfkit's existing schema validation (`validate_model`) and model-integrity checks (`check_model_integrity`); they do not reimplement them. Each failure becomes a candidate finding in the building physicist's output, so that it is debated and reported with the other findings.

## 1. Rules

1. **Read only.** Load each model read-only. Never call `save_model`, `update_object`, `add_object`, `remove_object`, `rename_object`, `migrate_model` or any other tool that changes a model, and never write to a project file.
2. **No simulation.** Never call `run_simulation`, and never start EnergyPlus by any other means, unless the user has explicitly requested a simulation for this review. The checks below need no EnergyPlus installation.
3. **No substitute verdicts.** When neither route of section 3 is available, report the checks as not run. Do not replace them with a manual reading of the model presented as their result; a manual reading is reported as ordinary findings.

## 2. Files checked

Check every file of `scope.json` whose extension is `.idf` or `.epjson`, compared case-insensitively. Weather files (`.epw`) and simulation outputs (`eplusout*`) are reviewed by reading, not by these checks. Resolve each path against the project root given for the review.

## 3. Procedure

For each file, use the first route that is available, in this order.

### Route A: the idfkit MCP server

The server is named `idfkit`. Its tools appear as `load_model`, `validate_model` and `check_model_integrity` (on Claude Code, with the prefix of the plugin's server, for example `mcp__plugin_idfkit_idfkit__validate_model`).

1. Call `load_model` with `file_path` set to the absolute path of the file. A load that fails because the file cannot be parsed (for example, no detectable version or a malformed object) is itself a failure: report it as a finding as described in section 4.
2. Call `validate_model` with its defaults (all object types, `check_references` true). Collect every item of severity `error` or `warning`.
3. Call `check_model_integrity`. Collect every item of severity `error` or `warning`.

`load_model` replaces the server session's active model. State in the output `notes` which files were loaded, so that the user knows the session model changed. Do not save the session model.

### Route B: the idfkit Python package

Use this route when the MCP tools are not available to you (for example, in a subagent without MCP access) or the server does not respond.

1. Read the pinned `idfkit-mcp` requirement from the idfkit plugin's `.mcp.json`, two directories above this file (`mcpServers.idfkit.args[0]`, for example `idfkit-mcp@0.11.1`). The package includes idfkit, and pinning it gives the same checks as Route A.
2. Run the script below once per file, from a directory outside the project, with `uvx --from '<requirement>' python -I - <absolute path to the model>`, passing the script on standard input. If `uvx` is absent, run the same script with an interpreter in which `idfkit` is installed (for example, the project's own virtual environment); `check_model_integrity` then runs only if `idfkit-mcp` is installed in that interpreter, and otherwise the script reports it as not run.
3. Each line of output is one JSON object. Lines with `"check": "load"` report a file that could not be loaded; lines with `"status": "not run"` report a check that could not run; every other line is one failure.

```python
import json
import sys
from pathlib import Path

from idfkit import load_epjson, load_idf, validate_document

path = Path(sys.argv[1])
loader = load_epjson if path.suffix.lower() in (".epjson", ".json") else load_idf
try:
    doc = loader(str(path), strict=True)  # read into memory; the file is never written
except Exception as exc:
    print(json.dumps({"check": "load", "severity": "error", "message": f"{type(exc).__name__}: {exc}"}))
    raise SystemExit(0) from None

result = validate_document(doc, check_references=True)
for issue in result.errors + result.warnings:
    print(json.dumps({
        "check": "validate_model", "severity": issue.severity.value, "object_type": issue.obj_type,
        "object_name": issue.obj_name, "field": issue.field, "code": issue.code, "message": issue.message,
    }))

try:
    from idfkit_mcp.state import get_state
    from idfkit_mcp.tools.integrity import check_model_integrity
except ImportError:
    print(json.dumps({"check": "check_model_integrity", "status": "not run", "reason": "idfkit-mcp is not installed"}))
else:
    state = get_state()
    state.persistence_enabled = False  # no session file is written
    state.document = doc
    for issue in check_model_integrity().issues:
        print(json.dumps({
            "check": "check_model_integrity", "severity": issue.severity, "category": issue.category,
            "object_type": issue.object_type, "object_name": issue.object_name, "message": issue.message,
        }))
```

### Route C: not run

When neither route is available, run no check for the file and state in the output `notes`, for each file: its path, the checks not run (`validate_model`, `check_model_integrity` or both) and the reason (for example, "no idfkit MCP tools in this session and `uvx` not found"). Do the same for a single check that Route B reports as not run.

## 4. From failure to candidate finding

Each failure of severity `error` or `warning`, and each load failure, becomes one candidate finding with the fields of `candidate-findings.schema.json`:

| Field | Value |
|---|---|
| `id`, `raised_by` | `building-physicist-<n>` and `building-physicist`, numbered with the other findings of the building physicist |
| `file` | The model file's path as it appears in `scope.json` |
| `line_start`, `line_end` | The lines of the failing field in the file: in an IDF file, the line holding the field value (its `!-` comment names the field); in an epJSON file, the line of the field's key; for an object-level failure with no field, the line of the object's type or name. For a load failure, the line the parser reports, or the first scoped line of the file when it reports none |
| `dimension` | `physical-modelling-and-units` |
| `severity` | `high` for a failure of severity `error` and for a load failure, because EnergyPlus rejects or misreads the model; `low` for a failure of severity `warning`, raised to `medium` or `high` only when the finding states a concrete scenario in which the result is wrong |
| `summary` | One sentence naming the object, the field and the defect, for example "Surface Office South Wall references construction Exterior Wall Insulated, which is not defined." |
| `trigger` | The object and field as written: object type, object name, field name and value, for example "BuildingSurface:Detailed `Office South Wall`, field `construction_name` = `Exterior Wall Insulated`" |
| `wrong_output` | The check's error message, with its code where one is given, and its consequence, for example "validate_model E009: Reference to non-existent object 'EXTERIOR WALL INSULATED'; EnergyPlus stops with a severe error before the first timestep" |
| `fix` | The model change that removes the failure, for example defining the missing object or correcting the reference to an existing name |
| `evidence` | The route used (A or B, with the `idfkit-mcp` requirement for B), the check and the raw failure record |

Then apply these rules:

1. **Scope.** When the failing line lies outside the file's `line_ranges` in `scope.json`, do not report a finding (it would fall outside the review scope); list the failure in `notes` instead.
2. **Duplicates.** When both checks report the same object and field, report one finding and cite both records in `evidence`.
3. **Checked items.** For each file whose checks ran with no failure of severity `error` or `warning`, add one checked item with the file's first and last scoped lines, the dimension `physical-modelling-and-units` and a note naming the checks run and the route.
4. **Notes.** Always state in `notes` which files were checked, by which route, and which checks were not run and why.

The findings take part in the debate on the same terms as every other finding. Other members may challenge a finding, for example when the failing object is unused, and the debate decides it.
