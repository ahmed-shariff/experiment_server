# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
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

