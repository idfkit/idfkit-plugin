#!/usr/bin/env bash
# inject-idf-context.sh — Add EnergyPlus context when working with relevant files.
#
# Wired as a PreToolUse hook (Read|Edit|Write). PreToolUse plain stdout is NOT shown to the
# model — context must be returned as JSON via hookSpecificOutput.additionalContext.

# Read tool input from stdin
input=$(cat)

# Extract the target file path. PreToolUse nests it under .tool_input.file_path; fall back to a
# top-level .file_path. Requires jq for robust parsing (handles spaces, quotes, escapes).
if command -v jq &>/dev/null; then
    file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .file_path // empty' 2>/dev/null)
else
    # Minimal fallback if jq is unavailable.
    file_path=$(printf '%s' "$input" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//; s/"$//')
fi

if [[ -z "$file_path" ]]; then
    exit 0
fi

# Lowercase extension
ext_lower=$(printf '%s' "${file_path##*.}" | tr '[:upper:]' '[:lower:]')

case "$ext_lower" in
    idf)
        context="This is an EnergyPlus Input Data File (.idf). For structured editing, use the idfkit MCP tools (load_model, list_objects, update_object, add_object) or read the idfkit://model/objects/{type}/{name} resource rather than raw text manipulation. The MCP tools handle reference tracking and validation automatically."
        ;;
    epjson)
        context="This is an EnergyPlus JSON input file (.epJSON). For structured editing, use the idfkit MCP tools (load_model, list_objects, update_object) which handle schema validation and reference integrity."
        ;;
    epw)
        context="This is an EnergyPlus Weather file (.epw). Use search_weather_stations and download_weather_file MCP tools to find and manage weather data. EPW files should generally not be edited manually."
        ;;
    ddy)
        context="This is an EnergyPlus Design Day file (.ddy), typically paired with an EPW weather file. Design day data drives HVAC autosizing; the design days must be injected into the model as SizingPeriod:DesignDay objects."
        ;;
    *)
        exit 0
        ;;
esac

# Emit as PreToolUse additionalContext so the model actually sees it.
if command -v jq &>/dev/null; then
    jq -n --arg ctx "[idfkit] $context" \
        '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $ctx}}'
else
    # Hand-rolled JSON fallback; context strings above contain no characters needing escaping.
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"[idfkit] %s"}}\n' "$context"
fi

exit 0
