#!/usr/bin/env bash
# inject-idf-context.sh — Add EnergyPlus context when working with relevant files

# Read tool input from stdin
input=$(cat)

# Extract file_path from the JSON
file_path=$(echo "$input" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//' | sed 's/"$//')

if [[ -z "$file_path" ]]; then
    exit 0
fi

# Get the file extension
ext="${file_path##*.}"
ext_lower=$(echo "$ext" | tr '[:upper:]' '[:lower:]')

case "$ext_lower" in
    idf)
        echo "[idfkit] This is an EnergyPlus Input Data File (.idf). For structured editing, use the idfkit MCP tools (load_model, get_object, update_object, add_object) rather than raw text manipulation. The MCP tools handle reference tracking and validation automatically."
        ;;
    epjson)
        echo "[idfkit] This is an EnergyPlus JSON input file (.epJSON). For structured editing, use the idfkit MCP tools (load_model, get_object, update_object) which handle schema validation and reference integrity."
        ;;
    epw)
        echo "[idfkit] This is an EnergyPlus Weather file (.epw). Use search_weather_stations and download_weather_file MCP tools to find and manage weather data. EPW files should generally not be edited manually."
        ;;
    ddy)
        echo "[idfkit] This is an EnergyPlus Design Day file (.ddy), typically paired with an EPW weather file. Design day data is used for HVAC sizing calculations."
        ;;
esac

exit 0
