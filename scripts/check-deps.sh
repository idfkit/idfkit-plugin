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

# 2. Check idfkit-mcp availability (don't actually install, just check)
if command -v uvx &>/dev/null; then
    if uvx --help &>/dev/null 2>&1; then
        info+=("idfkit-mcp: will be available via uvx")
    fi
fi

# 3. Look for EnergyPlus installation
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

# Auto-detect on macOS
if [[ -z "$ep_dir" ]]; then
    for d in /Applications/EnergyPlus-*/; do
        if [[ -d "$d" ]]; then
            ep_dir="$d"
        fi
    done
fi

# Auto-detect on Linux
if [[ -z "$ep_dir" ]]; then
    for d in /usr/local/EnergyPlus-*/; do
        if [[ -d "$d" ]]; then
            ep_dir="$d"
        fi
    done
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
