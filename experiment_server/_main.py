#!/usr/bin/env python
"""Main script."""

from loguru import logger
from pathlib import Path
from multiprocessing import Process

from tornado.web import RequestHandler, Application, StaticFileHandler
import tornado.ioloop
import asyncio
import json

from experiment_server._process_config import process_config_file
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


def _main(participant_index=None, host="127.0.0.1", port="5000", config_file="static/base_config.expconfig"):
    asyncio.run(_init_api(participant_index, host, port, config_file))


def server_process(config_file, participant_index=None, host="127.0.0.1", port="5000"):
    p = Process(target=_main, kwargs={"participant_index":participant_index, "host":host, "port":port, "config_file":config_file})
    return p


class GlobalState:
    def __init__(self, config_file, participant_index):
        self.config_file = config_file
        self.change_participant_index(participant_index)

    def change_participant_index(self, participant_index):
        self._participant_index = participant_index
        self._block_id = None
        self.block = None
        self.config = process_config_file(self.config_file, participant_index)

    def setBlock(self, block_id):
        self._block_id = block_id
        self.block = self.config[block_id]

    def moveToNextBlock(self):
        self.setBlock(self._block_id + 1)

    def get_global_data(self):
        return {
            "participant_index": self._participant_index,
            "config_lenght": len(self.config)
        }


class ExperimentHandler(RequestHandler):
    def initialize(self, globalState):
        self.globalState = globalState

    def get(self, action=None):
        if action == "itemsCount":
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
                self.write("A call to `/move_to_next` must be made before calling `/config`")
        elif action == "globalData":
            self.write(self.globalState.get_global_data())
        else:
            self.set_status(404)
            self.write("N/A")

    def post(self, action=None, param=None):
        if action == "move_to_next":
            try:
                self.globalState.moveToNextBlock()
                logger.info(f"Loading block: {self.globalState.block}\n")
                self.write({"name": self.globalState.block["name"]})
            except TypeError:
                self.globalState.setBlock(0)
                logger.info(f"Loading block: {self.globalState.block}\n")
                self.write({"name": self.globalState.block["name"]})
            except IndexError:
                self.globalState.block = {"name": "end"}
                logger.info("Loading block: {'name': 'end'}\n")
                self.write({"name": "end"})
            # return  {"name": "SampleScene"} # {"buttonSize": 0.5, "trialsPerItem": 5}
        elif action == "move":
            if param is None:
                self.set_status(404)
                self.write("Need paramter")
            param = self._get_int_from_param(param)
            if param is not None:
                if param >= len(self.globalState.config):
                    return "param should be >= 0 and < " + str(len(self.globalState.config)), 404
                self.globalState.setBlock(int(param))
                self.write(str(param))
        elif action == "shutdown":
            shutdown_server()
        elif action == "change_participant_index":
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
