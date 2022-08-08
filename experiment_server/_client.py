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
        return self._post("move_to_next")

    def get_config(self) -> Tuple[bool, dict]:
        return self._get("config")

    def server_is_active(self) -> Tuple[bool, dict]:
        return self._get("active")
    
    def get_total_steps_count(self) -> Tuple[bool, dict]:
        return self._get("itemsCount")

    def move_to_step(self, step: int) -> Tuple[bool, dict]:
        assert isinstance(step, int), "`step` should be a int"
        return self._post(f"move/{step}")

    def change_participant_index(self, step: int) -> Tuple[bool, dict]:
        assert isinstance(step, int), "`step` should be a int"
        return self._post(f"change_participant_index/{step}")

    def shutdown(self) -> Tuple[bool, dict]:
        return self._post("shutdown")
