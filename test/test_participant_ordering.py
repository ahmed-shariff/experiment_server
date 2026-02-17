import itertools
import pytest

from experiment_server._participant_ordering import construct_participant_condition, ORDERING_STRATEGY, INIT_FINAL_ORDERING_STRATEGY
from experiment_server.utils import ExperimentServerConfigurationException, balanced_latin_square


def generate_test_config(size=4, init_final_size=3):
    config = []
    for i in range(size):
        config.append({"name": i,
                       "config": {"value": 1}})
    for i in range(init_final_size):
        config.append({"name": f"init_{i}",
                       "config": {"value": 1}})
        config.append({"name": f"final_{i}",
                       "config": {"value": 1}})
    return config


@pytest.mark.parametrize(
    "order",[
        [[2], [3], 1, [0]],
        [[1], [2], [3], "str"],
        [[1], [[2]], ["str"], [4]],
        [["2"], ["3"], "1", ["0"]],
        [["2"], ["3"], 1, ["0"]],
        [["2"], ["3"], [1], ["0"]],
        {"1": [[0]], "2":[[1]], "3":[4]},
        {"1": [0], "2":[1], "3":4},
        {"2":[[1]], "3":[[4]]},
        {"1": [[0]], "2":[["1"]], "3":[["4"]]},
        {"1": [[0]], "2":[["1"]], "3":[[4]]},
        [["2"], ["3"], "1", ["0"]]])
def test_order_fail_checks(order):
    with pytest.raises(ExperimentServerConfigurationException):
        construct_participant_condition(generate_test_config(), 1, order=order, init_block_names=[], final_block_names=[])


@pytest.mark.parametrize(
    "order",[
        ["0", "1", "2", "3"],
        [["0"], ["1"], ["2"], ["3"]],
        {"1": ["0"], "2":["1"], "3":["3"]}])
def test_order_pass_checks(order):
    try:
        config = construct_participant_condition(generate_test_config(), 1, order=order, init_block_names=[], final_block_names=[])
        assert config[0]["name"] == "0"
    except ExperimentServerConfigurationException:
        assert False, "Raised ExperimentServerConfigurationExcetion"


def test_duplicate_name_fail():
    config = generate_test_config()
    config[1]["name"] = "0"
    with pytest.raises(ExperimentServerConfigurationException):
        construct_participant_condition(config, 1, order=[], init_block_names=[], final_block_names=[])


@pytest.mark.parametrize(
    "order, randomize_within_groups, randomize_groups",[
        ([["0"], ["1"], ["2"], ["3"]], ORDERING_STRATEGY.as_is, ORDERING_STRATEGY.randomize),
        ([["0", "1", "2", "3"]], ORDERING_STRATEGY.randomize, ORDERING_STRATEGY.as_is),
        ([["0", "1"], ["2", "3"]], ORDERING_STRATEGY.randomize, ORDERING_STRATEGY.randomize)])
def test_group_randomization(order, randomize_within_groups, randomize_groups):
    config = generate_test_config()
    out_config_1 = [c["name"] for c in construct_participant_condition(config, 1, order, [], [], randomize_within_groups, randomize_groups)]
    out_config_2 = [c["name"] for c in construct_participant_condition(config, 1, order, [], [], randomize_within_groups, randomize_groups)]
    out_config_3 = [c["name"] for c in construct_participant_condition(config, 1, order, [], [], randomize_within_groups, randomize_groups)]
    out_config_4 = [c["name"] for c in construct_participant_condition(config, 1, order, [], [], randomize_within_groups, randomize_groups)]
    assert any([pair[0] != pair[1]  for c in zip(out_config_1, out_config_2, out_config_3, out_config_4) for pair in itertools.combinations(c, 2)])


def test_init_randomization():
    init_blocks = ["init_0", "init_1", "init_2"]
    config = generate_test_config()
    out_config_1 = [c["name"] for c in construct_participant_condition(config, 1, ["0"], init_blocks, ["2", "3"], None, None, INIT_FINAL_ORDERING_STRATEGY.randomize, None)]
    out_config_2 = [c["name"] for c in construct_participant_condition(config, 1, ["0"], init_blocks, ["2", "3"], None, None, INIT_FINAL_ORDERING_STRATEGY.randomize, None)]
    out_config_3 = [c["name"] for c in construct_participant_condition(config, 1, ["0"], init_blocks, ["2", "3"], None, None, INIT_FINAL_ORDERING_STRATEGY.randomize, None)]
    out_config_4 = [c["name"] for c in construct_participant_condition(config, 1, ["0"], init_blocks, ["2", "3"], None, None, INIT_FINAL_ORDERING_STRATEGY.randomize, None)]
    comps = [pair[0] != pair[1]  for all_c in zip(*(c[:3] for c in [out_config_1, out_config_2, out_config_3, out_config_4])) for pair in itertools.combinations(all_c, 2)]
    assert any(comps)
    comps = [pair[0] == pair[1]  for all_c in zip(*(c[3:] for c in [out_config_1, out_config_2, out_config_3, out_config_4])) for pair in itertools.combinations(all_c, 2)]
    assert all(comps)


