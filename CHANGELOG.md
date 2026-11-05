# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- The building-energy fixture in `tests/fixtures/sci-review/` lists the two defects of `calibration_error` in `src/bem/units.py` that it previously omitted: `zip` pairs simulated and billed months by position and silently truncates a shorter bill series, and the relative error divides by a month billed at zero. A panel that reports them is now credited with detections rather than charged with false positives.

## [0.3.0] - 2026-11-04

### Added

- The `building-energy-sci-review-extension` skill, an extension for the `sci-review` plugin. It adds a building physicist perspective to a scientific code review, covering heat-transfer and psychrometric relations, energy balances, IP and SI conversions and simulation time conventions, and runs `validate_model` and `check_model_integrity` on the IDF and epJSON files under review, without running a simulation or modifying a model. A seeded fixture for it is in `tests/fixtures/sci-review/`.

## [0.2.0] - 2026-11-02

First tagged release. Version 0.1.0 was never tagged, and its number covered every change listed here, so existing installations did not receive them as updates.

### Added

- Skills for simulation, validation, new models, loading models, energy audits, weather, version upgrades, IDF conventions and documentation lookup.
- The `developing-with-idfkit` skill, which discovers the reference documentation bundled with the installed idfkit package.
- The `energy-modeler`, `envelope-analyst` and `hvac-designer` agents, the `/quick-sim` command and context hooks for model and weather files.
- Plugin manifests for Claude Code and Codex.
- Workflows that adopt idfkit and EnergyPlus releases as pull requests, and a consumer register check in CI.

### Changed

- The plugin delivers `idfkit-mcp` 0.11.1 and `idfkit-lsp` 0.4.0, each pinned exactly. Both run on idfkit 1.1.1.
- The skills state EnergyPlus 26.2.0 as the latest supported version.

### Removed

- The `--prerelease=allow` flag in `.lsp.json`, because `idfkit-lsp` now depends on a stable idfkit.

[Unreleased]: https://github.com/idfkit/idfkit-plugin/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/idfkit/idfkit-plugin/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/idfkit/idfkit-plugin/releases/tag/v0.2.0
