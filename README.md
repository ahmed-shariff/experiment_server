# Overview

Server for experiments to get configurations from

# Setup

## Requirements

* Python 3.8+

## Installation

Install it directly into an activated virtual environment:

```text
$ pip install experiment-server
```

or add it to your [Poetry](https://poetry.eustace.io/) project:

```text
$ poetry add experiment-server
```

# Usage
## Configuration of an experiment
The configuration id defined in a [toml](https://toml.io/en/) file. See example `.toml` below for how the configuration can be defined.
```toml
# The `configuration` table contains settings of the study/experiment itself
[configuration]
# The `order` is an array of block names or an array of array of block names.
order = [["conditionA", "conditionB", "conditionA", "conditionB"]]
# The `groups` and `within_groups` keys allows you to define how the conditions specified
# in `order` will be managed. `groups` would dictate how the top level array of `order`
# will be handled. `within_groups` would dictate how the conditions in the nested arrays
# (if specified) would be managed. These keys can have one of the following values.
# - "latin_square": Apply latin square to balance the values.
# - "randomize": For each participant randomize the order of the values in the array.
# - "as_is": Use the order of the values as specified.
groups = "latin_square"
within_groups= "randomize"

# The subtable `variabels` are values that can be used anywhere when defining the blocks.
# Any variable can be used by appending "$" before the variable name in the blocks. See 
# below for an exmaple of how variables can be used
[configuration.variables]
TRIALS_PER_ITEM = 3

# Blocks are defined as an array of tables. Each block must contain `name` and the 
# subtable `config`. Optionally, a block can also specify `extends`, whish is a `name` of
# another block. See below for more explanation on how `extends` works

# Block: Condition A
[[blocks]]
name = "conditionA"

# The `config` subtable can have any key-values. Note that `name` and `participant_index`
# will be added to the `config` when this file is being processed. Hence, those keys 
# will be overwritten if used in this subtable.
[blocks.config]
trialsPerItem = "$TRIALS_PER_ITEM"
param1 = 1
param2 = 1
param3 = 1

# Block: Condition B
[[blocks]]
name = "conditionB"
extends = "conditionA"

# Since "conditionB" is extending "conditionA", the keys in the `config` subtable of 
# the block "conditionA" not defined in the `config` subtable of "conditionB" will be copied
# to the `config` subtable of "conditionB". In this example, `param1`, `param2` and 
# `trialsPerItem` will be copied over here.
[blocks.config]
param3 = 2
```

See [toml spec](https://toml.io/en/v1.0.0) for more information on the format of a toml file.

The above config file, after being processed, would result in the following list of blocks for participant number 1:
```json
[
  {
    "name": "conditionB",
    "extends": "conditionA",
    "config": {
      "param3": 2,
      "trialsPerItem": 3,
      "param1": 1,
      "param2": 1,
      "participant_index": 1,
      "name": "conditionB"
    }
  },
  {
    "name": "conditionB",
    "extends": "conditionA",
    "config": {
      "param3": 2,
      "trialsPerItem": 3,
      "param1": 1,
      "param2": 1,
      "participant_index": 1,
      "name": "conditionB"
    }
  },
  {
    "name": "conditionA",
    "config": {
      "trialsPerItem": 3,
      "param1": 1,
      "param2": 1,
      "param3": 1,
      "participant_index": 1,
      "name": "conditionA"
    }
  },
  {
    "name": "conditionA",
    "config": {
      "trialsPerItem": 3,
      "param1": 1,
      "param2": 1,
      "param3": 1,
      "participant_index": 1,
      "name": "conditionA"
    }
  }
]
```

## Verify config
A config file can be validated by running:
```sh
$ experiment-server verify-config-file sample_config.toml
```
This will show how the expanded config looks like for the first 5 participant.

## Loading experiment through server
After installation, the server can used as:

```sh
$ experiment-server run sample_config.toml
```

See more options with `--help`

A simple web interface can be accessed at `/` or `/index`

The server exposes the following REST API:
- [GET] `/api/items-count`: The total number of blocks. Returns an integer
- [GET] `/api/active`: Test if the server is working. Returns boolean
- [GET] `/api/config`: Return the `config` subtable in the configuration file of the current block as a json object. Note that `move-to-next` has to be called atleast once before this can be called.
- [GET] `/api/global-data`: Returns a json object, with the following keys: 
  - "participant_index": the participant index
  - "config_length": same value `/items-count`
- [GET] `/api/all-configs`: Return all `config`s of all the blocks as a list, ordered based on the `order` for the configured participant.
- [POST] `/api/move-to-next`: Sets the current block to the next block in the list of blocks. Returns a json object, with the key "names", which is the name of the current block after moving. If there are no more blocks, the value of "names" will be "end".
- [POST] `/api/move-to-block/:block_id`: Set the block at index `block_id` in the list of blocks as the current block.
- [POST] `/api/shutdown`: Shutdown the server.
- [POST] `/api/change-participant-index/:participant_index`: Set the participant_index to value `participant_index`. Note that this will set the sate back to the initial state as if the server was freshly stared.

For a python application, `experiment_server.Client` can be used to access configs from the server. Also, the server can be launched programatically using `experiment_server.server_process` which returns a [`Process`](https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Process) object. Note that the server will reload the config and reset the state to the initial state when the config file loaded is modified.

## Loading experiment through API
A configuration can be loaded and managed by importing `experiment_server.Experiment`.

## Generate expanded config files
A config file (i.e. `.toml` file), can be expanded to json files with the following command

```sh
$ experiment-server generate-config-json sample_config.toml --participant-range 5
```

The above will generate the expanded configs for participant indices 1 to 5 as json files. See more options with `--help`

# Wishlist (todo list?)
- Serve multiple participants at the same time.
- Improved docs
  - Add the option of using dict values in order
  - Improve cli help docs
