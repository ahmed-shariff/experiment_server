#!/usr/bin/env python

"""Main script."""

import log
from pathlib import Path

from flask import Flask, request, send_from_directory, send_file
from flask_restful import Resource, Api

import json
from ._calibration import get_calibration_offsets


PARTICIPANT_ID = 1
TRIALS_PER_ITEM = 1

config = [
    {"step_name": "case_direct",
     "config": {"buttonSize": 0.5, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "dir_50", "participantId": PARTICIPANT_ID}},
    {"step_name": "case_indirect",
     "config": {"buttonSize": 0.5, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "indir_50", "participantId": PARTICIPANT_ID}},
    {"step_name": "case_indirect_no_hand",
     "config": {"buttonSize": 0.5, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "indir_noh_50", "participantId": PARTICIPANT_ID}},

    {"step_name": "case_direct",
     "config": {"buttonSize": 1, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "dir_100", "participantId": PARTICIPANT_ID}},
    {"step_name": "case_indirect",
     "config": {"buttonSize": 1, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "indir_100", "participantId": PARTICIPANT_ID}},
    {"step_name": "case_indirect_no_hand",
     "config": {"buttonSize": 1, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "indir_noh_100", "participantId": PARTICIPANT_ID}},

    {"step_name": "case_direct",
     "config": {"buttonSize": 0.75, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "dir_75", "participantId": PARTICIPANT_ID}},
    {"step_name": "case_indirect",
     "config": {"buttonSize": 0.75, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "indir_75", "participantId": PARTICIPANT_ID}},
    {"step_name": "case_indirect_no_hand",
     "config": {"buttonSize": 0.75, "trialsPerItem": TRIALS_PER_ITEM, "conditionId": "indir_noh_75", "participantId": PARTICIPANT_ID}},
]
_init_config = [{"step_name": "configuration",
                 "config": {"participantId": PARTICIPANT_ID}}]
iterator = None
stage = None
initconfig_move = 0

def _init_api(host="127.0.0.1", port="5000", calibration_data_file_path="calibration_data_file.json"):
    global config
    app = Flask("unity-exp-server", static_url_path='')
    api = Api(app)

    config = _init_config + config

    if Path(calibration_data_file_path).exists():
        with open(calibration_data_file_path) as f:
            calibration_data = json.load(f)
    else:
        calibration_data = {}

    class ExperimentConfig(Resource):
        def get(self):
            try:
                config = stage["config"]
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
                return {"step_name": stage["step_name"]}
            except TypeError:
                iterator = iter(config)
                stage = next(iterator)
                return {"step_name": stage["step_name"]}
            except StopIteration:
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