def test_final_randomization():
    final_blocks = ["final_0", "final_1", "final_2"]
    config = generate_test_config()
    out_config_1 = [c["name"] for c in construct_participant_condition(config, 1, ["0"], ["2", "3"], final_blocks, None, None, None, INIT_FINAL_ORDERING_STRATEGY.randomize)]
    out_config_2 = [c["name"] for c in construct_participant_condition(config, 1, ["0"], ["2", "3"], final_blocks, None, None, None, INIT_FINAL_ORDERING_STRATEGY.randomize)]
    out_config_3 = [c["name"] for c in construct_participant_condition(config, 1, ["0"], ["2", "3"], final_blocks, None, None, None, INIT_FINAL_ORDERING_STRATEGY.randomize)]
    out_config_4 = [c["name"] for c in construct_participant_condition(config, 1, ["0"], ["2", "3"], final_blocks, None, None, None, INIT_FINAL_ORDERING_STRATEGY.randomize)]
    comps = [pair[0] != pair[1]  for all_c in zip(*(c[-3:] for c in [out_config_1, out_config_2, out_config_3, out_config_4])) for pair in itertools.combinations(all_c, 2)]
    assert any(comps)
    comps = [pair[0] == pair[1]  for all_c in zip(*(c[:-3] for c in [out_config_1, out_config_2, out_config_3, out_config_4])) for pair in itertools.combinations(all_c, 2)]
    assert all(comps)


def test_return_all_configs():
    config = generate_test_config()
    out_config_idx = [c["name"] for c in construct_participant_condition(config, 1, [["0", "1", "2", "3"]], init_block_names=[], final_block_names=[])]
    assert all([str(idx) in out_config_idx for idx in range(4)])


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


@pytest.mark.parametrize(
    "size, order", [
        [6, [[0, 1], [2, 3], [4, 5]]],
        [8, [[0, 1], [2, 3], [4, 5], [6, 7]]],
        ])
def test_group_latin_square(size, order):
    order = [[str(g) for g in group] for group in order]
    collected_configs = []

    # Making sure the participants are rotated the same conditions
    for participant_index in range(size):
        config_a = construct_participant_condition(generate_test_config(size), participant_index, order, [], [], None, ORDERING_STRATEGY.latin_square)
        config_b = construct_participant_condition(generate_test_config(size), participant_index + size, order, [], [], None, ORDERING_STRATEGY.latin_square)
        assert config_a == config_b
        collected_configs.append("".join([str(c["name"]) for c in config_a]))

    # Making sure the different conditions are different for each participant within the number of conditions
    assert len(set(collected_configs)) == len(order)

@pytest.mark.parametrize(
    "size, participant_index, order, init_blocks, final_blocks, expected_order", [
        [4, 1, {1: ["0", "1"], 2: ["2", "3"]}, [], [], ["0", "1"]],
        [4, 2, {1: ["0", "1"], 2: ["2", "3"]}, [], [], ["2", "3"]],
        [4, 3, {1: ["0", "1"], 2: ["2", "3"]}, [], [], ["0", "1"]],
        [4, 4, {1: ["0", "1"], 2: ["2", "3"]}, [], [], ["2", "3"]],
        [4, 1, {1: ["0", "1"], 2: ["2", "3"]}, {1: ["init_0"], 2: ["init_1"]}, {1: ["final_0"], 2: ["final_1"]}, ["init_0", "0", "1", "final_0"]],
        [4, 2, {1: ["0", "1"], 2: ["2", "3"]}, {1: ["init_0"], 2: ["init_1"]}, {1: ["final_0"], 2: ["final_1"]}, ["init_1", "2", "3", "final_1"]],
        [4, 3, {1: ["0", "1"], 2: ["2", "3"]}, {1: ["init_0"], 2: ["init_1"]}, {1: ["final_0"], 2: ["final_1"]}, ["init_0", "0", "1", "final_0"]],
        [4, 4, {1: ["0", "1"], 2: ["2", "3"]}, {1: ["init_0"], 2: ["init_1"]}, {1: ["final_0"], 2: ["final_1"]}, ["init_1", "2", "3", "final_1"]],
        ])
def test_dict_order(size, participant_index, order, init_blocks, final_blocks, expected_order):
    config = construct_participant_condition(generate_test_config(size), participant_index, order, init_block_names=init_blocks, final_block_names=final_blocks)
    assert [c["name"] for c in config] == expected_order
