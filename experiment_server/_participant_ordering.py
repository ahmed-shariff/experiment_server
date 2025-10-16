import random
import itertools
from typing import Dict, List, Union
from easydict import EasyDict as edict

from experiment_server.utils import ExperimentServerConfigurationExcetion, balanced_latin_square


ORDERING_STRATEGY = edict({v:v for v in ["randomize", "latin_square", "as_is"]})
INIT_FINAL_ORDERING_STRATEGY = edict({v:v for v in ["randomize", "as_is"]})


def construct_participant_condition(config: List[Dict],
                                    participant_index: int,
                                    order: Union[dict,list],
                                    init_block_names: Union[dict,list],
                                    final_block_names: Union[dict,list],
                                    within_groups_strategy:Union[str,None]=None,
                                    groups_strategy:Union[str,None]=None,
                                    init_blocks_strategy:Union[str,None]=None,
                                    final_blocks_strategy:Union[str,None]=None) -> List:
    if within_groups_strategy is None:
        within_groups_strategy = ORDERING_STRATEGY.as_is
    elif within_groups_strategy not in list(ORDERING_STRATEGY.values()):
        raise ExperimentServerConfigurationExcetion(f"Allowed values for `within_groups` are {ORDERING_STRATEGY.values()}, for {within_groups_strategy}")

    if groups_strategy is None:
        groups_strategy = ORDERING_STRATEGY.as_is
    elif groups_strategy not in list(ORDERING_STRATEGY.values()):
        raise ExperimentServerConfigurationExcetion(f"Allowed values for `groups` are {ORDERING_STRATEGY.values()}, for {groups_strategy}")

    if init_blocks_strategy is None:
        init_blocks_strategy = INIT_FINAL_ORDERING_STRATEGY.as_is
    elif init_blocks_strategy not in list(INIT_FINAL_ORDERING_STRATEGY.values()):
        raise ExperimentServerConfigurationExcetion(f"Allowed values for `init_blocks_strategy` are {INIT_FINAL_ORDERING_STRATEGY.values()}, for {init_blocks_strategy}")

    if final_blocks_strategy is None:
        final_blocks_strategy = INIT_FINAL_ORDERING_STRATEGY.as_is
    elif final_blocks_strategy not in list(INIT_FINAL_ORDERING_STRATEGY.values()):
        raise ExperimentServerConfigurationExcetion(f"Allowed values for `final_blocks_strategy` are {INIT_FINAL_ORDERING_STRATEGY.values()}, for {final_blocks_strategy}")

    name_to_config_mapping = {}

    for c in config:
        name = c["name"] = str(c["name"])
        if name in name_to_config_mapping:
            raise ExperimentServerConfigurationExcetion(f"Duplicate block name: {name}")
        name_to_config_mapping[c["name"]] = c

    if isinstance(order, list):
        if not all([isinstance(group, list) for group in order]):
            order = [order,]
            # Making sure the stratergy set for groups is used for within groups
            within_groups_strategy = groups_strategy
        if not all([isinstance(g, str) for group in order for g in group]):
            raise ExperimentServerConfigurationExcetion(f"All conditions in order were expected to be strings, got {order}")
        
        _filtered_order = order
        
    elif isinstance(order, dict):
        assert isinstance(groups_strategy, str)
        _filtered_order = [_process_dict_orders(participant_index, order, groups_strategy, "order", ORDERING_STRATEGY), ]

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

    # process init and final blocks
    assert isinstance(init_blocks_strategy, str)
    _filtered_init_order = _process_init_final_block(participant_index, init_block_names, init_blocks_strategy, "init_blocks", INIT_FINAL_ORDERING_STRATEGY)

    if init_blocks_strategy == INIT_FINAL_ORDERING_STRATEGY.randomize:
        random.shuffle(_filtered_init_order)

    assert isinstance(final_blocks_strategy, str)
    _filtered_final_order = _process_init_final_block(participant_index, final_block_names, final_blocks_strategy, "final_blocks", INIT_FINAL_ORDERING_STRATEGY)

    if final_blocks_strategy == INIT_FINAL_ORDERING_STRATEGY.randomize:
        random.shuffle(_filtered_final_order)

    chained_order = _filtered_init_order + list(itertools.chain(*_filtered_order)) + _filtered_final_order
    return [name_to_config_mapping[i] for i in chained_order]


def _process_init_final_block(participant_index:int, block_names: Union[list, dict], blocks_strategy:str, var_name:str, strategy_enum:dict) -> list[str]:
    _filtered_block_names = block_names
    if isinstance(block_names, list):
        if not all([isinstance(n, str) for n in block_names]):
            raise ExperimentServerConfigurationExcetion(f"All conditions in order were expected to be strings, got {block_names}")

    elif isinstance(block_names, dict):
        _filtered_block_names = _process_dict_orders(participant_index, block_names, blocks_strategy, var_name, strategy_enum)
    assert isinstance(_filtered_block_names, list)

    return _filtered_block_names


def _process_dict_orders(participant_index:int, block_names: dict, blocks_strategy:str, var_name:str, strategy_enum) -> list:
    block_names = {int(k):v for k, v in block_names.items()}
    if not all([isinstance(_order, list) for _order in block_names.values()]):
        raise ExperimentServerConfigurationExcetion(f"Each group in {var_name} for all participants needs to be list, got {block_names}")
    if not all([isinstance(val, str) for _order in block_names.values() for val in _order]):
        raise ExperimentServerConfigurationExcetion(f"All conditions in {var_name} for all participants needs to be a strings, got {block_names}")

    if not all([idx+1 in block_names.keys() for idx in range(len(block_names))]):
        raise ExperimentServerConfigurationExcetion(f"Keys order in {var_name} should match the consecutive indices starting from 1. Got keys {list(block_names.keys())}, expected keys {[idx + 1 for idx in list(range(len(block_names)))]}")

    if blocks_strategy != strategy_enum.as_is:
        raise ExperimentServerConfigurationExcetion(f"Ordering strategy for {var_name} should be {strategy_enum.as_is} when {var_name} is a dictionary. Got {blocks_strategy}")
    _key = ((participant_index - 1) % len(block_names)) + 1
    _filtered_block_names = block_names[_key]

    return _filtered_block_names
