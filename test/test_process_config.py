import pytest
from pathlib import Path

from experiment_server._process_config import verify_config

@pytest.mark.parametrize(
    "f, expected",[
        (Path(__file__).parent / "test_files/working_file.expconfig", True),
        (Path(__file__).parent / "test_files/working_file_2.expconfig", True),
        (Path(__file__).parent / "test_files/working_file_3.expconfig", True),
        (Path(__file__).parent / "test_files/failing_config.expconfig", False)])
def test_verify_config(f, expected):
    out = verify_config(f)
    assert out == expected
