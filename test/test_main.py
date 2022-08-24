import pytest
import importlib
import pytest_mock
import experiment_server._main
from .fixtures import config_file, participant_index


class TestGlobalState:
    @pytest.fixture()
    def state(self, config_file, participant_index, mocker):
        process_config_file = mocker.patch("experiment_server._main.process_config_file", return_value=[f"a{i}" for i in range(10)])
        return experiment_server._main.GlobalState(config_file, participant_index)

    def test_init(self, state, config_file, participant_index):
        assert state.config_file == config_file
        assert state._participant_index == participant_index
        assert state.step == None
        assert state._step_id == None
        experiment_server._main.process_config_file.assert_called_with(config_file, participant_index)

    def test_change_participant_index(self, state, config_file, participant_index):
        new_participant_index = participant_index + 1
        state.change_participant_index(new_participant_index)
        assert state._participant_index == new_participant_index
        assert state.step == None
        assert state._step_id == None
        experiment_server._main.process_config_file.assert_called_with(config_file, new_participant_index)

    def test_stepStep(self, state):
        state.setStep(9)
        assert state._step_id == 9
        assert state.step == "a9"

    def test_moveToNextStep(self, state):
        state.setStep(1)
        state.moveToNextStep()
        assert state._step_id == 2

    def test_get_global_data(self, state, participant_index):
        out = state.get_global_data()
        assert out["participant_index"] == participant_index
        assert out["config_lenght"] == 10
