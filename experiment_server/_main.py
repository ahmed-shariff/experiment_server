#!/usr/bin/env python

"""Main script."""

from loguru import logger
import random
from pathlib import Path

from flask import Flask, request, send_from_directory, send_file
from flask_restful import Resource, Api

import json


PARTICIPANT_ID = 0

# latin_square = [[1, 2, 3, 4, 5, 6, 7, 8, 9],
#                 [2, 3, 1, 5, 6, 4, 8, 9, 7],
#                 [3, 1, 2, 6, 4, 5, 9, 7, 8],
#                 [4, 5, 6, 7, 8, 9, 1, 2, 3],
#                 [5, 6, 4, 8, 9, 7, 2, 3, 1],
#                 [6, 4, 5, 9, 7, 8, 3, 1, 2],
#                 [7, 8, 9, 1, 2, 3, 4, 5, 6],
#                 [8, 9, 7, 2, 3, 1, 5, 6, 4],
#                 [9, 7, 8, 3, 1, 2, 6, 4, 5]]

latin_square = [[1, 2, 3, 4],
                [3, 4, 1, 2],
                [4, 3, 2, 1],
                [2, 1, 4, 3]]

iterator = None
stage = None


def _construct_participant_condition(config, participant_id, use_latin_square=False, latin_square=None, config_categorization=None, default_configuration=None, randomize=True):
    if participant_id < 1:
        participant_id = 1
    if use_latin_square:
        _config = [config[i - 1] for i in latin_square[(participant_id - 1) % len(config)]]
    else:
        assert len(config_categorization) == 2
        if not randomize or participant_id % len(config_categorization) == 0:
            init_condition = config_categorization[0][:]
            other_condition = config_categorization[1][:]
        else:
            init_condition = config_categorization[1][:]
            other_condition = config_categorization[0][:]
        init_condition = [config[i] for i in init_condition]
        other_condition = [config[i] for i in other_condition]
        random.shuffle(init_condition)
        random.shuffle(other_condition)

        if default_configuration is not None:
            default_configuration_config = default_configuration[0]["config"]
            non_default_keys = [k for k in default_configuration_config.keys() if k not in ["conditionId"]]

            init_condition_train = init_condition[0].copy()
            init_condition_train["config"] = init_condition_train["config"].copy()
            init_condition_train["config"]["conditionId"] = "training1"
            for k in non_default_keys:
                init_condition_train["config"][k] = default_configuration_config[k]

            other_condition_train = other_condition[0].copy()
            other_condition_train["config"] = other_condition_train["config"].copy()
            other_condition_train["config"]["conditionId"] = "training2"
            for k in non_default_keys:
                other_condition_train["config"][k] = default_configuration_config[k]

            _config = [init_condition_train] + init_condition + [other_condition_train] + other_condition

        else:
            _config = init_condition + other_condition
        # _config = [config[i] for i in _config_list]
    return _config


def _process_config_file(f, participant_id):
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
    print(*config, sep="\n")
    return config


def _replace_template_values(string, template_values):
    for k, v in template_values.items():
        string = string.replace("{" + k + "}", str(v))
    return string


def _init_api(host="127.0.0.1", port="5000", config_file="static/base_config.expconfig", calibration_data_file_path="calibration_data_file.json"):
    global PARTICIPANT_ID
    PARTICIPANT_ID = int(input("participant id: "))
    app = Flask("unity-exp-server", static_url_path='')
    api = Api(app)
    config = _process_config_file(config_file, PARTICIPANT_ID)
    
    if Path(calibration_data_file_path).exists():
        with open(calibration_data_file_path) as f:
            calibration_data = json.load(f)
    else:
        calibration_data = {}

    class ExperimentConfig(Resource):
        def get(self):
            try:
                config = stage["config"]
                logger.info(f"Config returned (sans calibration): {config}")
                try:
                    config.update(calibration_data[str(PARTICIPANT_ID)])
                except KeyError:
                    config.update({"calibration_offsets": {},
                                   "fix_calibration_offsets": {}})
                return config
            except TypeError:
                return "", 404

    class ExperimentRouter(Resource):
        def get(self, action=None, param=None):
            global iterator, stage
            if action == "next":
                try:
                    iterator += 1
                    stage = config[iterator]
                    logger.info(f"Lading step: {stage}\n")
                    return {"step_name": stage["step_name"]}
                except TypeError:
                    iterator = 0
                    stage = config[iterator]
                    logger.info(f"Lading step: {stage}\n")
                    return {"step_name": stage["step_name"]}
                except IndexError:
                    logger.info(f"Lading step: MainScene{stage}\n")
                    return {"step_name": "MainScene"}
                # return  {"step_name": "SampleScene"} # {"buttonSize": 0.5, "trialsPerItem": 5}
            elif action == "switch":
                if param is None:
                    return "param cannot be None", 404
                if int(param) >= len(config):
                    return "param max is " + len(config), 404
                iterator = int(param)
                stage = config[iterator]
                return stage
            elif action == "itemsCount":
                return len(config)
            elif action == "index":
                return send_file(Path(__file__).parent  / "static" / "initconfig.html")
            else:
                return "n/a", 404

    api.add_resource(ExperimentConfig, '/config')
    api.add_resource(ExperimentRouter, '/<string:action>', '/<string:action>/<int:param>')
    app.run(host=host, port=int(port))


def main():
    pass


if __name__ == '__main__':  # pragma: no cover
    main()
