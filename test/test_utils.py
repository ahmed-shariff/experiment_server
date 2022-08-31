import pytest
from experiment_server.utils import FileModifiedWatcher, merge_dicts
from deepdiff import DeepDiff
import time
from .fixtures import caplog


@pytest.mark.parametrize(
    "dict_a, dict_b, expected", [
        ({"a": "boo", "b": "hoo"}, {"a": "boo", "b": "roo"}, {"a": "boo", "b": "hoo"}),
        ({"a": "boo"}, {"a": "boo", "b": "roo"}, {"a": "boo", "b": "roo"}),
        ({"a": "boo", "b": "hoo"}, {"a": "boo"}, {"a": "boo", "b": "hoo"}),
        ({'name': 'a', 'extends': 'b', 'param1': '0', 'block_idx': 0},
         {'name': 'b', 'extends': 'c', 'param2': '0', 'block_idx': 1, 'param3': '0'},
         {'name': 'a', 'extends': 'b', 'param1': '0', 'param2': '0', 'param3': '0', 'block_idx': 0}),
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
    

def test_FileModifiedWatcher(tmp_path, caplog):
    config_file = tmp_path / "test_config_file.toml"

    with open(config_file, "w") as f:
        f.write("before watchdog started")

    class MockCallable:
        called = False
        def __call__(self) -> None:
            print("asdfasdf")
            self.called = True

    mocked_callback = MockCallable()

    _watchdog = FileModifiedWatcher(config_file, mocked_callback)

    with open(config_file, "a") as f:
        f.write("after watchdog started")

    timeout_at = time.time() + 5

    try:
        while not mocked_callback.called and time.time() < timeout_at:
            time.sleep(0.1)

        assert mocked_callback.called
        assert str(config_file.name) in caplog.text
    finally:
        _watchdog.end_watch()

