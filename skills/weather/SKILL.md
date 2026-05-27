---
name: weather
description: Search for EnergyPlus weather stations and download EPW + DDY files. Use when setting up weather data for a building energy simulation or when the user asks about climate data for a location.
argument-hint: "[location]"
---

# Find and Download Weather Files

Search for weather data near: $ARGUMENTS

## Steps

1. **Search** — Use `search_weather_stations` with the location:
   - For text queries (city names): pass the `query` parameter
   - For coordinate-based: pass `latitude` and `longitude`
   - Optionally filter by `country` (ISO code) or `state` (US state code)
   - **Data vintage** — the default files are typical-year (TMY/IWEC/etc.), the right choice for design
     and code-compliance work. For calibration or measurement & verification (M&V) against metered
     energy, the user instead needs actual-year (AMY) data for the specific year being matched, which
     these stations do not provide — flag this so they source an AMY EPW separately.

2. **Present results** — Show the top matches with:
   - Station name and location (city, state, country)
   - WMO number (unique identifier)
   - Distance from query location (for spatial searches)

3. **Download** — Once the user selects a station (or if there's a clear best match), use `download_weather_file` with the WMO number:
   - Returns paths to both EPW (weather data) and DDY (design day data) files
   - Files are cached locally for reuse

4. **Summary** — Report:
   - Weather file location on disk
   - Key climate characteristics (if available from the station metadata)
   - Remind that the weather file can be used with `run_simulation`
   - **Site:Location** — the model's `Site:Location` (latitude, longitude, elevation, time zone) should
     match the chosen EPW header; a mismatch silently skews solar position and run-period results. If a
     model is loaded, suggest aligning `Site:Location` to the downloaded station's coordinates.
