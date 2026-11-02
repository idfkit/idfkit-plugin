# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-02

First tagged release. Version 0.1.0 was never tagged, and its number covered every change listed here, so existing installations did not receive them as updates.

### Added

- Skills for simulation, validation, new models, loading models, energy audits, weather, version upgrades, IDF conventions and documentation lookup.
- The `developing-with-idfkit` skill, which discovers the reference documentation bundled with the installed idfkit package.
- The `energy-modeler`, `envelope-analyst` and `hvac-designer` agents, the `/quick-sim` command and context hooks for model and weather files.
- Plugin manifests for Claude Code and Codex.
- The idfkit visual identity in the README, with a CI check at `identity-2026.4`.
- Workflows that adopt idfkit and EnergyPlus releases as pull requests, and a consumer register check in CI.

### Changed

- The plugin delivers `idfkit-mcp` 0.11.1 and `idfkit-lsp` 0.4.0, each pinned exactly. Both run on idfkit 1.1.1.
- The skills state EnergyPlus 26.2.0 as the latest supported version.

### Removed

- The `--prerelease=allow` flag in `.lsp.json`, because `idfkit-lsp` now depends on a stable idfkit.

[Unreleased]: https://github.com/idfkit/idfkit-plugin/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/idfkit/idfkit-plugin/releases/tag/v0.2.0
