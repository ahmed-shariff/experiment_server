import pytest
from experiment_server.utils import merge_dicts
from deepdiff import DeepDiff

@pytest.mark.parametrize(
    "dict_a, dict_b, expected", [
        ({"a": "boo", "b": "hoo"}, {"a": "boo", "b": "roo"}, {"a": "boo", "b": "hoo"}),
        ({"a": "boo"}, {"a": "boo", "b": "roo"}, {"a": "boo", "b": "roo"}),
        ({"a": "boo", "b": "hoo"}, {"a": "boo"}, {"a": "boo", "b": "hoo"}),
        ({'step_name': 'a', 'extends': 'b', 'param1': '0', 'step_idx': 0},
         {'step_name': 'b', 'extends': 'c', 'param2': '0', 'step_idx': 1, 'param3': '0'},
         {'step_name': 'a', 'extends': 'b', 'param1': '0', 'param2': '0', 'param3': '0', 'step_idx': 0}),
        ({"a": "boo"}, {"a": "boo", "b": {"x": "roo"}}, {"a": "boo", "b": {"x": "roo"}}),
        ({"a": "boo", "b": {"c": "roma", "d": "once", "e": {"f": "foo"}}},
         {"a": "foo", "b": {"c": "soma", "d": {"d": "boo"}, "e": {"f": "foo"}}},
         {"a": "boo", "b": {"c": "roma", "d": "once", "e": {"f": "foo"}}}),
        ({"a": "boo", "b": {"c": "roma", "d": "once", "e": {"f": "foo"}}},
         {"a": "foo", "b": {"c": "soma", "d": {"d": "boo"}, "e": {"f": "foo", "g": "godad"}}},
         {"a": "boo", "b": {"c": "roma", "d": "once", "e": {"f": "foo", "g": "godad"}}}),
    ])
def test_merge_dicts(dict_a, dict_b, expected):
    output = merge_dicts(dict_a, dict_b)
    assert DeepDiff(output, expected) == {}
    
