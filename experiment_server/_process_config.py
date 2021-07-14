from pathlib import Path
from shutil import ExecError
from typing import Any, Callable, Dict, List, Tuple, Union
from experiment_server._participant_ordering import construct_participant_condition, ORDERING_BEHAVIOUR
from experiment_server.utils import ExperimentServerConfigurationExcetion
from loguru import logger
from easydict import EasyDict as edict
import json


TOP_LEVEL_RESERVED_KEYS = ["step_name", "config", "repeat"]
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


def process_config_file(f: Union[str, Path], participant_id: int) -> List[Dict[str, Any]]:
    if participant_id < 1:
        raise ExperimentServerConfigurationExcetion(f"Participant id needs to be greater than 0, got {participant_id}")

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

    # TODO: expand repeat parameter

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
    main_configuration = construct_participant_condition(main_configuration, participant_id, order=order,
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

    for c in config:
        c["config"]["participant_id"] = participant_id
        c["config"]["step_name"] = c["step_name"]
    
    logger.info("Configuration loaded: \n" + "\n".join([f"{idx}: {json.dumps(c, indent=2)}" for idx, c in enumerate(config)]))
    return config


def _replace_template_values(string, template_values):
    for k, v in template_values.items():
        string = string.replace("{" + k + "}", str(v))
    return string


def verify_config(f: Union[str, Path], test_func:Callable[[List[Dict[str, Any]]], Tuple[bool, str]]=None) -> bool:
    import pandas as pd
    from tabulate import tabulate
    with logger.catch(reraise=False, message="Config verification failed"):
        config_steps = {}
        for participant_id in range(1,6):
            config = process_config_file(f, participant_id=participant_id)
            config_steps[participant_id] = {f"trial_{idx + 1}": c["step_name"] for idx, c in enumerate(config)}
            if test_func is not None:
                test_result, reason = test_func(config)
                assert test_result, f"test_func failed for {participant_id} with reason, {reason}"
        df = pd.DataFrame(config_steps)
        df.style.set_properties(**{'text-align': 'left'}).set_table_styles([ dict(selector='th', props=[('text-align', 'left')])])
        logger.info(f"Ordering for 5 participants: \n\n{tabulate(df, headers='keys', tablefmt='fancy_grid')}\n")
        logger.info(f"Config file verification successful for {f}")
        return True
    return False
