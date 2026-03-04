# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - Initial release

### Added
- Schema validation with normalization and structured warning/guard flags.
- Config-driven metric scoring via `bioage/constants.yaml` thresholds and weights.
- Composite model producing subsystem scores, total risk, age delta, and biological age estimate.
- Explanation bundle with driver analysis, recommendations, and counterfactual simulations.
- HTML report generation with chart artifacts.
- CLI runner (`python -m bioage`) with reproducible run artifact outputs.
- FastAPI web UI for interactive input and report viewing.
