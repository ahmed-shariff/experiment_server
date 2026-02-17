# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.8] - 2026-02-16
### Added
- New compact editor-only TUI App and CLI flag:
  - experiment-server ui --editor-only (-c required) launches a slim Textual editor (no HTTP server) with embedded log pane.
- ConfigEditor component:
  - Extracted from ConfigTab; encapsulates loading, incremental text replacement, edit/save/cancel flow, snippet insertion, save validation flow and ordering preview.
- Snippet insertion UI and snippets:
  - Modal to choose/preview/insert common TOML fragments at cursor, EOF, end of configuration, or configuration.variables.
- Confirmation modal and cancel button:
  - ConfirmationScreen modal used for destructive actions (write/overwrite/move all).
  - Cancel button for config editing to exit without saving.

### Changed
- verify_config API:
  - Now returns (success: bool, reason: Optional[str]) and accepts `raise_on_error` to optionally re-raise exceptions.
  - Call sites updated to unpack result or opt into `raise_on_error`.
- Stricter config validation:
  - process_config now enforces presence/shape of top-level "configuration", "order", and that blocks are lists; requires block "name" and either "config" or "extends".
  - Improved, clearer error messages when config is malformed.
- Exceptions and typing:
  - Renamed/standardized exceptions to ExperimentServerException and ExperimentServerConfigurationException; updated usages and tests.
- CLI / UI behavior:
  - ui command: verify config at TUI startup (unless --editor-only) and exit on invalid config with suggestion to use verify-config-file or editor-only mode.
  - Editor-only mode removes default stderr sink to avoid CLI output.
- UI refactor & UX tweaks:
  - ConfigTab now embeds ConfigEditor; reduced duplication and simplified refresh behavior.
  - Added client-side save validation (temp file + verify_config) and confirmation when saving invalid files; detect unreplaced <REPLACE_*> placeholders.
  - Added message styling class and other CSS tweaks for modal, order table, snippet screens and editor padding.
  - LoadConfig renamed to LoadConfigScreen and related style updates.
  - Move-all action now prompts for confirmation.
- Misc:
  - Fixed suppress_message parameter name in process_config_file and call sites.
  - Minor CSS/layout and wording adjustments.

### Fixed
- Several misspellings/typos in exception names and related imports.
- Tests updated to reflect new exception names and verify_config behaviour.

## [0.3.7] - 2026-02-06

### Added
- Textual-based terminal UI (ui CLI command) for interactive experiment management:
  - Manage participants, view/pretty-print and edit per‑participant configs, generate/verify TOML and participant JSON, live log pane, file browser to load configs, and ability to start the HTTP server from the TUI.
  - CLI options for the TUI: --config-file, --default-participant-index, --host, --port.
  - New UI assets (TCSS and screenshots).

### Changed
- Refactor config processing:
  - Split TOML loading from processing and introduce _process_config(configuration, participant_index, ...) so config processing can be reused without a file.
  - verify_config now uses a lightweight tabulate/list table helper instead of pandas for ordering previews.
- Experiment API and lifecycle:
  - config_file is now a property; setting it reloads participant states and recreates the file watcher.
  - default_participant_index is a validated property that initializes the default participant state.
  - Added observable callbacks: on_file_change_callback and on_config_change_callback.
- Server integration:
  - Expose a start_server_in_current_ioloop helper to run the Tornado HTTP server on the existing asyncio loop (used by the TUI).
- CLI / utilities:
  - new_config_file moved into experiment_server.utils and reused from the CLI.
- Packaging and requirements:
  - Bump minimum Python to >=3.10 and add Textual and tree-sitter related deps required by the TUI.
- Documentation:
  - README updated with TUI details and API docs/ mkdocs plugin options improved.

### Fixed
- Use public watchdog attribute during shutdown and guard against None to avoid shutdown errors.
- Make config reloads more robust: callback exceptions are caught and logged; failures notify callbacks and attempt to restore prior watcher where appropriate.

### Removed
- Remove pandas dependency (ordering preview replaced by tabulate-based output).

