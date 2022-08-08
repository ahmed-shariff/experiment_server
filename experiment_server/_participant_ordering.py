import random
import itertools
from typing import Dict, List, Union
from easydict import EasyDict as edict

from experiment_server.utils import ExperimentServerConfigurationExcetion, balanced_latin_square


ORDERING_BEHAVIOUR = edict({v:v for v in ["randomize", "latin_square", "as_is"]})


def construct_participant_condition(config: List[Dict], participant_index: int, order: Union[dict, list], within_groups:str =None, groups:str =None) -> List:
    if within_groups is None:
        within_groups = ORDERING_BEHAVIOUR.as_is
    if groups is None:
        groups = ORDERING_BEHAVIOUR.as_is

    step_names = {}

    # To make sure the string based indexing works
    for idx, c in enumerate(config):
        c["step_name"] = str(c["step_name"])
        step_names[c["step_name"]] = idx

    if len(set(step_names.values()).symmetric_difference(list(range(len(config))))) != 0:
        raise ExperimentServerConfigurationExcetion("Duplicate step names: {}".format(set([c["step_name"] for idx, c in enumerate(config) if idx not in step_names.values()])))

    if within_groups not in list(ORDERING_BEHAVIOUR.values()):
        raise ExperimentServerConfigurationExcetion(f"Allowed values for `within_groups` are {ORDERING_BEHAVIOUR.values()}, for {within_groups}")
    if groups not in list(ORDERING_BEHAVIOUR.values()):
        raise ExperimentServerConfigurationExcetion(f"Allowed values for `groups` are {ORDERING_BEHAVIOUR.values()}, for {groups}")

    if isinstance(order, list):
        if not all([isinstance(group, list) for group in order]):
            raise ExperimentServerConfigurationExcetion(f"Each group in order needs to be list, got {order}")
        if not all([isinstance(g, int) for group in order for g in group]) and not all([isinstance(g, str) for group in order for g in group]):
            raise ExperimentServerConfigurationExcetion(f"Each group in the order needs to be a list of `int` or list of `str`, got {order}")
        
        _filtered_order = order
        
    elif isinstance(order, dict):
        order = {int(k):v for k, v in order.items()}
        if not all([isinstance(_order, list) for _order in order.values()]) or not all([isinstance(group, list) for _order in order.values() for group in _order]):
            raise ExperimentServerConfigurationExcetion(f"Each group in orders for all participants needs to be list, got {order}")
        if not all([isinstance(g, int) for _order in order.values() for group in _order for g in group]) and not all([isinstance(g, str) for _order in order.values() for group in _order for g in group]):
            raise ExperimentServerConfigurationExcetion(f"Each group in orders for all participants needs to be a list of `int` or list of `str`, got {order}")

        if not all([idx+1 in order.keys() for idx in range(len(order))]):
            raise ExperimentServerConfigurationExcetion(f"Keys order oredr should match the consecutive indices starting from 1. Got keys {list(order.keys())}, expected keys {list(range(len(order)))}")

        if groups != ORDERING_BEHAVIOUR.as_is:
            raise ExperimentServerConfigurationExcetion(f"Ordering behaviour for groups should be {ORDERING_BEHAVIOUR.as_is} when order is a dictionary. Got {groups}")
        _key = ((participant_index - 1) % len(order)) + 1
        _filtered_order = order[_key]


    if groups == ORDERING_BEHAVIOUR.randomize:
        random.shuffle(_filtered_order)
    elif groups == ORDERING_BEHAVIOUR.latin_square:
        _latin_square = balanced_latin_square(len(_filtered_order))
        _participant_order = _latin_square[(participant_index - 1) % len(_filtered_order)]

        _filtered_order = [_filtered_order[idx] for idx in _participant_order]

    if within_groups == ORDERING_BEHAVIOUR.randomize:
        for group in _filtered_order:
            random.shuffle(group)
    elif within_groups == ORDERING_BEHAVIOUR.latin_square:
        elements_in_group = set([len(_g) for _g  in _filtered_order])
        if len(elements_in_group) != 1:
            raise ExperimentServerConfigurationExcetion(f"Currently {ORDERING_BEHAVIOUR.latin_square} not supported for `within_groups` when the number of elements in all groups are not the same")
        else:
            _elements_count = elements_in_group.pop()
            _latin_square = balanced_latin_square(_elements_count)
            _group_order = _latin_square[(participant_index - 1) % _elements_count]

            _filtered_order = [[_g[idx] for idx in _group_order] for _g in _filtered_order]

    chained_order = list(itertools.chain(*_filtered_order))
    if isinstance(chained_order[0], int):
        return [config[i] for i in chained_order]
    else:
        return [config[step_names[i]] for i in chained_order]
    

# def _construct_participant_condition_old(config, participant_index, use_latin_square=False, latin_square=None, config_categorization=None, default_configuration=None, randomize=True):
#     if participant_index < 1:
#         participant_index = 1
#     if use_latin_square:
#         _config = [config[i - 1] for i in latin_square[(participant_index - 1) % len(config)]]
#     else:
#         assert len(config_categorization) == 2
#         if not randomize or participant_index % len(config_categorization) == 0:
#             init_condition = config_categorization[0][:]
#             other_condition = config_categorization[1][:]
#         else:
#             init_condition = config_categorization[1][:]
#             other_condition = config_categorization[0][:]
#         init_condition = [config[i] for i in init_condition]
#         other_condition = [config[i] for i in other_condition]
#         random.shuffle(init_condition)
#         random.shuffle(other_condition)

#         if default_configuration is not None:
#             default_configuration_config = default_configuration[0]["config"]
#             non_default_keys = [k for k in default_configuration_config.keys() if k not in ["conditionId"]]

#             init_condition_train = init_condition[0].copy()
#             init_condition_train["config"] = init_condition_train["config"].copy()
#             init_condition_train["config"]["conditionId"] = "training1"
#             for k in non_default_keys:
#                 init_condition_train["config"][k] = default_configuration_config[k]

#             other_condition_train = other_condition[0].copy()
#             other_condition_train["config"] = other_condition_train["config"].copy()
#             other_condition_train["config"]["conditionId"] = "training2"
#             for k in non_default_keys:
#                 other_condition_train["config"][k] = default_configuration_config[k]

#             _config = [init_condition_train] + init_condition + [other_condition_train] + other_condition

#         else:
#             _config = init_condition + other_condition
#         # _config = [config[i] for i in _config_list]
#     return _config
