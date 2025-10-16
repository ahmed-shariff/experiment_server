import random
import itertools
from typing import Dict, List, Union
from easydict import EasyDict as edict

from experiment_server.utils import ExperimentServerConfigurationExcetion, balanced_latin_square


ORDERING_STRATEGY = edict({v:v for v in ["randomize", "latin_square", "as_is"]})


def construct_participant_condition(config: List[Dict], participant_index: int, order: Union[dict,list], within_groups_strategy:Union[str,None]=None, groups_strategy:Union[str,None]=None) -> List:
    if within_groups_strategy is None:
        within_groups_strategy = ORDERING_STRATEGY.as_is
    if groups_strategy is None:
        groups_strategy = ORDERING_STRATEGY.as_is

    name_to_config_mapping = {}

    for c in config:
        name = c["name"] = str(c["name"])
        if name in name_to_config_mapping:
            raise ExperimentServerConfigurationExcetion(f"Duplicate block name: {name}")
        name_to_config_mapping[c["name"]] = c

    if within_groups_strategy not in list(ORDERING_STRATEGY.values()):
        raise ExperimentServerConfigurationExcetion(f"Allowed values for `within_groups` are {ORDERING_STRATEGY.values()}, for {within_groups_strategy}")
    if groups_strategy not in list(ORDERING_STRATEGY.values()):
        raise ExperimentServerConfigurationExcetion(f"Allowed values for `groups` are {ORDERING_STRATEGY.values()}, for {groups_strategy}")

    if isinstance(order, list):
        if not all([isinstance(group, list) for group in order]):
            order = [order,]
            # Making sure the stratergy set for groups is used for within groups
            within_groups_strategy = groups_strategy
        if not all([isinstance(g, str) for group in order for g in group]):
            raise ExperimentServerConfigurationExcetion(f"All conditions in order were expected to be strings, got {order}")
        
        _filtered_order = order
        
    elif isinstance(order, dict):
        order = {int(k):v for k, v in order.items()}
        if not all([isinstance(_order, list) for _order in order.values()]):
            raise ExperimentServerConfigurationExcetion(f"Each group in orders for all participants needs to be list, got {order}")
        if not all([isinstance(val, str) for _order in order.values() for val in _order]):
            raise ExperimentServerConfigurationExcetion(f"All conditions in order for all participants needs to be a strings, got {order}")

        if not all([idx+1 in order.keys() for idx in range(len(order))]):
            raise ExperimentServerConfigurationExcetion(f"Keys order oredr should match the consecutive indices starting from 1. Got keys {list(order.keys())}, expected keys {[idx + 1 for idx in list(range(len(order)))]}")

        if groups_strategy != ORDERING_STRATEGY.as_is:
            raise ExperimentServerConfigurationExcetion(f"Ordering behaviour for groups should be {ORDERING_STRATEGY.as_is} when order is a dictionary. Got {groups_strategy}")
        _key = ((participant_index - 1) % len(order)) + 1
        _filtered_order = [order[_key],]

    if groups_strategy == ORDERING_STRATEGY.randomize:
        random.shuffle(_filtered_order)
    elif groups_strategy == ORDERING_STRATEGY.latin_square:
        _latin_square = balanced_latin_square(len(_filtered_order))
        _participant_order = _latin_square[(participant_index - 1) % len(_filtered_order)]

        _filtered_order = [_filtered_order[idx] for idx in _participant_order]

    if within_groups_strategy == ORDERING_STRATEGY.randomize:
        for group in _filtered_order:
            random.shuffle(group)
    elif within_groups_strategy == ORDERING_STRATEGY.latin_square:
        elements_in_group = set([len(_g) for _g  in _filtered_order])
        if len(elements_in_group) != 1:
            raise ExperimentServerConfigurationExcetion(f"Currently {ORDERING_STRATEGY.latin_square} not supported for `within_groups` when the number of elements in all groups are not the same")
        else:
            _elements_count = elements_in_group.pop()
            _latin_square = [el for l in balanced_latin_square(_elements_count) for el in [l,] * len(_filtered_order)]
            _group_order = _latin_square[(participant_index - 1) % (_elements_count * len(_filtered_order))]

            _filtered_order = [[_g[idx] for idx in _group_order] for _g in _filtered_order]

    chained_order = list(itertools.chain(*_filtered_order))
    return [name_to_config_mapping[i] for i in chained_order]
