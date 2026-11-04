---
name: building-energy-sci-review-extension
description: "sci-review extension: building energy. Adds a building physicist perspective, a building-energy reference document and idfkit model checks to a sci-review panel. Consumed by sci-review only; not for direct use."
---

# Building-energy extension for sci-review

This skill is consumed by `sci-review`. It declares, in `extension.json`, the following contributions to a scientific review panel, together with the files and imports to which they apply:

1. A *building physicist* perspective (`perspective.md`), covering heat-transfer and psychrometric relations, zone and system energy balances, IP and SI conversions, and simulation time conventions.
2. One reference document in the dimension-document form (`reference/building-energy.md`).
3. Domain checks (`checks.md`): idfkit's `validate_model` and `check_model_integrity` on each in-scope IDF or epJSON file, whose failures enter the debate as candidate findings. The checks never modify a model file and never run a simulation.

The extension applies to Python and TypeScript code that imports idfkit, to EnergyPlus model files (IDF and epJSON), to weather files (EPW) and to EnergyPlus outputs (`eplusout*`).

A model that loads this skill directly must not perform a review from it. Run the `sci-review` skill instead; `sci-review` discovers this extension, decides whether it applies to the code under review, and adds the building physicist to the panel when it does.
