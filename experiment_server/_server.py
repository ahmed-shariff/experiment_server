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
        (r"/()",StaticFileHandler, {'path': str(static_location / "index.html")}),
        (r"/index()",StaticFileHandler, {'path': str(static_location / "index.html")}),
        (r"/web/([^/]+)", WebHandler, resource_parameters),
        (r"/web/([^/]+)/([0-9]+)", WebHandler, resource_parameters),
        (r"/api/([^/]+)", ExperimentHandler, resource_parameters),
        (r"/api/([^/]+)/([0-9]+)", ExperimentHandler, resource_parameters),
        (r"/api/([^/]+)/([0-9]+)/([0-9]+)", ExperimentHandler, resource_parameters),
        (r"/(.*)",StaticFileHandler, {'path': static_location, 'default_filename': "index.html"})
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


class WebHandler(RequestHandler):
    def initialize(self, experiment:Experiment):
        self.experiment = experiment
        self.output_written: bool = False

    def write_to_output(self, message):
        self.write(f"<div hx-swap-oob=\"innerHTML:#output\">{message}</div>")

    def write_alert(self, alert_type, message):
        self.write_to_output(f"<div class=\"alert alert-{alert_type}\">{message}</div>")

    def write_info(self, message):
        self.write_alert("info", message)

    def write_warn(self, message):
        self.write_alert("warning", message)

    def write_danger(self, message):
        self.write_alert("danger", message)

    def write_empty_status(self):
        self.write_status_string(None, True)

    def write_status_string(self, participant_id=None, no_message=False):
        if not no_message:
            message = self.experiment.get_participant_state(participant_id).status_string().replace("\n", "&nbsp;&nbsp;&nbsp;")
        else:
            message = ""
        self.write(f"<div hx-swap-oob=\"innerHTML:#status\">{message}</div>")

    # NOTE: I am abusing the GET here!
    def get(self, action=None):
        if action in ["status-string", "acive-participant-change", "config", "reset-config", "move-to-block", "move-to-next"]:
            participant_id = self.get_argument("txtPPID", self.experiment.default_participant_index, True)
            use_default = self.get_argument("checkUseDefult", "off", True)

            if use_default == "on":
                participant_id = None
            else:
                try:
                    participant_id = int(participant_id)
                except ValueError:
                    participant_id = self.experiment.default_participant_index

            if participant_id is not None and participant_id not in self.experiment.global_state:
                self.write_danger(f"Participant with ID {participant_id} not known. Consider initializing new participant.")
                self.write_empty_status()
                return

            if action == "status-string":
                self.write_status_string(participant_id)

            elif action == "acive-participant-change":
                self.write_status_string(participant_id)
                self.write_to_output("")

            elif action == "config":
                config = self.experiment.get_config(participant_id)
                if config is not None:
                    table_output = "<table class=\"table\"><tr><th>key</th><th>value</th></tr>"
                    for k,v in config.items():
                        table_output += f"<tr><td>{k}</td><td>{v}</td></tr>"
                    table_output += "</table>"
                    self.write_info(table_output)
                else:
                    self.write_warn(f"participant {participant_id} not active. A call to `/move-to-next` must be made before calling `/config`")

            elif action == "reset-config":
                self.experiment.reset_config(participant_id)
                _str = f"index {participant_id}" if participant_id is not None else "default index"
                self.write_info(f"Reset config for participant with {_str}")

            elif action == "move-to-block":
                new_block_id = self.get_argument("txtBlockID", "-", True)
                try:
                    new_block_id = int(new_block_id)
                except ValueError:
                    self.write_danger("Invaid input")
                    return

                try:
                    new_block_name = self.experiment.move_to_block(new_block_id, participant_id)
                    self.write_info(f"Moved to block: {new_block_name}")
                except Exception as e:
                    self.write_danger(e)
                self.write_status_string(participant_id)

            elif action == "move-to-next":
                try:
                    new_block_name = self.experiment.move_to_next(participant_id)
                    self.write_info(f"Moved to block: {new_block_name}")
                except Exception as e:
                    self.write_danger(e)
                self.write_status_string(participant_id)

        elif action == "move-all-to-block":
            new_block_id = self.get_argument("txtAllBlockID", "-", True)
            try:
                new_block_id = int(new_block_id)
            except ValueError:
                self.write_danger("Invaid input")
                return

            try:
                new_block_name = self.experiment.move_all_to_block(new_block_id)
                self.write_info(f"Moved all to block: {new_block_name}")
            except Exception as e:
                self.write_danger(e)

        elif action == "new-participant":
            self.write_info("New participant id added: " + str(self.experiment.get_next_participant()))

        elif action == "add-participant":
            new_participant_id = self.get_argument("newPPID", "-", True)
            try:
                new_participant_id = int(new_participant_id)
            except ValueError:
                self.write_danger("Invaid input")
                return

            added_participant = self.experiment.add_participant_index(new_participant_id)
            if not added_participant:
                self.write_warn(f"Participant id {new_participant_id} already exists.")
            else:
                self.write_info(f"Added new participant with id: {new_participant_id}")

        elif action == "list-participants":
            table_output = "<table class=\"table\"><tr><th>participant ID</th><th>Block ID</th><th>Block Name</th></tr>"
            for idx, state in self.experiment.global_state.items():
                table_output += f"<tr><td>{idx}</td><td>{state.block_id}</td><td>{state.block_name}</td></tr>"
            table_output += "</table>"
            self.write_info(table_output)

    def post(self, action=None):
        pass


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
