# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) over what a user of the plugin
sees: the settings declared in `ida-plugin.json`, the minimum IDA version, and the Python
dependencies the plugin needs in IDA's interpreter. A release that raises any of those says so in
its entry.

Add your entry to `[Unreleased]` when the change merges, while the reasoning is still at hand,
rather than reconstructing it from the commit log at release time.

## [Unreleased]

### Added

- Pushing a `vX.Y.Z` tag now cuts the release. The workflow refuses to continue unless the tag
  matches `ida-plugin.json` and `config.py`, `CHANGELOG.md` has a section for it, the commit is on
  `main` and CI passed there; it then runs the metadata, settings and quality checks, builds
  `mcrit-ida-<version>.zip`, lints the repository and the archive with `hcli`, and creates the
  GitHub release from that version's changelog section with the generated contributor list
  appended and the archive attached. The offline wheelhouse workflow runs from the published
  release as before. Pre-release tags (`v1.2.0rc1`) are marked as such. See `RELEASING.md`.
- A pull request that changes the shipped plugin files has to add a `CHANGELOG.md` entry or carry
  the `no-changelog` label; CI checks it.

### Changed

- The release history moved out of `README.md` into this file; the entries below are unchanged.
  `verify_metadata_sync.py` now reads the latest release heading from here.
- The offline-dependency workflow no longer expands the release tag inside its scripts (a tag
  name is attacker-influenced text in a workflow that runs with write permissions) and no longer
  keeps the checkout's credentials on the runner.
- CI and the release workflow run on Python 3.12, matching the floor the rest of the MCRIT
  ecosystem now shares (`smda`, which the plugin needs in IDA's interpreter, requires 3.12 from
  its next release). IDA 9 bundles 3.12 alongside 3.11; nothing in the plugin needed 3.12.

## [1.1.10] - 2026-09-16

### Fixed

- Function Scope returning no matches for every function after the first, on SMDA 4.8 and later.
  `SmdaReport.getFunctions()` caches its result there, and the plugin reused a single outline
  report across queries while only swapping its `xcfg`, so every query after the first
  re-submitted the first function. A fresh outline is now built per query.
- The outline now follows a replaced local report, so an upload after renaming no longer carries
  the previous report's metadata.

## Older releases

Recorded as they were written in the README at the time, newest first.

### v1.1.9 (2026-08-04)
- Matching reports now load ~7x faster (2.08s -> 0.29s on a 220k-match report), as the bundled minimcrit `MatchingResult.fromDict` no longer deep-copies the match lists for filtering. They are derived lazily as shallow copies on first access instead, mirroring the change in MCRIT 1.5.3.
- Added `MatchingResult.resetFilters()`, so a report can be re-filtered without accumulating previous filters.

### v1.1.8 (2026-07-15)
- Isolated MCRIT4IDA loggers by configuring them with their own handler instead of relying on IDA's shared root logger.
- Stopped bundled minimcrit modules from calling `logging.basicConfig()` at import time.
- Added a regression test for the case where another IDA plugin has already configured the root logger.

### v1.1.7 (2026-05-11)
- Better guarding of remote metadata
- Extensive testing for config parsing and McritClient communication
- Expose sample-group-only matching setting

### v1.1.6 (2026-03-23)
- Updated HCLI-facing plugin metadata for release packaging, including the `1.1.6` version, `IDA 9.0+` minimum, repository URL, and request-timeout setting.
- Added repo-local packaging and validation scripts for metadata sync, settings sync, Ruff checks, and minimal plugin ZIP creation.
- Added validation/release GitHub Actions to lint both the repo and packaged ZIP, publish `mcrit-ida-<version>.zip`, and attach offline dependency bundles to published releases.
- Switched the offline dependency workflow to run from published releases so wheelhouse bundles attach to the canonical release instead of tag pushes alone.
- Expanded the README with first-time HCLI setup, local ZIP installs, headless configuration examples, and manual installation steps without HCLI.

### v1.1.5 (2026-02-27)
- Added configurable MCRIT request timeouts via `mcrit_request_timeout` and aligned numeric setting defaults with the plugin settings metadata.
- Refactored `McritClient` HTTP calls through shared request helpers and added centralized timeout support via `setTimeout()`.
- Moved the initial server connection check off the UI thread and improved startup status reporting.
- Added architecture-aware SMDA backend selection with logging and fallback handling during IDB-to-SMDA conversion.
- Hardened `McritInterface` connection error handling and UI-thread dispatch for background updates.
- Guarded remote metadata lookups and empty/missing response data in `BlockMatchWidget`, `FunctionMatchWidget`, and `SampleInfoWidget` to avoid crashes when server state is incomplete.
- Added safety checks before applying labels in `FunctionOverviewWidget` when no label column is configured or no labels have been fetched.
- Fixed job dialog preselection when the selected row index is `0`.
- Removed the custom graph close action from `SmdaGraphViewer` to avoid the `AttributeError` path there.
- Cleaned up vendored `pyperclip` compatibility handling for newer Python versions and removed stray debug/formatting issues from the batch.

### v1.1.4 (2026-01-30)
- added Github action to build dependency packages to facilitate installation in offline environments.
- Removed the mcrit package dependency by internalizing McritClient and required DTOs.
- Restored plugin hotkey handler and added a close action to the graph context menu.
- Improved resilience for missing or empty match data and guarded SMDA import paths.
- Hardened UI flows around function labels and form handling.
- Dev/CI: Added Ruff config + GitHub Action and reformatted the codebase.

### v1.1.3 (2026-01-28)
- Significantly improved usablity of FunctionOverviewWidget by being able to deconflict multiple candidate labels.

### v1.1.2 (2026-01-19)
- Optionally use SMDA as backend analysis engine (consistency towards MCRIT server), even when in IDA Pro.

### v1.1.1 (2026-01-15)
- Now coloring results in BlockMatch (by frequency) and FunctionMatch (by score) widgets
- Can now display offsets of matched functions in FunctionMatchWidget

### v1.1.0 (2025-12-30)
- Full HCLI Plugin Manager support.
- Migrated configuration to `ida-settings`.
- Code quality improvements.
- Strict HCLI compliance.

### v1.0.0 (2025-12-22)
- Initial standalone release.
- IDA 9.2 (PySide6) compatibility.

[Unreleased]: https://github.com/danielplohmann/mcrit-plugin/compare/v1.1.10...HEAD
[1.1.10]: https://github.com/danielplohmann/mcrit-plugin/compare/v1.1.9...v1.1.10
