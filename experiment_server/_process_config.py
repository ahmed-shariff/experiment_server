from pathlib import Path
from shutil import ExecError
from typing import Any, Dict, Union
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
            if line.lstrip().startswith("//"):
                if current_blob is not None:
                    loaded_configurations[current_section] = current_blob
                current_blob = ""
                current_section = line.lstrip().rstrip().lstrip("//")
                
                if current_section not in SECTIONS:  # Lines starting with // are considered comments
                    continue
            else:
                try:
                    current_blob += line.rstrip()
                except TypeError:
                    raise ExperimentServerConfigurationExcetion("The file should start with a section header.")
                    
        loaded_configurations[current_section] = current_blob

    logger.info(f"Sections in configuration: {list(loaded_configurations.keys())}")
    return loaded_configurations


def process_config_file(f: Union[str, Path], participant_id: int) -> Dict[str, Any]:
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

    try:
        main_configuration = json.loads(_replace_template_values(loaded_configurations["main_configuration"], template_values))
    except:
        logger.error(loaded_configurations["main_configuration"])
        logger.error(_replace_template_values(loaded_configurations["main_configuration"], template_values))
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


def verify_config(f: Union[str, Path]) -> bool:
    with logger.catch(reraise=False, message="Config verification failed"):
        process_config_file(f, 1)
        logger.info("Config file verification successful")
        return True
    return False
