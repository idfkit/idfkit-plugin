#!/usr/bin/env bash
# check-deps.sh — Verify idfkit plugin dependencies on session startup

set -euo pipefail

issues=()
info=()

# 1. Check uvx
if command -v uvx &>/dev/null; then
    info+=("uvx: available ($(uvx --version 2>/dev/null || echo 'unknown version'))")
else
    issues+=("uvx is not installed. Install uv (https://docs.astral.sh/uv/getting-started/installation/) to use the idfkit MCP server and LSP.")
fi

# 2. Look for EnergyPlus installation
ep_dir=""

# Check user config first
if [[ -n "${CLAUDE_PLUGIN_OPTION_ENERGYPLUS_DIR:-}" ]]; then
    if [[ -d "$CLAUDE_PLUGIN_OPTION_ENERGYPLUS_DIR" ]]; then
        ep_dir="$CLAUDE_PLUGIN_OPTION_ENERGYPLUS_DIR"
    fi
fi

# Check ENERGYPLUS_DIR env var
if [[ -z "$ep_dir" && -n "${ENERGYPLUS_DIR:-}" ]]; then
    if [[ -d "$ENERGYPLUS_DIR" ]]; then
        ep_dir="$ENERGYPLUS_DIR"
    fi
fi

# Auto-detect (macOS + Linux standard locations). Glob expansion is lexical, so
# EnergyPlus-9.6.0 would sort after EnergyPlus-25.2.0 — pick the highest version
# explicitly with `sort -V`.
if [[ -z "$ep_dir" ]]; then
    shopt -s nullglob
    ep_candidates=(/Applications/EnergyPlus-*/ /usr/local/EnergyPlus-*/)
    shopt -u nullglob
    if (( ${#ep_candidates[@]} > 0 )); then
        ep_dir=$(printf '%s\n' "${ep_candidates[@]}" | sort -V | tail -n1)
    fi
fi

if [[ -n "$ep_dir" ]]; then
    # Try to get version from the directory name
    ep_version=$(basename "$ep_dir" | sed 's/EnergyPlus-//' | tr '-' '.')
    info+=("EnergyPlus: found at $ep_dir (version $ep_version)")
else
    issues+=("EnergyPlus not found. Simulation tools require a local EnergyPlus installation. Download from https://energyplus.net/downloads — or set the energyplus_dir plugin option.")
fi

# Output results
if [[ ${#info[@]} -gt 0 ]]; then
    for msg in "${info[@]}"; do
        echo "[idfkit] $msg"
    done
fi

if [[ ${#issues[@]} -gt 0 ]]; then
    for msg in "${issues[@]}"; do
        echo "[idfkit] WARNING: $msg"
    done
fi

exit 0
