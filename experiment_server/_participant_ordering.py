import random
import itertools
from typing import Dict, List, Union
from easydict import EasyDict as edict

from experiment_server.utils import ExperimentServerConfigurationException, balanced_latin_square


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
    """
    Construct the per-participant ordered list of block configurations based on a global experiment
    configuration, ordering specification, and a participant index.

    The function maps block names defined in `config` to a concrete ordering for a single participant,
    applying ordering strategies at three levels:
      - groups (ordering of groups of blocks)
      - within_groups (ordering of elements inside each group)
      - init_blocks and final_blocks (ordering of initial and final blocks appended before/after main groups)

    Behavior details and constraints:
        - Names in `order`, `init_block_names`, and `final_block_names` are validated to be strings and must
          match unique names in `config`. Duplicate names in `config` cause an error.
        - When `groups_strategy` or `within_groups_strategy` is "randomize", Python's random.shuffle is used
          (non-deterministic unless the caller seeds the RNG).
        - When "latin_square" is requested for groups or within-group ordering, a balanced Latin square
          generator is used and `participant_index` selects the row; latin-square requires equal-sized
          values where appropriate (e.g., all groups must have the same size when using within-group
          latin-square).
        - When dictionary mappings are provided for order/init/final blocks, keys are expected to be
          1-based consecutive integer indices (or strings coercible to those integers). For dicts, the
          corresponding strategy argument must be "as_is".

    Notes:
          The function does not modify the input `config` objects beyond coercing the "name" field to str.
              Deterministic rotation behavior for latin-square and dict-based selection is 1-based and uses
              (participant_index - 1) modulo the appropriate period.

    Args:
        config (List[Dict]): A list of block configuration dictionaries. Each dict must contain a
        unique "name" key whose value will be coerced to a string. The returned value is a list of
        these configuration dicts arranged according to the computed participant order.

        participant_index (int): 1-based index of the participant used to select deterministic
        rotations when latin-square or per-participant dictionary-based indexing is used. Must be
        positive.

        order (Union[dict, list]):
            Specification of the main experimental order. Two forms are supported:

            * list of groups: e.g. [["A","B"], ["C","D","E"]] where each inner list is a group of block names.
              If a flat list of strings is provided (["A","B","C"]) it will be treated as a single group.
            * dict keyed by participant index (string or int keys) mapping to a group-list for that participant.
              When a dict is provided, the `groups_strategy` must be "as_is" (per-participant assignment by key).

            All block names in the resolved order must be strings and must exist in `config`.

        init_block_names (Union[dict, list]): Names of blocks to prepend for the
            participant. Accepts a list of block names (strings) or a dictionary keyed by participant
            indices (1-based) to select a list for the participant. When a dict is supplied, the
            strategy for init blocks must be "as_is" (per-participant selection).

        final_block_names (Union[dict, list]): Names of blocks to append for the
            participant. Accepts same forms and constraints as init_block_names.

        within_groups_strategy (Union[str, None]):
            Strategy applied to the ordering of elements inside each group. Allowed values:

              * "as_is"      - leave element order as provided
              * "randomize"  - shuffle elements inside each group (non-deterministic)
              * "latin_square" - apply a balanced Latin square to permute positions across participants

            If None, defaults to "as_is". If `order` was provided as a list-of-lists and `groups_strategy`
            was set to "randomize" or "latin_square" and not explicitly set for `within_groups_strategy`,
            the `groups_strategy` may be reused for within-groups behavior in some calling patterns.

        groups_strategy (Union[str, None]): Strategy applied to the sequence of groups. Allowed values:

              * "as_is"
              * "randomize"
              * "latin_square"

            If None, defaults to "as_is". When `order` is a dict keyed by participant index, `groups_strategy`
            must be "as_is" because the dict already selects per-participant grouping.

        init_blocks_strategy (Union[str, None]): Strategy for ordering initial blocks. Allowed values:

              * "as_is"
              * "randomize"

            If None, defaults to "as_is". When init_block_names is a dict keyed by participant index,
            the strategy must be "as_is" (per-participant selection).

        final_blocks_strategy (Union[str, None]): Strategy for ordering final blocks. Same semantics and allowed values as init_blocks_strategy.

    Returns:
        List: A list of block configuration dictionaries (the original dicts from `config`) in the final
            order constructed for the participant: [init_blocks..., main_blocks..., final_blocks...].
            The main_blocks portion is produced by flattening the possibly nested group structure after
            applying the requested group- and within-group strategies.

    Exceptions:
        ExperimentServerConfigurationExcetion: on invalid configuration, such as:

            * duplicate block names in config
            * non-string block names in orders
            * unsupported strategy names
            * inconsistent group sizes for latin-square within-group ordering
            * improper dict key sets or types when dict-based per-participant selection is used
    """
    if within_groups_strategy is None:
        within_groups_strategy = ORDERING_STRATEGY.as_is
    elif within_groups_strategy not in list(ORDERING_STRATEGY.values()):
        raise ExperimentServerConfigurationException(f"Allowed values for `within_groups` are {ORDERING_STRATEGY.values()}, for {within_groups_strategy}")

    if groups_strategy is None:
        groups_strategy = ORDERING_STRATEGY.as_is
    elif groups_strategy not in list(ORDERING_STRATEGY.values()):
        raise ExperimentServerConfigurationException(f"Allowed values for `groups` are {ORDERING_STRATEGY.values()}, for {groups_strategy}")

    if init_blocks_strategy is None:
        init_blocks_strategy = INIT_FINAL_ORDERING_STRATEGY.as_is
    elif init_blocks_strategy not in list(INIT_FINAL_ORDERING_STRATEGY.values()):
        raise ExperimentServerConfigurationException(f"Allowed values for `init_blocks_strategy` are {INIT_FINAL_ORDERING_STRATEGY.values()}, for {init_blocks_strategy}")

    if final_blocks_strategy is None:
        final_blocks_strategy = INIT_FINAL_ORDERING_STRATEGY.as_is
    elif final_blocks_strategy not in list(INIT_FINAL_ORDERING_STRATEGY.values()):
        raise ExperimentServerConfigurationException(f"Allowed values for `final_blocks_strategy` are {INIT_FINAL_ORDERING_STRATEGY.values()}, for {final_blocks_strategy}")

    name_to_config_mapping = {}

    for c in config:
        name = c["name"] = str(c["name"])
        if name in name_to_config_mapping:
            raise ExperimentServerConfigurationException(f"Duplicate block name: {name}")
        name_to_config_mapping[c["name"]] = c

    if isinstance(order, list):
        if not all([isinstance(group, list) for group in order]):
            order = [order,]
            # Making sure the stratergy set for groups is used for within groups
            within_groups_strategy = groups_strategy
        if not all([isinstance(g, str) for group in order for g in group]):
            raise ExperimentServerConfigurationException(f"All conditions in order were expected to be strings, got {order}")
        
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
            raise ExperimentServerConfigurationException(f"Currently {ORDERING_STRATEGY.latin_square} not supported for `within_groups` when the number of elements in all groups are not the same")
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
    """Helper to process initial and final blocks. See `construct_participant_condition` for more details."""
    _filtered_block_names = block_names
    if isinstance(block_names, list):
        if not all([isinstance(n, str) for n in block_names]):
            raise ExperimentServerConfigurationException(f"All conditions in order were expected to be strings, got {block_names}")

    elif isinstance(block_names, dict):
        _filtered_block_names = _process_dict_orders(participant_index, block_names, blocks_strategy, var_name, strategy_enum)
    assert isinstance(_filtered_block_names, list)

    return _filtered_block_names


