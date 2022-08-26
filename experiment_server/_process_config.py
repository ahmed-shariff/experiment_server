from pathlib import Path
from shutil import ExecError
from typing import Any, Callable, Dict, List, Tuple, Union

from tornado.locale import load_translations
from experiment_server._participant_ordering import construct_participant_condition, ORDERING_BEHAVIOUR
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


def process_config_file(f: Union[str, Path], participant_index: int) -> List[Dict[str, Any]]:
    if participant_index < 1:
        raise ExperimentServerConfigurationExcetion(f"Participant index needs to be greater than 0, got {participant_index}")

    if Path(f).suffix == ".expconfig":
        return _process_expconfig(f, participant_index)
    elif Path(f).suffix == ".toml":
        return _process_toml(f, participant_index)
    else:
        raise ExperimentServerExcetion("Invalid file type. Expected `.expconfig` or `.toml`")


def _process_toml(f: Union[str, Path], participant_index:int) -> List[Dict[str, Any]]:
    loaded_configuration = toml.load(f)

    configurations = loaded_configuration.get("configuration", {})
    variables = configurations.get("variables", {})
    blocks = _replace_variables(loaded_configuration["blocks"], variables)

    configurations_groups = configurations.get("groups", ORDERING_BEHAVIOUR.as_is)
    configurations_within_groups = configurations.get("within_groups", ORDERING_BEHAVIOUR.as_is)

    order = configurations.get("order", [list(range(len(blocks)))])

    blocks = construct_participant_condition(blocks, participant_index, order=order,
                                             groups=configurations_groups,
                                             within_groups=configurations_within_groups)

    init_blocks = _replace_variables(loaded_configuration.get("init_blocks", []), variables)
    final_blocks = _replace_variables(loaded_configuration.get("final_blocks", []), variables)

    blocks = init_blocks + blocks + final_blocks
    blocks = resolve_extends(blocks)

    for c in blocks:
        c["config"]["participant_index"] = participant_index
        c["config"]["name"] = c["name"]
    
    logger.info("Configuration loaded: \n" + "\n".join([f"{idx}: {json.dumps(c, indent=2)}" for idx, c in enumerate(blocks)]))
    return blocks


def _process_expconfig(f: Union[str, Path], participant_index: int) -> List[Dict[str, Any]]:
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

    settings.groups = settings.get("groups", ORDERING_BEHAVIOUR.as_is)
    settings.within_groups = settings.get("within_groups", ORDERING_BEHAVIOUR.as_is)

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
                                                         groups=settings.groups,
                                                         within_groups=settings.within_groups)

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
        for c in config:
            c["config"]["participant_index"] = participant_index
            c["config"]["name"] = c["name"]
    except KeyError:
        raise ExperimentServerConfigurationExcetion("blocks missing keys (config/name)")
    
    logger.info("Configuration loaded: \n" + "\n".join([f"{idx}: {json.dumps(c, indent=2)}" for idx, c in enumerate(config)]))
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
