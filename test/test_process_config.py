import pytest
from pathlib import Path
import pytest_mock
from deepdiff import DeepDiff
import random

from experiment_server._process_config import verify_config, get_sections, process_config_file, _process_expconfig, _process_toml, resolve_extends, ChoicesFunction, _resolve_function
from experiment_server.utils import ExperimentServerConfigurationExcetion


MAIN_CONFIG_KEYS = ["buttonSize","trialsPerItem","conditionId","relativePosition", "participant_index", "name", "block_id"]


@pytest.mark.parametrize(
    "f, expected",[
        (Path(__file__).parent / "test_files/working_file.toml", True),
        (Path(__file__).parent / "test_files/working_file_6.toml", True),
        (Path(__file__).parent / "test_files/working_file_7.toml", True),
        (Path(__file__).parent / "test_files/working_file_8.toml", True),
        (Path(__file__).parent / "test_files/working_file_9.toml", True),
        (Path(__file__).parent / "test_files/working_file.expconfig", True),
        (Path(__file__).parent / "test_files/working_file_2.expconfig", True),
        (Path(__file__).parent / "test_files/working_file_3.expconfig", True),
        (Path(__file__).parent / "test_files/working_file_4.expconfig", True),
        (Path(__file__).parent / "test_files/working_file_5.expconfig", True),
        (Path(__file__).parent / "test_files/working_file_6.expconfig", True),
        (Path(__file__).parent / "test_files/failing_config.expconfig", False),
        (Path(__file__).parent / "test_files/failing_config_2.expconfig", False)])
def test_verify_config(f, expected):
    out = verify_config(f)
    assert out == expected


def _test_func(config):
    other_config_keys = ["conditionId", "participant_index", "name", "block_id"]
    for c in config:
        if c["name"] in ["rating", "configuration"]:
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
        (Path(__file__).parent / "test_files/working_file.toml", True),
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
        (Path(__file__).parent / "test_files/working_file_6.expconfig", ['main_configuration', 'order']),
        (Path(__file__).parent / "test_files/working_file_4.expconfig", ['main_configuration', 'init_configuration', 'final_configuration', 'template_values', 'order']),
        ])
def test_get_sections(f, expected):
    loaded_configs = get_sections(f)
    loaded_sections = list(loaded_configs.keys())
    assert len(set(loaded_sections).difference(expected)) == 0


@pytest.mark.parametrize(
    "f, pid", [
        (Path(__file__).parent / "test_files/working_file.expconfig", 1),
        (Path(__file__).parent / "test_files/working_file.expconfig", 2),
        (Path(__file__).parent / "test_files/working_file_4.expconfig", 1),
        (Path(__file__).parent / "test_files/working_file_4.expconfig", 2),
        ])
def test_process_expconfig(mocker, f, pid):
    import experiment_server._process_config
    spy_get_sections = mocker.spy(experiment_server._process_config, "get_sections")
    config = _process_expconfig(f, pid)
    spy_get_sections.assert_called_once_with(f)
    assert len(config) == 10
    assert config[0]["name"] == "configuration"
    assert config[-1]["name"] == "rating"

    for c in config:
        assert "config" in c
        assert "name" in c
        assert "name" in c["config"]
        assert "participant_index" in c["config"]
        assert c["config"]["participant_index"] == pid

    for block_id in range(1, 10):
        keys = set(config[block_id]["config"].keys())
        assert len(keys.difference(MAIN_CONFIG_KEYS)) == 0


@pytest.mark.parametrize(
    "f, pid, length, first_name, last_name, config_keys", [
        # (Path(__file__).parent / "test_files/working_file.toml", 1, 8, "configuration", "rating", MAIN_CONFIG_KEYS),
        # (Path(__file__).parent / "test_files/working_file.toml", 2, 8, "configuration", "rating", MAIN_CONFIG_KEYS),
        (Path(__file__).parent / "test_files/working_file_9.toml", 2, 2, "2", "2", ["p1", "p2", "p3", "name", "participant_index", "block_id"]),
        ])
def test_process_toml(f, pid, length, first_name, last_name, config_keys):
    config = _process_toml(f, pid)
    assert len(config) == length
    assert config[0]["name"] == first_name
    assert config[-1]["name"] == last_name

    for c in config:
        assert "config" in c
        assert "name" in c
        assert "name" in c["config"]
        assert "participant_index" in c["config"]
        assert c["config"]["participant_index"] == pid

    for block_id in range(1, length):
        keys = set(config[block_id]["config"].keys())
        assert len(keys.difference(config_keys)) == 0


