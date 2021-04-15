import pytest

from experiment_server._participant_ordering import construct_participant_condition
from experiment_server.utils import ExperimentServerConfigurationExcetion


def generate_test_config():
    config = []
    for i in range(4):
        config.append({"step_name": i,
                       "config": {"participantId": 1}})
    return config


@pytest.mark.parametrize(
    "order",[
        [0, 1, 2, 3],
        [[2], [3], 1, [0]],
        [[1], [2], [3], "str"],
        [[1], [[2]], ["str"], [4]]])
def test_checks(order):
    with pytest.raises(ExperimentServerConfigurationExcetion):
        construct_participant_condition(generate_test_config(), 1, order=order)

@pytest.mark.parametrize(
    "order, randomize_within_groups, randomize_groups",[
        ([[0], [1], [2], [3]], False, True),
        ([[0, 1, 2, 3]], True, False),
        ([[0, 1], [2, 3]], True, True)])
def test_group_randomization(order, randomize_within_groups, randomize_groups):
    config = generate_test_config()
    out_config_1 = [c["step_name"] for c in construct_participant_condition(config, 1, order, randomize_within_groups, randomize_groups)]
    out_config_2 = [c["step_name"] for c in construct_participant_condition(config, 1, order, randomize_within_groups, randomize_groups)]
    assert any([c1 !=  c2 for c1, c2 in zip(out_config_1, out_config_2)])        


def test_return_all_configs():
    config = generate_test_config()
    out_config_idx = [c["step_name"] for c in construct_participant_condition(config, 1, [[0, 1, 2, 3]])]
    assert all([idx in out_config_idx for idx in range(4)])
