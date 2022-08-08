import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def config_file():
    return Path(__file__).parent / "test_files/working_file.expconfig"


@pytest.fixture(scope="session")
def participant_index():
    return 1
