import random

# latin_square = [[1, 2, 3, 4, 5, 6, 7, 8, 9],
#                 [2, 3, 1, 5, 6, 4, 8, 9, 7],
#                 [3, 1, 2, 6, 4, 5, 9, 7, 8],
#                 [4, 5, 6, 7, 8, 9, 1, 2, 3],
#                 [5, 6, 4, 8, 9, 7, 2, 3, 1],
#                 [6, 4, 5, 9, 7, 8, 3, 1, 2],
#                 [7, 8, 9, 1, 2, 3, 4, 5, 6],
#                 [8, 9, 7, 2, 3, 1, 5, 6, 4],
#                 [9, 7, 8, 3, 1, 2, 6, 4, 5]]

latin_square = [[1, 2, 3, 4],
                [3, 4, 1, 2],
                [4, 3, 2, 1],
                [2, 1, 4, 3]]


def _construct_participant_condition(config, participant_id, use_latin_square=False, latin_square=None, config_categorization=None, default_configuration=None, randomize=True):
    if participant_id < 1:
        participant_id = 1
    if use_latin_square:
        _config = [config[i - 1] for i in latin_square[(participant_id - 1) % len(config)]]
    else:
        assert len(config_categorization) == 2
        if not randomize or participant_id % len(config_categorization) == 0:
            init_condition = config_categorization[0][:]
            other_condition = config_categorization[1][:]
        else:
            init_condition = config_categorization[1][:]
            other_condition = config_categorization[0][:]
        init_condition = [config[i] for i in init_condition]
        other_condition = [config[i] for i in other_condition]
        random.shuffle(init_condition)
        random.shuffle(other_condition)

        if default_configuration is not None:
            default_configuration_config = default_configuration[0]["config"]
            non_default_keys = [k for k in default_configuration_config.keys() if k not in ["conditionId"]]

            init_condition_train = init_condition[0].copy()
            init_condition_train["config"] = init_condition_train["config"].copy()
            init_condition_train["config"]["conditionId"] = "training1"
            for k in non_default_keys:
                init_condition_train["config"][k] = default_configuration_config[k]

            other_condition_train = other_condition[0].copy()
            other_condition_train["config"] = other_condition_train["config"].copy()
            other_condition_train["config"]["conditionId"] = "training2"
            for k in non_default_keys:
                other_condition_train["config"][k] = default_configuration_config[k]

            _config = [init_condition_train] + init_condition + [other_condition_train] + other_condition

        else:
            _config = init_condition + other_condition
        # _config = [config[i] for i in _config_list]
    return _config
