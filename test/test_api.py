import json
from experiment_server.utils import ExperimentServerExcetion
import pytest
import importlib
import pytest_mock
from deepdiff import DeepDiff
import experiment_server._api
from experiment_server._process_config import process_config_file
from .fixtures import config_file, participant_index
from pathlib import Path


class TestParticipantState:
    @pytest.fixture()
    def state(self, config_file, participant_index, mocker):
        # process_config_file = mocker.patch("experiment_server._api.process_config_file", return_value=[f"a{i}" for i in range(10)])
        return experiment_server._api.ParticipantState(process_config_file(config_file, participant_index), participant_index, False)

    @pytest.fixture(scope="class")
    def exp_config(self, config_file, participant_index):
        return process_config_file(config_file, participant_index)

    def test_init(self, state, exp_config, participant_index):
        assert state.config == exp_config
        assert state.participant_index == participant_index
        assert state._block_id == -1
        assert state.active == False

    def test_moveToNextBlock0(self, state):
        state.move_to_next_block()
        assert state._block_id == 0
        assert state.active == True

    def test_blockBlock(self, state):
        state.block_id = 7
        assert state._block_id == 7
        assert state.block["config"]["block_id"] == 7

    def test_moveToNextBlock(self, state):
        state.block_id = 1
        state.move_to_next_block()
        assert state._block_id == 2

    def test_activeOnEnd(self, state):
        state.block_id = 9
        assert state.active == True
        state.move_to_next_block()
        assert state._block_id == 10
        assert state.active == False


class TestExperiment:
    @pytest.fixture(scope="class")
    def experiment(self, config_file, participant_index):
        return experiment_server._api.Experiment(config_file, participant_index)

    @pytest.fixture(scope="class")
    def exp_config(self, config_file, participant_index):
        return process_config_file(config_file, participant_index)

    def test_block_0_config(self, experiment):
        config = experiment.get_config()
        assert config is None

    def test_block_through_all(self, experiment, exp_config):
        for c in exp_config:
            ret = experiment.move_to_next()
            assert ret == c["name"], c["name"]
            ret = experiment.get_config()
            assert ret["name"] == c["name"], c["name"]

    def test_reset_participant(self, experiment):
        _ = experiment.move_to_block(0)
        experiment.global_state[experiment.default_participant_index].config[0]["config"]["foo"] = "bar"
        output = experiment.get_config()
        assert "foo" in output
        experiment.reset_participant()
        output = experiment.get_config()
        assert "foo" not in output

    def test_get_total_block_count(self, experiment, exp_config):
        ret = experiment.get_blocks_count()
        assert ret == len(exp_config)

    def test_get_all_configs(self, experiment, exp_config):
        ret = experiment.get_all_configs()
        assert len(ret) == len(exp_config)
        for c1, c2 in zip(exp_config, ret):
            assert c1["config"]["name"] == c2["name"]

    def test_move_to_block_correct(self, experiment, exp_config):
        ret = experiment.move_to_block(3)
        assert ret == exp_config[3]["name"]
        ret = experiment.get_config()
        assert ret == exp_config[3]["config"]

    def test_move_to_block_outside_range(self, experiment, exp_config):
        ret = experiment.move_to_block(len(exp_config) + 4)
        assert ret == "END"
        ret = experiment.move_to_block(-1)
        assert ret == "START"

    def test_move_to_block_fail_empty(self, experiment):
        with pytest.raises(AssertionError) as exc_info:
            experiment.move_to_block(None)

    def test_move_to_block_fail_non_number(self, experiment):
        with pytest.raises(AssertionError) as exc_info:
            experiment.move_to_block("ha")

    def test_new_participant(self, experiment):
        val = experiment.get_next_participant()
        assert val == 2

    def test_adding_participant(self, experiment):
        added = experiment.add_participant_index(2)
        assert not added
        added = experiment.add_participant_index(3)
        assert added


def test_generate_config_json(tmp_path, config_file):
    out_file_location = tmp_path / "out1"
    # out_file_location.mkdir()
    configs = [process_config_file(config_file, i) for i in range(1, 5)]
    experiment_server._api._generate_config_json(config_file, range(1, 5), out_file_location)

    for i in range(1, 5):
        file_name = out_file_location / f"{Path(config_file).stem}-participant_{i}.json"
        assert file_name.exists()
        with open(file_name) as f:
            loaded_config = json.load(f)
            for c1, c2 in zip(loaded_config, configs[i - 1]):
                assert c1["name"] == c2["name"]


def test_generate_config_json_with_location_as_non_dir(tmp_path, config_file):
    out_file_location = tmp_path / "out2" / "somefile.json"
    out_file_location.parent.mkdir()
    out_file_location.touch()
    with pytest.raises(ExperimentServerExcetion):
        experiment_server._api._generate_config_json(config_file, range(1, 5), out_file_location)
