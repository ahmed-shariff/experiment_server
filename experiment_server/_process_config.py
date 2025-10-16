from pathlib import Path
import random
from shutil import ExecError
from typing import Any, Callable, Dict, List, Tuple, Union

from tornado.locale import load_translations
from experiment_server._participant_ordering import construct_participant_condition, ORDERING_STRATEGY
from experiment_server.utils import ExperimentServerConfigurationExcetion, ExperimentServerExcetion, merge_dicts
from loguru import logger
from easydict import EasyDict as edict
import json
import toml


TOP_LEVEL_RESERVED_KEYS = ["name", "config", "extends"]
SECTIONS = ["main_configuration", "init_configuration", "final_configuration", "template_values", "order", "settings"]
ALLOWED_SETTINGS = ["randomize_within_groups", "randomize_groups"]


def get_sections(f: Union[str, Path]) -> Dict[str, str]:
    loaded_configurations = {}
    current_blob = None
    current_section = None
    with open(f) as fp:
        for line in fp.readlines():
            stripped_line = line.strip()
            if stripped_line.startswith("//"):
                stripped_line = stripped_line.lstrip("//")
                if stripped_line in SECTIONS:   # Lines starting with // are considered comments
                    if current_blob is not None:
                        loaded_configurations[current_section] = current_blob
                    current_blob = ""
                    current_section = stripped_line
            else:
                try:
                    line = line.rstrip()
                    if len(line) > 0:
                        current_blob += line
                except TypeError:
                    raise ExperimentServerConfigurationExcetion("The file should start with a section header.")
                    
        loaded_configurations[current_section] = current_blob

    logger.info(f"Sections in configuration: {list(loaded_configurations.keys())}")
    return loaded_configurations


def process_config_file(f: Union[str, Path], participant_index: int, supress_message:bool=False) -> List[Dict[str, Any]]:
    if participant_index < 1:
        raise ExperimentServerConfigurationExcetion(f"Participant index needs to be greater than 0, got {participant_index}")

    if Path(f).suffix == ".expconfig":
        return _process_expconfig(f, participant_index, supress_message)
    elif Path(f).suffix == ".toml":
        return _process_toml(f, participant_index, supress_message)
    else:
        raise ExperimentServerExcetion("Invalid file type. Expected `.expconfig` or `.toml`")


def _process_toml(f: Union[str, Path], participant_index:int, supress_message:bool=False) -> List[Dict[str, Any]]:
    loaded_configuration = toml.load(f)

    configurations = loaded_configuration.get("configuration", {})
    variables = configurations.get("variables", {})

    configurations_groups = configurations.get("groups", ORDERING_STRATEGY.as_is)
    configurations_within_groups = configurations.get("within_groups", ORDERING_STRATEGY.as_is)
    init_blocks_names = configurations.get("init_blocks", [])
    final_blocks_names = configurations.get("final_blocks", [])
    init_blocks_strategy = configurations.get("init_blocks_strategy", None)
    final_blocks_strategy = configurations.get("final_blocks_strategy", None)

    random_seed = configurations.get("random_seed", 0)
    random.seed(random_seed + participant_index)

    all_blocks = _replace_variables(loaded_configuration["blocks"], variables)
    assert isinstance(all_blocks, list)

    order = configurations.get("order", [str(i) for i in list(range(len(all_blocks)))])

    for c in all_blocks:
        c["name"] = str(c["name"])

    blocks = construct_participant_condition(all_blocks, participant_index, order=order,
                                             init_block_names=init_blocks_names,
                                             final_block_names=final_blocks_names,
                                             groups_strategy=configurations_groups,
                                             within_groups_strategy=configurations_within_groups,
                                             init_blocks_strategy=init_blocks_strategy,
                                             final_blocks_strategy=final_blocks_strategy)

    block_names = [c["name"] for c in blocks]

    # Using merge_dicts to ensure the values are references
    resolved_blocks = {c["name"]: c for c in resolve_extends([merge_dicts(b, {}) for b in all_blocks])}

    # Use block names to get resolved blocks in the expected order
    blocks = [resolved_blocks[c] for c in block_names]
    blocks = resolve_function_calls(blocks)

    for (idx, c) in enumerate(blocks):
        c["config"]["participant_index"] = participant_index
        c["config"]["name"] = c["name"]
        c["config"]["block_id"] = idx
    
    if not supress_message:
        logger.info("Configuration loaded: \n" + json.dumps(blocks, indent=2))
    return blocks


