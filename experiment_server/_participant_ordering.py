import random
import itertools
from easydict import EasyDict as edict

from experiment_server.utils import ExperimentServerConfigurationExcetion, balanced_latin_square


ORDERING_BEHAVIOUR = edict({v:v for v in ["randomize", "latin_square", "as_is"]})


def construct_participant_condition(config, participant_id, order, within_groups=None, groups=None):
    if within_groups is None:
        within_groups = ORDERING_BEHAVIOUR.as_is
    if groups is None:
        groups = ORDERING_BEHAVIOUR.as_is

    if within_groups not in list(ORDERING_BEHAVIOUR.values()):
        raise ExperimentServerConfigurationExcetion(f"Allowed values for `within_groups` are {ORDERING_BEHAVIOUR.values()}, for {within_groups}")
    if groups not in list(ORDERING_BEHAVIOUR.values()):
        raise ExperimentServerConfigurationExcetion(f"Allowed values for `groups` are {ORDERING_BEHAVIOUR.values()}, for {groups}")
    
    if not all([isinstance(group, list) for group in order]):
        raise ExperimentServerConfigurationExcetion(f"Each group in order needs to be list, got {order}")
    if not all([isinstance(g, int) for group in order for g in group]):
        raise ExperimentServerConfigurationExcetion(f"Each group in the order needs to be a list of `int`, got {order}")

    if groups == ORDERING_BEHAVIOUR.randomize:
        random.shuffle(order)

    if within_groups == ORDERING_BEHAVIOUR.randomize:
        for group in order:
            random.shuffle(group)

    return [config[i] for i in list(itertools.chain(*order))]
    
    
def _construct_participant_condition_old(config, participant_id, use_latin_square=False, latin_square=None, config_categorization=None, default_configuration=None, randomize=True):
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
