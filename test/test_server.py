from unittest.mock import Mock

from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

from experiment_server._api import Experiment
from experiment_server._server import _create_app
from experiment_server._ui import ExperimentTextualApp


class TestShutdownCallback(AsyncHTTPTestCase):
    def get_app(self):
        self.shutdown_requested = Mock()
        experiment = Experiment(
            "test/test_files/working_file.toml",
            default_participant_index=1,
        )
        return _create_app(experiment, on_shutdown=self.shutdown_requested)

    def test_shutdown_acknowledges_request_and_notifies_embedding(self):
        response = self.fetch("/api/shutdown", method="POST", body=b"")

        assert response.code == 200
        assert response.body == b'{"message": "shutting down"}'
        self.shutdown_requested.assert_called_once_with()


class TestExperimentTextualAppShutdown:
    def test_server_shutdown_requests_textual_exit(self):
        app = ExperimentTextualApp()
        app.exit = Mock()

        app._server_shutdown_requested()

        app.exit.assert_called_once_with()