def _process_expconfig(f: Union[str, Path], participant_index: int, supress_message:bool=False) -> List[Dict[str, Any]]:
    loaded_configurations = get_sections(f)
    if "template_values" in loaded_configurations:
        template_values = json.loads(loaded_configurations["template_values"])
    else:
        template_values = {}
    
    # config = json.loads(_replace_template_values(loaded_configurations["init_configuration"], template_values))
    if "order" in loaded_configurations:
        order = json.loads(loaded_configurations["order"])
    else:
        order = [list(range(len(loaded_configurations)))]

    if "settings" in loaded_configurations:
        settings = edict(json.loads(loaded_configurations["settings"]))
    else:
        settings = edict()

    settings.groups = settings.get("groups", ORDERING_STRATEGY.as_is)
    settings.within_groups = settings.get("within_groups", ORDERING_STRATEGY.as_is)

    logger.info(f"Settings used: \n {json.dumps(settings, indent=4)}")

    _raw_main_configuration = loaded_configurations["main_configuration"]
    _templated_main_configuration = _replace_template_values(_raw_main_configuration, template_values)
    try:
        main_configuration = json.loads(_templated_main_configuration)
    except Exception as e:
        logger.error("Raw main config: " + _raw_main_configuration)
        logger.error("Main config with template values passed: " + _templated_main_configuration)
        if isinstance(e, json.decoder.JSONDecodeError):
            raise ExperimentServerConfigurationExcetion("JSONDecodeError at position {}: `... {} ...`".format(
                e.pos,
                _templated_main_configuration[max(0, e.pos - 40):min(len(_templated_main_configuration), e.pos + 40)]))
        else:
            raise
    main_configuration = construct_participant_condition(main_configuration, participant_index, order=order,
                                                         init_block_names=[],
                                                         final_block_names=[],
                                                         groups_strategy=settings.groups,
                                                         within_groups_strategy=settings.within_groups)

    if "init_configuration" in loaded_configurations:
        init_configuration = json.loads(_replace_template_values(loaded_configurations["init_configuration"], template_values))
    else:
        init_configuration = []
        
    if "final_configuration" in loaded_configurations:
        final_configuration = json.loads(_replace_template_values(loaded_configurations["final_configuration"], template_values))
    else:
        final_configuration = []

    config = init_configuration + main_configuration + final_configuration
    config = resolve_extends(config)

    try:
        for (idx, c) in enumerate(config):
            c["config"]["participant_index"] = participant_index
            c["config"]["name"] = c["name"]
            c["config"]["block_id"] = idx
    except KeyError:
        raise ExperimentServerConfigurationExcetion("blocks missing keys (config/name)")
    
    if not supress_message:
        logger.info("Configuration loaded: \n" + json.dumps(config, indent=2))
    return config


def _resolve_extends(c, configs, seen_configs):
    """
    Recursively go through all dependents and collect all values. 
    If cyclic dependancy is encountered, it will simply merge all configs along the dependancy path.
    """
    if "extends" not in c or c["extends"] in seen_configs:
        return c, configs, seen_configs

    dict_a = c
    try:
        dict_b = [_c for _c in configs if _c["name"] == c["extends"]][0]
    except IndexError:
        raise ExperimentServerConfigurationExcetion("`{}` is not a valid name. It must be a `name`.".format(c["extends"]))

    dict_b, configs, seen_configs = _resolve_extends(dict_b, configs, seen_configs + [dict_b["name"]])
    configs[dict_a["block_idx"]] = merge_dicts(dict_a, dict_b)
    return configs[dict_a["block_idx"]], configs, seen_configs


def resolve_extends(configs):
    # Adding idx to track the configs
    for idx, c in enumerate(configs):
        c["block_idx"] = idx

    for c in configs:
        configs[c["block_idx"]] = _resolve_extends(c, configs, [c["name"]])[0]

    # Removing idx
    for c in configs:
        del c["block_idx"]

    return configs


def _replace_template_values(string, template_values):
    for k, v in template_values.items():
        string = string.replace("{" + k + "}", json.dumps(v))
    return string


def _replace_variables(config: Union[Dict[str, Any], List[Any]], variabels: Dict[str, Any]) -> Union[Dict[str, Any], List[Any]]:
    resolved_config: Union[Dict, List]
    if isinstance(config, dict):
        resolved_config = {}
        for k, v in config.items():
            if isinstance(v, str) and v.startswith("$"):
                try:
                    resolved_config[k] = variabels[v[1:]]
                except KeyError:
                    raise ExperimentServerConfigurationExcetion(f"The variable `{v}` does not exsist in `configuration.variables`")
            elif isinstance(v, dict):
                resolved_config[k] = _replace_variables(v, variabels)
            else:
                resolved_config[k] = v
    elif isinstance(config, list):
        resolved_config = []
        for v in config:
            if isinstance(v, str) and v.startswith("$"):
                try:
                    resolved_config.append(variabels[v[1:]])
                except KeyError:
                    raise ExperimentServerConfigurationExcetion(f"The variable `{v}` does not exsist in `configuration.variables`")
            elif isinstance(v, dict):
                resolved_config.append(_replace_variables(v, variabels))
            else:
                resolved_config.append(v)
    return resolved_config


