import pytest
from pathlib import Path
import pytest_mock

from experiment_server._process_config import verify_config, get_sections, process_config_file


MAIN_CONFIG_KEYS = ["buttonSize","trialsPerItem","conditionId","relativePosition", "participant_id", "step_name"]


@pytest.mark.parametrize(
    "f, expected",[
        (Path(__file__).parent / "test_files/working_file.expconfig", True),
        (Path(__file__).parent / "test_files/working_file_2.expconfig", True),
        (Path(__file__).parent / "test_files/working_file_3.expconfig", True),
        (Path(__file__).parent / "test_files/working_file_4.expconfig", True),
        (Path(__file__).parent / "test_files/working_file_5.expconfig", True),
        (Path(__file__).parent / "test_files/failing_config.expconfig", False),
        (Path(__file__).parent / "test_files/failing_config_2.expconfig", False)])
def test_verify_config(f, expected):
    out = verify_config(f)
    assert out == expected


def _test_func(config):
    other_config_keys = ["conditionId", "participant_id", "step_name"]
    for c in config:
        if c["step_name"] in ["rating", "configuration"]:
            config_keys = other_config_keys
        else:
            config_keys = MAIN_CONFIG_KEYS
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
        (Path(__file__).parent / "test_files/working_file_4.expconfig", True),
        (Path(__file__).parent / "test_files/failing_config.expconfig", False)])
def test_verify_config_with_test_func(f, expected):
    out = verify_config(f, test_func=_test_func)
    assert out == expected


@pytest.mark.parametrize(
    "f, expected",[
        (Path(__file__).parent / "test_files/working_file.expconfig", ['main_configuration', 'init_configuration', 'final_configuration', 'template_values', 'order']),
        (Path(__file__).parent / "test_files/working_file_4.expconfig", ['main_configuration', 'init_configuration', 'final_configuration', 'template_values', 'order']),
        ])
def test_get_sections(f, expected):
    loaded_configs = get_sections(f)
    loaded_sections = list(loaded_configs.keys())
    assert len(set(loaded_sections).difference(expected)) == 0


@pytest.mark.parametrize(
    "f, pid",[
        (Path(__file__).parent / "test_files/working_file.expconfig", 1),
        (Path(__file__).parent / "test_files/working_file.expconfig", 2),
        (Path(__file__).parent / "test_files/working_file_4.expconfig", 1),
        (Path(__file__).parent / "test_files/working_file_4.expconfig", 2),        
        ])
def test_process_config(mocker, f, pid):
    import experiment_server._process_config
    spy_get_sections = mocker.spy(experiment_server._process_config, "get_sections")
    config = process_config_file(f, pid)
    spy_get_sections.assert_called_once_with(f)
    assert len(config) == 10
    assert config[0]["step_name"] == "configuration"
    assert config[-1]["step_name"] == "rating"

    for c in config:
        assert "config" in c
        assert "step_name" in c
        assert "step_name" in c["config"]
        assert "participant_id" in c["config"]
        assert c["config"]["participant_id"] == pid
    
    for step_id in range(1, 10):
        keys = set(config[step_id]["config"].keys())
        assert len(keys.difference(MAIN_CONFIG_KEYS)) == 0