## [0.3.6] - 2025-10-17
### Changed
- Update readme and example config to improve readability.
- Update dev dependancies

### Fixed
- github workflow

### Removed
- Removed sample_config.expconfig

## [0.3.5] - 2025-10-17
### Changed
- Ordering strategies are consistantly called strategies througout
  - `groups` and `within_groups` options in a configuration are now called `groups_strategy` and `within_groups_strategy` respectively. The old names are supported till 0.4 release.

### Added
- Adding `init_blocks` and `final_blocks`
  Previously these were undocumented features and represented blocks themselves. Now they are simialr to the `order` configuration.
- Adding `init_blocks_strategy` and `final_blocks_strategy` which support `randomized` as `as_is`
- Adding proper documentation for dict based ordering. init and final blocks also support the dict based orders.

### Removed
- Removed support for expconfig.
- Removed support for index based orders.

## [0.3.4]
### Fixed
- Participant order with dictionary failing
- Both levels of grouping correctly using latin square

## [0.3.3]
### Added
- `run` cli command has an `ask-default-participant-index` option.

### Fixed
- Typos

## [0.3.2]
### Added
- documentation with mkdocs

### Fixed
- CLI new-config-file handle error when directory does not exist.

## [0.3.0] - 2024-03-19
### Added
- Allow editing configs for a given block
  - Methods to allow resetting participant state to allow the above work
- CLI option to generate new config

### Changed
- Allow managing multiple participants
- Generated output can be written to stdout
- Renamed endpoints
- Refactor web ui and related backend
  - js/css sources served locally
  - Config displayed as table
  - Update UI to manage multiple participants
  - Uses htmx & alpine
- Added aliases to commands

## [0.2.6] - 2023-08-28
### Added
- Web ui: Adding refresh button and poll every min

## [0.2.5] - 2023-08-28
### Changed
- Web UI:
  - Using htmx
  - Show status
- Returned json from server is formatted

### Added
- `block-id` and `status-string` to api

## [0.2.4] - 2022-11-15
### Changed
- Fix - GET method crashing when getting second parameter meant for POST methods
- Fix - `extends` not working with names not in `order`
- Fix - (#1) modification watcher failing when reloading config fails
- Fix - `group` ordering not used when flat array is used in `order`

### Added
- Dev tools (debugger and static analyzer)

## [0.2.3] - 2022-10-09
### Changed
- Fix call order in cli

## [0.2.2] - 2022-10-09
### Added
- Allow setting random seed in toml config
- Function calls within configs

### Removed
- Removed `base_config.expconfig` in static folder and references to it.

## [0.2.1] - 2022-08-31
### Added
- Generate json files based on config file from cli
- Get complete config (in server, client and experiment)
- Watchdog to reload config when it's modified

### Changed
- Fix - Allow flat list for order
- Fix - Inconsistent naming
- Refactor - rename `_main` to `_server`
- Refactor - moved `GlobalState` to `_api`

## [0.2] - 2022-08-26
### Added
- `Experiment` class to allow loading and managing script locally.
- toml based configurations.
- `-i/--participant-index` as cli option for `run`

### Changed
- Renaming `step` to `block` and `step_name` to `name`
- Refactor: `GlobalState`'s camel case to snake case
- Fixed same condition being reused causing issues with `resolve_extends` as the reused dicts are references.

## [0.1] - 2022-08-25
### Added
- Change log
- Adding functions to process `extends`.
  - `Utils.merge_dicts`
  - `_process_config.resolve_extends`
  - `_process_config._resolve_extends`
- Adding test cases to cli
- Adding `change_participant_index` to api
- Adding `globalData` to api

### Changed
- ExperimentConfig was refactored into ExperimentRouter
- Fixed issues in stati html page:
  - Call to `/move`: post->get
  - Adding button to get and display config
- Updaing sample_config to reflect uptodate changes.
- Renaming `participant_id` to `participant_index`
- Replace flask with tornado

## [0.1.rc.3] - 2021-07-14
- Started tracking