def resolve_function_calls(configs: list) -> list:
    """Check all function calls and replace the values with the result of the function calls."""
    function_calls: Dict[Any, Any] = {}
    return [_resolve_function_calls(c, function_calls) for c in configs]


def _resolve_function_calls(config: dict, function_calls: dict):
    """Recursive function to go traverse through tree and resolve functions."""
    resolved_config = {}
    for k, v in config.items():
        if isinstance(v, dict):
            if len(v) in (2, 3, 4) and all([_k in ["function_name", "args", "params", "id"] for _k in v.keys()]):
                resolved_config[k] = _resolve_function(**v, function_calls=function_calls)
            else:
                resolved_config[k] = _resolve_function_calls(v, function_calls)
        else:
            resolved_config[k] = v
    return resolved_config


def _unpack_args(args) -> Tuple[list, dict]:
    """Convert args into list or dict to allow unpacking."""
    largs, kwargs = [], {}
    if isinstance(args, list):
        largs = args
    elif isinstance(args, dict):
        kwargs = args
    else:
        raise ExperimentServerConfigurationExcetion(f"`args` should be a list or a dict. Got {args}")
    return largs, kwargs


def _resolve_function(function_name:str, args: Union[List,Dict], function_calls: dict, params: Any=None, id: Any=None) -> Any:
    """Call the function and return the value."""
    if id is None:
        call_signature = hash(json.dumps({"function_name": function_name, "args": args, "params": params}, sort_keys=True))
    else:
        call_signature = id

    if function_name == "choices":
        try:
            function_call_group = function_calls[call_signature]
        except KeyError:
            function_call_group = function_calls[call_signature] = ChoicesFunction(args, params)
        return function_call_group(args, params)
    else:
        raise ExperimentServerConfigurationExcetion(f"Unknown function {function_name}")


class ChoicesFunction:
    """Wrapper for random.choices function call.
    `args` will be passed to `random.choices`.
    If `params` has `unique` whose value is True, will ensure no duplicate values seen in any of the choices call."""
    def __init__(self, args, params) -> None:
        self.args = args
        self.largs, self.kwargs = _unpack_args(args)
        self.unique = False
        self.params = params
        if params is not None:
            if not isinstance(params, dict):
                raise ExperimentServerConfigurationExcetion(f"`params` for `choices` should be a dict.")
            if len(params) not in (0, 1):
                raise ExperimentServerConfigurationExcetion(f"Function `choices` expected 0 or 1 keys in params, got {len(params)}")
            if len(params) == 1 and "unique" not in params:
                raise ExperimentServerConfigurationExcetion(f"Unexpected key in `params` of `choices`. Allowed keys: [`unique`]")
            if "unique" in params:
                self.unique = params.get("unique")
        self.previous_choices = []

    def __call__(self, args, params) -> Any:
        # Sanity check, making sure nothing changes between calls
        assert self.args == args
        assert params == self.params
        choice = random.choices(*self.largs, **self.kwargs)
        if self.unique:
            # Making sure there are only unique values
            i = 0
            while any([c in self.previous_choices for c in choice]) or len(set(choice)) != len(choice):
                if i > 20:
                    # KLUDGE: Chouldn't find unique values?
                    break
                i += 1
                choice = random.choices(*self.largs, **self.kwargs)

            self.previous_choices.extend(choice)

            # Check if it is possible to get unique values.
            if len(self.previous_choices) != len(set(self.previous_choices)):
                raise ExperimentServerConfigurationExcetion("There are more calls to `choices` than number of elements in `args`")
        return choice


def verify_config(f: Union[str, Path], test_func:Callable[[List[Dict[str, Any]]], Tuple[bool, str]]=None) -> bool:
    import pandas as pd
    from tabulate import tabulate
    with logger.catch(reraise=False, message="Config verification failed"):
        config_blocks = {}
        for participant_index in range(1,6):
            config = process_config_file(f, participant_index=participant_index)
            config_blocks[participant_index] = {f"trial_{idx + 1}": c["name"] for idx, c in enumerate(config)}
            if test_func is not None:
                test_result, reason = test_func(config)
                assert test_result, f"test_func failed for {participant_index} with reason, {reason}"
        df = pd.DataFrame(config_blocks)
        df.style.set_properties(**{'text-align': 'left'}).set_table_styles([ dict(selector='th', props=[('text-align', 'left')])])
        logger.info(f"Ordering for 5 participants: \n\n{tabulate(df, headers='keys', tablefmt='fancy_grid')}\n")
        logger.info(f"Config file verification successful for {f}")
        return True
    return False
