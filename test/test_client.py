import time
import requests
import pytest
from experiment_server import Client
from experiment_server._main import server_process
from experiment_server._process_config import process_config_file
from .fixtures import config_file, participant_index


@pytest.fixture(scope="class", autouse=True)
def server(config_file, participant_index):
    p = server_process(config_file=config_file, participant_index=participant_index)
    p.start()
    for i in range(10) :
        time.sleep(0.1)
        try:
            if requests.get("http://127.0.0.1:5000/active").status_code == 200:
                break
        except requests.ConnectionError:
            continue

    yield
    p.kill()
    p.join()


# TODO: Convert to tornado.testing.AsyncHTTPTestCase
class TestClient:
    @pytest.fixture(scope="class")
    def client(self):
        return Client("127.0.0.1", "5000")

    @pytest.fixture(scope="class")
    def exp_config(self, config_file, participant_index):
        return process_config_file(config_file, participant_index)

    def test_is_active(self, client):
        ret, out = client.server_is_active()
        assert ret

    def test_block_0_config(self, client):
        ret, out = client.get_config()
        assert not ret

    def test_block_through_all(self, client, exp_config):
        for idx, c in enumerate(exp_config):
            ret, out = client.move_to_next()
            assert ret, f"block {idx}"
            assert out["name"] == c["name"], f"block {idx}"
            ret, out = client.get_config()
            assert ret, f"block {idx}"
            assert out == c["config"], f"block {idx}"
            
    def test_get_total_block_count(self, client, exp_config):
        ret, out = client.get_total_blocks_count()
        assert ret
        assert out == len(exp_config)

    def test_move_to_block_correct(self, client, exp_config):
        ret, out = client.move_to_block(3)
        assert ret
        assert out == 3
        ret, out = client.get_config()
        assert ret
        assert out == exp_config[3]["config"]

    def test_move_to_block_fail_outside_range(self, client, exp_config):
        ret, out = client.move_to_block(len(exp_config) + 4)
        assert not ret

    def test_move_to_block_fail_empty(self, client):
        with pytest.raises(AssertionError) as exc_info:
            client.move_to_block(None)

    def test_move_to_block_fail_non_number(self, client):
        with pytest.raises(AssertionError) as exc_info:
            client.move_to_block("ha")

    def test_change_participant_index_fail_empty(self, client):
        with pytest.raises(AssertionError) as exc_info:
            client.change_participant_index(None)

    def test_change_participant_index_fail_non_number(self, client):
        with pytest.raises(AssertionError) as exc_info:
            client.change_participant_index(None)

    def test_change_participant_index(self, client, participant_index):
        ret, out = client.change_participant_index(0)

    def test_shutdown(self, client):
        ret, out = client.shutdown()
        assert ret
        with pytest.raises(requests.ConnectionError):
            client.server_is_active()

