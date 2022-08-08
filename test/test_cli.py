import pytest
import importlib
from click.testing import CliRunner
import experiment_server
import pytest_mock

import experiment_server.cli


@pytest.fixture(scope="function")
def runner():
    return CliRunner()


def mock_function(mocker, mock_function):
    mocker.patch(mock_function)
    # Before the _main method gets imported need to mock them
    importlib.reload(experiment_server.cli)


def test_run(runner, mocker):
    mock_function(mocker, "experiment_server._main._main")
    result = runner.invoke(experiment_server.cli.cli, ["run", "file"])
    experiment_server._main._main.assert_called_with(None, '127.0.0.1', '5000', "file")


def test_verify_config(runner, mocker):
    mock_function(mocker, "experiment_server._process_config.verify_config")
    result = runner.invoke(experiment_server.cli.cli, ["verify-config-file", "file"])
    experiment_server._process_config.verify_config.assert_called_with("file")
