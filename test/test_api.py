import pytest
import importlib
import pytest_mock
import experiment_server._api
from .fixtures import config_file, participant_index


class TestGlobalState:
    @pytest.fixture()
    def state(self, config_file, participant_index, mocker):
        process_config_file = mocker.patch("experiment_server._api.process_config_file", return_value=[f"a{i}" for i in range(10)])
        return experiment_server._api.GlobalState(config_file, participant_index)

    def test_init(self, state, config_file, participant_index):
        assert state.config_file == config_file
        assert state._participant_index == participant_index
        assert state.block == None
        assert state._block_id == None
        experiment_server._api.process_config_file.assert_called_with(config_file, participant_index)

    def test_change_participant_index(self, state, config_file, participant_index):
        new_participant_index = participant_index + 1
        state.change_participant_index(new_participant_index)
        assert state._participant_index == new_participant_index
        assert state.block == None
        assert state._block_id == None
        experiment_server._api.process_config_file.assert_called_with(config_file, new_participant_index)

    def test_blockBlock(self, state):
        state.set_block(9)
        assert state._block_id == 9
        assert state.block == "a9"

    def test_moveToNextBlock(self, state):
        state.set_block(1)
        state.move_to_next_block()
        assert state._block_id == 2
