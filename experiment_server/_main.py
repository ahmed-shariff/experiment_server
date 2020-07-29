#!/usr/bin/env python

"""Main script."""

import log
import random
from pathlib import Path

from flask import Flask, request, send_from_directory, send_file
from flask_restful import Resource, Api

import json
from ._calibration import get_calibration_offsets


PARTICIPANT_ID = 0
TRIALS_PER_ITEM = 3

base_config = [
    # {"step_name": "case_direct_hand_for",
    #  "config": {"buttonSize": 0.5, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "dir_50", "participantId": PARTICIPANT_ID}},
    {"step_name": "case_direct_finger_for",
     "config": {"buttonSize": 1, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "dir_100", "participantId": PARTICIPANT_ID}},
    # {"step_name": "case_indirect_hand_for",
    #  "config": {"buttonSize": 0.5, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "dir_50", "participantId": PARTICIPANT_ID}},
    {"step_name": "case_indirect_finger_for",
     "config": {"buttonSize": 1, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "indir_100", "participantId": PARTICIPANT_ID}},

    {"step_name": "case_direct_finger_for",
     "config": {"buttonSize": 0.75, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "dir_75", "participantId": PARTICIPANT_ID}},
    # {"step_name": "case_indirect_hand_for",
    #  "config": {"buttonSize": 0.5, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "dir_50", "participantId": PARTICIPANT_ID}},
    {"step_name": "case_indirect_finger_for",
     "config": {"buttonSize": 0.75, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "indir_75", "participantId": PARTICIPANT_ID}},

    
    # {"step_name": "case_direct",
    #  "config": {"buttonSize": 1, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "dir_100", "participantId": PARTICIPANT_ID}},
    # {"step_name": "case_indirect",
    #  "config": {"buttonSize": 1, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "indir_100", "participantId": PARTICIPANT_ID}},
    # {"step_name": "case_indirect_no_hand",
    #  "config": {"buttonSize": 1, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "indir_noh_100", "participantId": PARTICIPANT_ID}},

    # {"step_name": "case_direct",
    #  "config": {"buttonSize": 0.75, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "dir_75", "participantId": PARTICIPANT_ID}},
    # {"step_name": "case_indirect",
    #  "config": {"buttonSize": 0.75, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "indir_75", "participantId": PARTICIPANT_ID}},
    # {"step_name": "case_indirect_no_hand",
    #  "config": {"buttonSize": 0.75, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "indir_noh_75", "participantId": PARTICIPANT_ID}},
]
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

_init_config = [# {"step_name": "configuration",
                #  "config": {"participantId": PARTICIPANT_ID, "conditionId": "training"}},
    {"step_name": "case_direct_finger_for",
     "config": {"buttonSize": 0.75, "trialsPerItem": 1, "conditionId": "training1", "participantId": PARTICIPANT_ID}},
    {"step_name": "case_indirect_finger_for",
     "config": {"buttonSize": 0.75, "trialsPerItem": 1, "conditionId": "training2", "participantId": PARTICIPANT_ID}},]

_final_config = [{"step_name": "configuration",
                 "config": {"participantId": PARTICIPANT_ID, "conditionId": "final"}}]
iterator = None
stage = None
initconfig_move = 0

def _construct_latin_square(config, participant_id, latin_square):
    if participant_id < 1:
        participant_id = 1
    config = [base_config[i - 1] for i in latin_square[(participant_id - 1) % len(base_config)]]
    return config

def _init_api(host="127.0.0.1", port="5000", calibration_data_file_path="calibration_data_file.json"):
    app = Flask("unity-exp-server", static_url_path='')
    api = Api(app)
    log.i(f"Loading latin_square {PARTICIPANT_ID}: \n{latin_square[(PARTICIPANT_ID - 1) % len(base_config)]}")
    config = _init_config + _construct_latin_square(base_config, PARTICIPANT_ID, latin_square)
    config = base_config

    if Path(calibration_data_file_path).exists():
        with open(calibration_data_file_path) as f:
            calibration_data = json.load(f)
    else:
        calibration_data = {}

    class ExperimentConfig(Resource):
        def get(self):
            try:
                config = stage["config"]
                log.i(f"Config returned (sans calibration): {config}")
                try:
                    config.update(calibration_data[str(PARTICIPANT_ID)])
                except KeyError:
                    config.update({"calibration_offsets": {},
                                   "fix_calibration_offsets": {}})
                return config
            except TypeError:
                return "", 404

    class ExperimentRouter(Resource):
        def get(self):
            global iterator, stage
            try:
                stage = next(iterator)
                log.i(f"Lading step: {stage}")
                return {"step_name": stage["step_name"]}
            except TypeError:
                iterator = iter(config)
                stage = next(iterator)
                log.i(f"Lading step: {stage}")
                return {"step_name": stage["step_name"]}
            except StopIteration:
                log.i(f"Lading step: MainScene{stage}")
                return {"step_name": "MainScene"}
            # return  {"step_name": "SampleScene"} # {"buttonSize": 0.5, "trialsPerItem": 5}

    class ExperimentInitConfiguration(Resource):
        def get(self):
            global initconfig_move
            message = {"move": initconfig_move}
            initconfig_move = 0
            return message

        def post(self):
            data = request.form["data"]  # .splitlines()
            with open("temp.csv", "w") as f:
                f.write(data)
            calibration_offsets, fix_calibration_offsets = get_calibration_offsets("temp.csv")
            calibration_data[PARTICIPANT_ID] = {"calibrationOffsets": calibration_offsets,   
                                                 "fixCaliberationOffsets": fix_calibration_offsets}
            log.i(f"Caliberarion Data: {calibration_data[PARTICIPANT_ID]}")
            with open(calibration_data_file_path, "w") as f:
                json.dump(calibration_data, f)
            print(calibration_data)
            

    class ExperimentInitConfigurationMove(Resource):
        def get(self, action):
            global initconfig_move
            if action == "index":
                return send_file(Path(__file__).parent  / "static" / "initconfig.html")
            elif action == "move":
                initconfig_move = 1
            elif action == "pause":
                initconfig_move = 2
            elif action == "previous":
                initconfig_move = 3
            else:
                return "", 404
            
    api.add_resource(ExperimentConfig, '/config')
    api.add_resource(ExperimentRouter, '/next')
    api.add_resource(ExperimentInitConfiguration, '/initconfig')
    api.add_resource(ExperimentInitConfigurationMove, '/initconfig/<string:action>')
    app.run(host=host, port=int(port))


def main():
    pass

if __name__ == '__main__':  # pragma: no cover
    main()