def _process_dict_orders(participant_index:int, block_names: dict, blocks_strategy:str, var_name:str, strategy_enum) -> list:
    """Helper to process dictionary patterns. See `construct_participant_condition` for more details."""
    block_names = {int(k):v for k, v in block_names.items()}
    if not all([isinstance(_order, list) for _order in block_names.values()]):
        raise ExperimentServerConfigurationException(f"Each group in {var_name} for all participants needs to be list, got {block_names}")
    if not all([isinstance(val, str) for _order in block_names.values() for val in _order]):
        raise ExperimentServerConfigurationException(f"All conditions in {var_name} for all participants needs to be a strings, got {block_names}")

    if not all([idx+1 in block_names.keys() for idx in range(len(block_names))]):
        raise ExperimentServerConfigurationException(f"Keys order in {var_name} should match the consecutive indices starting from 1. Got keys {list(block_names.keys())}, expected keys {[idx + 1 for idx in list(range(len(block_names)))]}")

    if blocks_strategy != strategy_enum.as_is:
        raise ExperimentServerConfigurationException(f"Ordering strategy for {var_name} should be {strategy_enum.as_is} when {var_name} is a dictionary. Got {blocks_strategy}")
    _key = ((participant_index - 1) % len(block_names)) + 1
    _filtered_block_names = block_names[_key]

    return _filtered_block_names
