from experiment_server._participant_ordering import _construct_participant_condition
from loguru import logger
import json


def process_config_file(f, participant_id):
    loaded_configurations = {}
    current_blob = None
    current_section = None
    with open(f) as fp:
        for line in fp.readlines():
            if line.startswith("//"):
                if current_blob is not None:
                    loaded_configurations[current_section] = current_blob
                current_blob = ""
                current_section = line.rstrip().lstrip("//")
            else:
                try:
                    current_blob += line.rstrip()
                except TypeError:
                    logger.error("The file should start with a section header.")
                    return None
        loaded_configurations[current_section] = current_blob
    template_values = json.loads(loaded_configurations["template_values"])
    template_values.update({"PARTICIPANT_ID": participant_id})

    # config = json.loads(_replace_template_values(loaded_configurations["init_configuration"], template_values))
    config_categorization = json.loads(loaded_configurations["order"])
    settings = json.loads(loaded_configurations["settings"])
    if "randomize" in settings:
        randomize = settings["randomize"]
    else:
        randomize = True

    if "default_configuration" in loaded_configurations:
        default_configuration = json.loads(_replace_template_values(loaded_configurations["default_configuration"], template_values))
    else:
        default_configuration = None

    try:
        main_configuration = json.loads(_replace_template_values(loaded_configurations["main_configuration"], template_values))
    except:
        logger.error(loaded_configurations["main_configuration"])
        logger.error(_replace_template_values(loaded_configurations["main_configuration"], template_values))
        raise
    main_configuration = _construct_participant_condition(main_configuration, participant_id, config_categorization=config_categorization, default_configuration=default_configuration, randomize=randomize)

    if "init_configuration" in loaded_configurations:
        init_configuration = json.loads(_replace_template_values(loaded_configurations["init_configuration"], template_values))
    else:
        init_configuration = []
        
    if "final_configuration" in loaded_configurations:
        final_configuration = json.loads(_replace_template_values(loaded_configurations["final_configuration"], template_values))
    else:
        final_configuration = []

    config = init_configuration + main_configuration + final_configuration
    
    logger.info("Configuration loaded: \n" + "\n".join([f"{idx}: {json.dumps(c, indent=2)}" for idx, c in enumerate(config)]))
    return config


def _replace_template_values(string, template_values):
    for k, v in template_values.items():
        string = string.replace("{" + k + "}", str(v))
    return string
