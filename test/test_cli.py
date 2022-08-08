import pytest
from click.testing import CliRunner
import experiment_server
import pytest_mock


@pytest.fixture(scope="function")
def runner():
    return CliRunner()


@pytest.fixture(scope="function")
def cli(mocker):
    mocker.patch("experiment_server._main._main")
    mocker.patch("experiment_server._process_config.verify_config")
    # Before the _main method gets imported need to mock them
    from experiment_server.cli import cli
    return None


def test_run(cli, runner):
    result = runner.invoke(cli, ["run", "file"])
    experiment_server._main._main.assert_called_with(None, '127.0.0.1', '5000', "file")


def test_verify_config(cli, runner):
    result = runner.invoke(cli, ["verify-config-file", "file"])
    experiment_server._process_config.verify_config.assert_called_with("file")
