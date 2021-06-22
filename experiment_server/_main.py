#!/usr/bin/env python
"""Main script."""

from loguru import logger
from pathlib import Path
from multiprocessing import Process

from flask import Flask, request, send_file
from flask_restful import Resource, Api

from experiment_server._process_config import process_config_file


def _create_app(participant_id=None, host="127.0.0.1", port="5000", config_file="static/base_config.expconfig"):
    app = Flask("unity-exp-server", static_url_path='')
    api = Api(app)
    config = process_config_file(config_file, participant_id)

    resource_parameters = {"globalState": GlobalState(config)}

    api.add_resource(ExperimentConfig, '/config', resource_class_kwargs=resource_parameters)
    api.add_resource(ExperimentRouter, '/<string:action>', '/<string:action>/<int:param>', resource_class_kwargs=resource_parameters)
    return app


def _init_api(participant_id=None, host="127.0.0.1", port="5000", config_file="static/base_config.expconfig"):
    if participant_id is None:
        participant_id = int(input("participant id: "))
    app = _create_app(participant_id=participant_id, host=host, port=port, config_file=config_file)
    app.run(host=host, port=int(port))


def server_process(config_file, participant_id=None, host="127.0.0.1", port="5000"):
    p = Process(target=_init_api, kwargs={"participant_id":participant_id, "host":host, "port":port, "config_file":config_file})
    return p


class GlobalState:
    def __init__(self, config):
        self.participant_id = -1
        self._step_id = None
        self.step = None
        self.config = config

    def setStep(self, step_id):
        self._step_id = step_id
        self.step = self.config[step_id]

    def moveToNextStep(self):
        self.setStep(self._step_id + 1)
        

class ExperimentConfig(Resource):
    def __init__(self, globalState):
        self.globalState = globalState

    def get(self):
        try:
            config = self.globalState.step["config"]
            logger.info(f"Config returned: {config}")
            return config
        except TypeError:
            return "", 404


class ExperimentRouter(Resource):
    def __init__(self, globalState):
        self.globalState = globalState

    def get(self, action=None, param=None):
        if action == "itemsCount":
            return len(self.globalState.config)
        elif action == "index":
            return send_file(Path(__file__).parent  / "static" / "initconfig.html")
        elif action == "active":
            return True
        else:
            return "n/a", 404

    def post(self, action=None, param=None):
        if action == "move_to_next":
            try:
                self.globalState.moveToNextStep()
                logger.info(f"Loading step: {self.globalState.step}\n")
                return {"step_name": self.globalState.step["step_name"]}
            except TypeError:
                self.globalState.setStep(0)
                logger.info(f"Loading step: {self.globalState.step}\n")
                return {"step_name": self.globalState.step["step_name"]}
            except IndexError:
                self.globalState.step = {"step_name": "end"}
                logger.info("Loading step: {'step_name': 'end'}\n")
                return {"step_name": "end"}
            # return  {"step_name": "SampleScene"} # {"buttonSize": 0.5, "trialsPerItem": 5}
        elif action == "move":
            if param is None:
                return "Need paramter", 404
            try:
                param = int(param)
                if param >= len(self.globalState.config):
                    return "param should be >= 0 and < " + str(len(self.globalState.config)), 404
                self.globalState.setStep(int(param))
                return int(param)
            except ValueError:
                return f"param should be a integer, got {param}", 404
        elif action == "shutdown":
            shutdown_server()
        else:
            return "n/a", 404


# From: https://stackoverflow.com/questions/15562446/how-to-stop-flask-application-without-using-ctrl-c
def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
