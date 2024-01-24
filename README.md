# Overview

This is a Python application that allows you to create/maintain/manage study configurations away from your implementations. `experiment-server` has several different interfaces (see below) to allow using it in a range of different scenarios. I've used it with Python, js and [Unity projects](https://github.com/ahmed-shariff/experiment_server/wiki/Using-with-Unity). See the [wiki](https://github.com/ahmed-shariff/experiment_server/wiki) for examples.

# Content

- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
  - [Configuration of an experiment](#configuration-of-an-experiment)
  - [Verify config](#verify-config)
  - [Loading experiment through server](#loading-experiment-through-server)
  - [Loading experiment through API](#loading-experiment-through-api)
  - [Generate expanded config files](#generate-expanded-config-files)
  - [Function calls in config](#function-calls-in-config)
    - [Supported functions](#supported-functions)
    - [Example function calls](#example-function-calls)

# Installation

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
The configuration is defined in a [toml](https://toml.io/en/) file. See example `.toml` below for how the configuration can be defined.

```toml
# The `configuration` table contains the settings of the study/experiment itself
[configuration]
# The `order` is an array of block names or an array of array of block names.
order = [["conditionA", "conditionB", "conditionA", "conditionB"]]
# The `groups` and `within_groups` are optional keys that allows you to define how the
# conditions specified in `order` will be managed. `groups` would dictate how the top 
# level array of `order` will be handled. `within_groups` would dictate how the conditions
# in the nested arrays (if specified) would be managed. These keys can have one 
# of the following values.
# - "latin_square": Apply latin square to balance the values.
# - "randomize": For each participant randomize the order of the values in the array.
# - "as_is": Use the order of the values as specified.
# When not specified, the default value is "as_is" for both keys.
groups = "latin_square"
within_groups= "randomize"
# The random seed to use for any randomization. Default seed is 0. The seed will be
# the value of random_seed + participant_index
random_seed = 0

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
# The value can also be a function call. A function call is represented as a table
# The following function call will be replaced with a call to 
# [random.choices](https://docs.python.org/3/library/random.html#random.choices)
# See `# Function calls` in README for more information.
param2 = { function_name = "choices", args = { population = [1 , 2 , 3 ], k = 2}}
param3 = { function_name = "choices", args = [[1 , 2 , 3 ]], params = { unique = true } }

# Block: Condition B
[[blocks]]
name = "conditionB"
extends = "conditionA"

# Since "conditionB" is extending "conditionA", the keys in the `config` subtable of 
# the block "conditionA" not defined in the `config` subtable of "conditionB" will be copied
# to the `config` subtable of "conditionB". In this example, `param1`, `param2` and 
# `trialsPerItem` will be copied over here.
[blocks.config]
param3 = [2]
```

See [toml spec](https://toml.io/en/v1.0.0) for more information on the format of a toml file.

The above config file, after being processed, would result in the following list of blocks for participant number 1:
```json
[
  {
    "name": "conditionB",
    "extends": "conditionA",
    "config": {
      "param3": [
        2
      ],
      "trialsPerItem": 3,
      "param1": 1,
      "param2": [
        1,
        2
      ],
      "participant_index": 1,
      "name": "conditionB",
      "block_id": 0
    }
  },
  {
    "name": "conditionA",
    "config": {
      "trialsPerItem": 3,
      "param1": 1,
      "param2": [
        2,
        2
      ],
      "param3": [
        3
      ],
      "participant_index": 1,
      "name": "conditionA",
      "block_id": 1
    }
  },
  {
    "name": "conditionA",
    "config": {
      "trialsPerItem": 3,
      "param1": 1,
      "param2": [
        1,
        1
      ],
      "param3": [
        2
      ],
      "participant_index": 1,
      "name": "conditionA",
      "block_id": 2
    }
  },
  {
    "name": "conditionB",
    "extends": "conditionA",
    "config": {
      "param3": [
        2
      ],
      "trialsPerItem": 3,
      "param1": 1,
      "param2": [
        3,
        1
      ],
      "participant_index": 1,
      "name": "conditionB",
      "block_id": 3
    }
  }
]
```

## Verify config
A config file can be validated by running:
```sh
$ experiment-server verify-config-file sample_config.toml
```
This will show how the expanded config looks like for the first 5 participants.

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
- [GET] `/api/config`: Return the `config` subtable in the configuration file of the current block as a JSON object. Note that `move-to-next` has to be called at least once before this can be called.
- [GET] `/api/block-id`: Returns the current block id
- [GET] `/api/status-string`: Returns the status as a string
- [GET] `/api/global-data`: Returns a JSON object, with the following keys: 
  - "participant_index": the participant index
  - "config_length": same value `/items-count`
- [GET] `/api/all-configs`: Return all `config`s of all the blocks as a list, ordered based on the `order` for the configured participant.
- [POST] `/api/move-to-next`: Sets the current block to the next block in the list of blocks. Returns a JSON object, with the key "names", which is the name of the current block after moving. If there are no more blocks, the value of "names" will be "end".
- [POST] `/api/move-to-block/:block_id`: Set the block at index `block_id` in the list of blocks as the current block.
- [POST] `/api/shutdown`: Shutdown the server.
- [POST] `/api/change-participant-index/:participant_index`: Set the participant_index to value `participant_index`. Note that this will set the state back to the initial state as if the server was freshly started.
For a Python application, `experiment_server.Client` can be used to access configs from the server. Also, the server can be launched programmatically using `experiment_server.server_process` which returns a [`Process`](https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Process) object. Note that the server will reload the config and reset the state to the initial state when the config file loaded is modified.

## Loading experiment through API
A configuration can be loaded and managed by importing `experiment_server.Experiment`.

## Generate expanded configs
A config file (i.e. `.toml` file), can be expanded to JSON with the following command

```sh
$ experiment-server generate-config-json sample_config.toml --participant-range 5
```

The above will generate the expanded configs for participant indices 1 to 5 as JSON output on stdout. This result can be written out to individual JSON files by setting the `--out-dir`/`-d` to a directory. See more options with `--help`

## Function calls in config
A function call in the config is represented by a table, with the following keys 
- `function_name`: This should be one of the names in the supported functions list below.
- `args`: The arguments to be passed to the function represented by `function_name`. This can be a list or a table/dict. They should unpack with `*` or `**` respectively when called with the corresponding function.
- (optional) `params`: function-specific configurations to apply with the function calls.
- (optional) `id`: A unique identifier to group function calls.

A table that has keys other than the above keys would not be treated as a function call. Any function calls in different places of the config with the same `id` would be treated as a single group. Tables without an `id` are grouped based on their key-value pairs. Groups are used to identify how some parameters affect the results (e.g., `unique` for `choices`). Function calls can also be in `configurations.variabels`. Note that all function calls are made after the `extends` are resolved and variables from `configurations.variabels` are replaced.

### Supported functions
- `choices`: Calls [random.choices](https://docs.python.org/3/library/random.html#random.choices). `params` can be a table/dictionary which can have the key `unique`. The value of `unique` must be `true` or `false`. By default `unique` is `false`. If it's `true`, within a group of function calls, no value from the population passed to `random.choices` is repeated for a given participant.

### Example function calls
```toml
param = { function_name = "choices", args = [[1 , 2 , 3 , 4]], params = { unique = true } }
```
```toml
param = { foo = "test", bar = { function_name = "choices", args = { population = ["w", "x", "y", "z"], k = 1 } } }
```

For more on the `experiemnt-server` and how it can be used see the [wiki](https://github.com/ahmed-shariff/experiment_server/wiki)

# Wishlist (todo list?)
- Serve multiple participants at the same time.
- Improved docs
  - Add the option of using dict values in order
  - Improve cli help docs
