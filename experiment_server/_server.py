#!/usr/bin/env python
"""Main script."""

from loguru import logger
from pathlib import Path
from multiprocessing import Process

from tornado.web import RequestHandler, Application, StaticFileHandler
import tornado.ioloop
import asyncio
import json

from experiment_server._api import Experiment
from experiment_server.utils import ExperimentServerConfigurationExcetion, ExperimentServerExcetion


def _create_app(default_participant_index, config_file):
    resource_parameters = {"experiment": Experiment(config_file, default_participant_index)}

    static_location = (Path(__file__).parent  / "static" ).absolute()
    
    application = Application([
        (r"/()",StaticFileHandler, {'path': str(static_location / "initconfig.html")}),
        (r"/index()",StaticFileHandler, {'path': str(static_location / "initconfig.html")}),
        (r"/api/([^/]+)", ExperimentHandler, resource_parameters),
        (r"/api/([^/]+)/([0-9]+)", ExperimentHandler, resource_parameters),
        (r"/api/([^/]+)/([0-9]+)/([0-9]+)", ExperimentHandler, resource_parameters),
        (r"/(.*)",StaticFileHandler, {'path': static_location, 'default_filename': "initconfig.html"})
    ])
    return application


async def _init_api(config_file, default_participant_index, host="127.0.0.1", port=5000):
    application = _create_app(default_participant_index, config_file)
    application.listen(port=port, address=host)
    await asyncio.Event().wait()


def _server(config_file, default_participant_index, host="127.0.0.1", port=5000):
    asyncio.run(_init_api(config_file, default_participant_index, host, port))


def server_process(config_file, default_participant_index=None, host="127.0.0.1", port="5000"):
    p = Process(target=_server,
                kwargs={
                    "default_participant_index":default_participant_index,
                    "host":host, "port":port, "config_file":config_file
                })
    return p


class ExperimentHandler(RequestHandler):
    def initialize(self, experiment:Experiment):
        self.experiment = experiment

    def get(self, action=None, param=None):
        # The experiment methods treat None as default pp
        if param is not None:
            participant_id = self._get_int_from_param(param)
        else:
            participant_id = None

        if participant_id is not None and participant_id not in self.experiment.global_state:
            self.write(f"Participant with ID {participant_id} not known. Consider initializing new participant.")
            self.set_status(406)
            return

        if action == "blocks-count":
            self.write(json.dumps(self.experiment.get_blocks_count()))
        elif action == "block-id":
            self.write(json.dumps(self.experiment.get_participant_state(participant_id).block_id))
        elif action == "active":
            self.write(json.dumps(self.experiment.get_state(participant_id)))
        elif action == "config":
            config = self.experiment.get_config(participant_id)
            if config is not None:
                logger.info(f"Config returned: {config}")
                self.write(json.dumps(config, indent=4))
            else:
                self.set_status(406)
                self.write(f"participant {participant_id} not active. A call to `/move-to-next` must be made before calling `/config`")
        elif action == "summary-data":
            self.write({
                "participant_index": participant_id if participant_id is not None else self.experiment.default_participant_index,
                "configs_length": self.experiment.get_blocks_count(participant_id)
            })
        elif action == "all-configs":
            self.write(json.dumps(self.experiment.get_all_configs(participant_id), indent=4))
        elif action == "status-string":
            self.write(self.experiment.get_participant_state(participant_id).status_string().replace("\n", "&nbsp;&nbsp;&nbsp;"))
        else:
            self.set_status(404)
            self.write("N/A")

    def post(self, action=None, param1=None, param2=None):
        if action == "move-to-next":
            if param2 is not None:
                self.set_status(404)
                self.write(f"unknown second parameter {param2}")
            if param1 is not None:
                participant_id = self._get_int_from_param(param1)
            else:
                participant_id = None

            try:
                block_name = self.experiment.move_to_next(participant_id)
                logger.info(f"Loading block: {self.experiment.get_participant_state(participant_id).block}\n")
                self.write({"name": block_name})
            except KeyError:
                self.write(f"Participant with ID {participant_id} not known. Consider initializing new participant.")
                self.set_status(406)

        elif action == "move-to-block":
            if param1 is None and param2 is None:
                self.set_status(404)
                self.write("Need atleast one paramter.")
                return
            elif param2 is None:
                participant_id = None
                new_block_id = self._get_int_from_param(param1)
            else:
                participant_id = self._get_int_from_param(param1)
                new_block_id = self._get_int_from_param(param2)
            if new_block_id is not None:
                try:
                    if new_block_id >= self.experiment.get_blocks_count(participant_id) or new_block_id < 0:
                        self.set_status(404)
                        self.write("param should be >= 0 and < " + str(self.experiment.get_blocks_count(participant_id)))
                    else:
                        self.experiment.move_to_block(new_block_id, participant_id)
                        self.write(str(new_block_id))
                except KeyError:
                    self.write(f"Participant with ID {participant_id} not known. Consider initializing new participant.")
                    self.set_status(406)
        elif action == "move-all-to-block":
            if param2 is not None:
                self.set_status(404)
                self.write(f"unknown second parameter {param2}")
                return
            new_block_id = self._get_int_from_param(param1)
            if new_block_id is not None:
                if new_block_id >= self.experiment.get_blocks_count() or new_block_id < 0:
                    self.set_status(404)
                    self.write("param should be >= 0 and < " + str(self.experiment.get_blocks_count()))
                else:
                    self.experiment.move_all_to_block(new_block_id)
                    self.write(str(new_block_id))
        elif action == "shutdown":
            self.experiment.watchdog.end_watch()
            shutdown_server()
        else:
            self.set_status(404)
            self.write("n/a")

    def put(self, action=None, param=None):
        if action == "new-participant":
            if param != None:
                self.set_status(406)
                self.write("`new-participant` doesn't take params")
            else:
                self.write(str(self.experiment.get_next_participant()))
        elif action == "add-participant":
            participant_id = self._get_int_from_param(param)
            if participant_id is not None:
                try:
                    added_participant = self.experiment.add_participant_index(participant_id)
                    if not added_participant:
                        self.set_status(406)
                    self.write(json.dumps(added_participant))
                except ExperimentServerConfigurationExcetion as e:
                    self.set_status(406)
                    self.write(e.args[0][0])

    def _get_int_from_param(self, param):
        try:
            param = int(param)
            return param
        except ValueError:
            self.set_status(404)
            self.write(f"param should be an integer, got {param}, processing as None")
            return None


# # From: https://stackoverflow.com/questions/15562446/how-to-stop-flask-application-without-using-ctrl-c
# def shutdown_server():
#     func = request.environ.get('werkzeug.server.shutdown')
#     if func is None:
#         raise RuntimeError('Not running with the Werkzeug Server')
#     func()


# from https://stackoverflow.com/questions/5375220/how-do-i-stop-tornado-web-server    
def shutdown_server():
    tornado.ioloop.IOLoop.instance().stop()
