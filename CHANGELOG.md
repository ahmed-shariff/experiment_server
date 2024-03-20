# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased
### Fixed
- CLI new-config-file handle error when directory does not exist.

## [0.3.0] - 2024-03-19
### Adding
- Allow editing configs for a given block
  - Methods to allow resetting participant state to allow the above work
- CLI option to generate new config

### Changing
- Allow managing multiple participants
- Generated output can be written to stdout
- Renamed endpoints
- Refactor web ui and related backend
  - js/css sources served locally
  - Config displayed as table
  - Update UI to manage multiple participants
  - Uses htmx & alpine
- Adding aliases to commands

## [0.2.6] - 2023-08-28
### Adding
- Web ui: Adding refresh button and poll every min

## [0.2.5] - 2023-08-28
### Changing
- Web UI:
  - Using htmx
  - Show status
- Returned json from server is formatted

### Adding
- `block-id` and `status-string` to api

## [0.2.4] - 2022-11-15
### Changing
- Fix - GET method crashing when getting second parameter meant for POST methods
- Fix - `extends` not working with names not in `order`
- Fix - (#1) modification watcher failing when reloading config fails
- Fix - `group` ordering not used when flat array is used in `order`

### Adding
- Dev tools (debugger and static analyzer)

## [0.2.3] - 2022-10-09
### Changing
- Fix call order in cli

## [0.2.2] - 2022-10-09
### Adding
- Allow setting random seed in toml config
- Function calls within configs

### Removing
- Removed `base_config.expconfig` in static folder and references to it.

## [0.2.1] - 2022-08-31
### Adding
- Generate json files based on config file from cli
- Get complete config (in server, client and experiment)
- Watchdog to reload config when it's modified

### Changed
- Fix - Allow flat list for order
- Fix - Inconsistent naming
- Refactor - rename `_main` to `_server`
- Refactor - moved `GlobalState` to `_api`

## [0.2] - 2022-08-26
### Adding
- `Experiment` class to allow loading and managing script locally.
- toml based configurations.
- `-i/--participant-index` as cli option for `run`

### Changed
- Renaming `step` to `block` and `step_name` to `name`
- Refactor: `GlobalState`'s camel case to snake case
- Fixed same condition being reused causing issues with `resolve_extends` as the reused dicts are references.

## [0.1] - 2022-08-25
### Adding
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

