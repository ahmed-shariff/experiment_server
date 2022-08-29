import json
from typing import Tuple, Union
import requests


class Client:
    def __init__(self, server_host:str ="127.0.0.1", server_port:Union[str, int]="5000") -> None:
        self._server_url = f"http://{server_host}:{server_port}"

    def _request(self, end_point:str, get:bool=True) -> Tuple[bool, dict]:
        url = self._server_url + f"/api/{end_point}"
        if get:
            r = requests.get(url)
        else:
            r = requests.post(url)

        if r.status_code != 200:
            return False, {"message": f"status {r.status_code} with text: {r.text}"}
        return True, json.loads(r.text) if len(r.text) > 0 else ""
    
    def _get(self, end_point:str) -> Tuple[bool, dict]:
        return self._request(end_point, True)

    def _post(self, end_point:str) -> Tuple[bool, dict]:
        return self._request(end_point, False)    

    def move_to_next(self) -> Tuple[bool, dict]:
        return self._post("move-to-next")

    def get_config(self) -> Tuple[bool, dict]:
        return self._get("config")

    def server_is_active(self) -> Tuple[bool, dict]:
        return self._get("active")
    
    def get_blocks_count(self) -> Tuple[bool, dict]:
        return self._get("blocks-count")

    def move_to_block(self, block_id: int) -> Tuple[bool, dict]:
        assert isinstance(block_id, int), "`block` should be a int"
        return self._post(f"move-to-block/{block_id}")

    def change_participant_index(self, participant_index: int) -> Tuple[bool, dict]:
        assert isinstance(participant_index, int), "`block` should be a int"
        return self._post(f"change-participant-index/{participant_index}")

    def shutdown(self) -> Tuple[bool, dict]:
        return self._post("shutdown")
