#!/usr/bin/env python
"""Main script."""

from loguru import logger
from pathlib import Path
from multiprocessing import Process

from tornado.web import RequestHandler, Application, StaticFileHandler
import tornado.ioloop
import asyncio
import json

from experiment_server._api import GlobalState
from experiment_server.utils import ExperimentServerConfigurationExcetion


def _create_app(participant_index=None, config_file="static/base_config.expconfig"):
    if participant_index is None:
        participant_index = int(input("participant id: "))
        
    resource_parameters = {"globalState": GlobalState(config_file, participant_index)}

    static_location = (Path(__file__).parent  / "static" ).absolute()
    
    application = Application([
        (r"/()",StaticFileHandler, {'path': str(static_location / "initconfig.html")}),
        (r"/index()",StaticFileHandler, {'path': str(static_location / "initconfig.html")}),
        (r"/api/([^/]+)", ExperimentHandler, resource_parameters),
        (r"/api/([^/]+)/([0-9]+)", ExperimentHandler, resource_parameters),
        (r"/(.*)",StaticFileHandler, {'path': static_location, 'default_filename': "initconfig.html"})
    ])
    return application


async def _init_api(participant_index=None, host="127.0.0.1", port="5000", config_file="static/base_config.expconfig"):
    application = _create_app(participant_index, config_file)
    application.listen(port=port, address=host)
    await asyncio.Event().wait()


def _server(participant_index=None, host="127.0.0.1", port="5000", config_file="static/base_config.expconfig"):
    asyncio.run(_init_api(participant_index, host, port, config_file))


def server_process(config_file, participant_index=None, host="127.0.0.1", port="5000"):
    p = Process(target=_server, kwargs={"participant_index":participant_index, "host":host, "port":port, "config_file":config_file})
    return p


class ExperimentHandler(RequestHandler):
    def initialize(self, globalState):
        self.globalState = globalState

    def get(self, action=None):
        if action == "blocks-count":
            self.write(json.dumps(len(self.globalState.config)))
        elif action == "active":
            self.write(json.dumps(True))
        elif action == "config":
            try:
                config = self.globalState.block["config"]
                logger.info(f"Config returned: {config}")
                self.write(config)
            except TypeError as e:
                logger.error(e)
                self.set_status(406)
                self.write("A call to `/move-to-next` must be made before calling `/config`")
        elif action == "global-data":
            self.write({
                "participant_index": self.globalState._participant_index,
                "config_length": len(self.globalState.config)
            })
        else:
            self.set_status(404)
            self.write("N/A")

    def post(self, action=None, param=None):
        if action == "move-to-next":
            try:
                self.globalState.move_to_next_block()
                logger.info(f"Loading block: {self.globalState.block}\n")
                self.write({"name": self.globalState.block["name"]})
            except TypeError:
                self.globalState.set_block(0)
                logger.info(f"Loading block: {self.globalState.block}\n")
                self.write({"name": self.globalState.block["name"]})
            except IndexError:
                self.globalState.block = {"name": "end"}
                logger.info("Loading block: {'name': 'end'}\n")
                self.write({"name": "end"})
            # return  {"name": "SampleScene"} # {"buttonSize": 0.5, "trialsPerItem": 5}
        elif action == "move-to-block":
            if param is None:
                self.set_status(404)
                self.write("Need paramter")
            param = self._get_int_from_param(param)
            if param is not None:
                if param >= len(self.globalState.config):
                    self.set_status(404)
                    self.write("param should be >= 0 and < " + str(len(self.globalState.config)))
                else:
                    self.globalState.set_block(int(param))
                    self.write(str(param))
        elif action == "shutdown":
            shutdown_server()
        elif action == "change-participant-index":
            new_participant_index = self._get_int_from_param(param)
            if new_participant_index is not None:
                try:
                    self.globalState.change_participant_index(new_participant_index)
                    self.write(f"Config for new participant (participant_index: {new_participant_index}) loaded.")
                except ExperimentServerConfigurationExcetion as e:
                    self.set_status(406)
                    self.write(e.args[0][0])
        else:
            self.set_status(404)
            self.write("n/a")

    def _get_int_from_param(self, param):
        try:
            param = int(param)
            return param
        except ValueError:
            self.set_status(404)
            self.write(f"param should be an integer, got {param}")
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
