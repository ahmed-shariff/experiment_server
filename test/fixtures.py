import pytest
from pathlib import Path
from _pytest.logging import LogCaptureFixture
from loguru import logger


@pytest.fixture
def caplog(caplog: LogCaptureFixture):
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)


@pytest.fixture(scope="session")
def config_file():
    return Path(__file__).parent / "test_files/working_file.toml"


@pytest.fixture(scope="session")
def participant_index():
    return 1