@pytest.mark.parametrize(
    "config, expected", [
        ([{"name": "a", "param1": "2", "param2": "foo"},
          {"name": "b", "param1": "3", "param2": "bar"},
          {"name": "c", "extends": "a", "param2": "baz"}],
         [{"name": "a", "param1": "2", "param2": "foo"},
          {"name": "b", "param1": "3", "param2": "bar"},
          {"name": "c", "extends": "a", "param1": "2", "param2": "baz"}]),
        ([{"name": "a", "extends": "c", "param1": "2", "param2": "foo"},
          {"name": "c", "extends": "a", "param1": "3", "param2": {"x": "bar"}}],
         [{"name": "a", "extends": "c", "param1": "2", "param2": "foo"},
          {"name": "c", "extends": "a", "param1": "3", "param2": {"x": "bar"}}]),
        ([{"name": "a", "extends": "c", "param1": "2", "param3": "foo"},
          {"name": "c", "extends": "a", "param1": "3", "param2": {"x": "bar"}}],
         [{"name": "a", "extends": "c", "param1": "2", "param2": {"x": "bar"}, "param3": "foo"},
          {"name": "c", "extends": "a", "param1": "3", "param2": {"x": "bar"}, "param3": "foo"}]),
        ([{"name": "a", "extends": "b", "param1": "0"},
          {"name": "b", "extends": "c", "param2": "0"},
          {"name": "c", "extends": "a", "param3": "0"}],
         [{"name": "a", "extends": "b", "param1": "0", "param2": "0", "param3": "0"},
          {"name": "b", "extends": "c", "param1": "0", "param2": "0", "param3": "0"},
          {"name": "c", "extends": "a", "param1": "0", "param2": "0", "param3": "0"}],
          )
    ])
def test_resolve_extends(config, expected):
    output = resolve_extends(config)
    assert DeepDiff(output, expected) == {}


@pytest.mark.parametrize(
    "config, expected", [
        ([{"name": "a", "param1": "2", "param2": "foo"},
          {"name": "c", "extends": "b", "param2": "baz"}], "`b` is not a valid name. It must be a `name`.")
    ])
def test_resolve_extends_exceptions(config, expected):
    with pytest.raises(ExperimentServerConfigurationExcetion, match=expected):
        resolve_extends(config)


@pytest.mark.parametrize(
    "f, seed, pid",[
        (Path(__file__).parent / "test_files/working_file.toml", 0, 1),
        (Path(__file__).parent / "test_files/working_file_6.toml", 100, 1),
        (Path(__file__).parent / "test_files/working_file_6.toml", 100, 2),
        ])
def test_random_seed(mocker, f, seed, pid):
    spy_seed = mocker.spy(random, "seed")
    _ = _process_toml(f, pid)
    spy_seed.assert_called_once_with(seed + pid)


@pytest.mark.parametrize(
    "params, expected", [
        ("wrong", "should be a dict."),
        ({"a": 1, "b": 2}, "Function .* expected 0 or 1 keys in params, got [0-9]+"),
        ({"a": 1}, f"Unexpected key in .*. Allowed keys: .*"),
    ])
def test_functions_choices_fail_paramters(params, expected):
    with pytest.raises(ExperimentServerConfigurationExcetion, match=expected):
        ChoicesFunction([1, 2, 3], params=params)


@pytest.mark.parametrize(
    "args, params, test_unique", [
        ([list(range(10))], {"unique": True}, True),
        ({"population": list(range(10)), "k": 2}, {"unique": True}, True),
        ([list(range(10))], {"unique": False}, False),
        ([list(range(10))], None, False),
    ])
def test_functions_choices_pass_calls(args, params, test_unique):
    choices_callable = ChoicesFunction(args, params)
    out = [c for _ in range(5) for c in choices_callable(args, params)]
    if test_unique:
        assert len(set(out)) == len(out)


@pytest.mark.parametrize(
    "args, params, expected", [
        ([list(range(4))], {"unique": True}, "There are more calls to .choices. than number of elements in .args."),
        ({"population": list(range(4)), "k": 2}, {"unique": True}, "There are more calls to .choices. than number of elements in .args."),
    ])
def test_functions_choices_failed_calls(args, params, expected):
    choices_callable = ChoicesFunction(args, params)
    with pytest.raises(ExperimentServerConfigurationExcetion, match=expected):
        [c for _ in range(5) for c in choices_callable(args, params)]


def test__resolve_function_unique_calls():
    callers = [{"function_name": "choices", "args": [list(range(5))]},
               {"function_name": "choices", "args": {"population": list(range(5))}},
               {"function_name": "choices", "args": [list(range(5))], "id": 1}]
    function_calls = {}
    [_resolve_function(**caller, function_calls=function_calls) for caller in callers for i in range(3)]

    assert len(function_calls) == len(callers)
