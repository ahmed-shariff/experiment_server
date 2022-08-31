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
    # Before the _server method gets imported need to mock them
    importlib.reload(experiment_server.cli)


def test_run(runner, mocker):
    mock_function(mocker, "experiment_server._server._server")
    result = runner.invoke(experiment_server.cli.cli, ["run", "file"])
    experiment_server._server._server.assert_called_with(None, '127.0.0.1', '5000', "file")


def test_verify_config(runner, mocker):
    mock_function(mocker, "experiment_server._process_config.verify_config")
    result = runner.invoke(experiment_server.cli.cli, ["verify-config-file", "file"])
    experiment_server._process_config.verify_config.assert_called_with("file")

@pytest.mark.parametrize(
    "params, called_with",[
        (["generate-config-json", "file", "-i", "1"], ["file", [1, ], None]),
        (["generate-config-json", "file", "-i", "1", "-r", "2"], ["file", range(1, 3), None]),
        (["generate-config-json", "file"], None),
        (["generate-config-json", "file", "-i", "1", "-r", "2", "-l" "l"], ["file", range(1, 3), "l"]),
        ])
def test_generate_config_json_1(runner, mocker, params, called_with):
    mock_function(mocker, "experiment_server._api.write_to_file")
    result = runner.invoke(experiment_server.cli.cli, params)
    if called_with is None:
        experiment_server._api.write_to_file.assert_not_called()
    else:
        experiment_server._api.write_to_file.assert_called_with(*called_with)
