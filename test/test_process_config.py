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


def _test_func(config):
    main_config_keys = ["buttonSize","trialsPerItem","conditionId","relativePosition", "participant_id", "step_name"]
    other_config_keys = ["conditionId", "participant_id", "step_name"]
    for c in config:
        if c["step_name"] in ["rating", "configuration"]:
            config_keys = other_config_keys
        else:
            config_keys = main_config_keys
        keys = list(c["config"].keys())
        if len(c["config"]) == len(config_keys):
            if not all([k in keys for k in config_keys]):
                return False, "Failed keys: {}".format({k: k in keys for k in config_keys})
        else:
            return False, f"Missing keys. Expected: {config_keys}, got, {keys}"
    return True, ""


@pytest.mark.parametrize(
    "f, expected",[
        (Path(__file__).parent / "test_files/working_file.expconfig", True),
        (Path(__file__).parent / "test_files/working_file_2.expconfig", False),
        (Path(__file__).parent / "test_files/working_file_3.expconfig", False),
        (Path(__file__).parent / "test_files/failing_config.expconfig", False)])
def test_verify_config_with_test_func(f, expected):
    out = verify_config(f, test_func=_test_func)
    assert out == expected

    
