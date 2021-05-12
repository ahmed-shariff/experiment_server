import pytest

from experiment_server._participant_ordering import construct_participant_condition
from experiment_server.utils import ExperimentServerConfigurationExcetion, balanced_latin_square


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
    assert any([c1 !=  c2 for c1, c2 in zip(out_config_1, out_config_2)]), "Due to randomization behaviour, this can fail, consider re runnning test"


def test_return_all_configs():
    config = generate_test_config()
    out_config_idx = [c["step_name"] for c in construct_participant_condition(config, 1, [[0, 1, 2, 3]])]
    assert all([idx in out_config_idx for idx in range(4)])


# Latin squares generated from https://cs.uwaterloo.ca/~dmasson/tools/latin_square/
@pytest.mark.parametrize(
    "number_of_conditions, latin_square",[
        (3, [[0,1,2],[0,2,1],[2,0,1],[2,1,0],[1,2,0],[1,0,2]]),
        (4, [[0,1,3,2],[1,2,0,3],[2,3,1,0],[3,0,2,1]]),
        (5, [[0,1,4,2,3],[4,3,0,2,1],[2,3,1,4,0],[1,0,2,4,3],[4,0,3,1,2],[3,2,4,1,0],[1,2,0,3,4],[0,4,1,3,2],[3,4,2,0,1],[2,1,3,0,4]]),
        (6, [[0,1,5,2,4,3],[1,2,0,3,5,4],[2,3,1,4,0,5],[3,4,2,5,1,0],[4,5,3,0,2,1],[5,0,4,1,3,2]])])
def test_balanced_latin_square(number_of_conditions, latin_square):
    generated_latin_square = balanced_latin_square(number_of_conditions)

    assert len(latin_square) == len(generated_latin_square)

    for entry in latin_square:
        assert entry in generated_latin_square
