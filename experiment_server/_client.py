import json
from typing import Tuple, Union
import requests

from experiment_server.utils import ExperimentServerExcetion


class Client:
    def __init__(self, server_host:str ="127.0.0.1", server_port:Union[str, int]="5000") -> None:
        self._server_url = f"http://{server_host}:{server_port}"

    def _request(self, end_point:str, verb:str) -> Tuple[bool, dict]:
        url = self._server_url + f"/api/{end_point}"
        if verb == "GET":
            r = requests.get(url)
        elif verb == "POST":
            r = requests.post(url)
        elif verb == "PUT":
            r = requests.put(url)
        else:
            raise ExperimentServerExcetion("huh?")

        if r.status_code != 200:
            return False, {"message": f"status {r.status_code} with text: {r.text}"}
        return True, json.loads(r.text) if len(r.text) > 0 else ""
    
    def _get(self, end_point:str) -> Tuple[bool, dict]:
        return self._request(end_point, "GET")

    def _post(self, end_point:str) -> Tuple[bool, dict]:
        return self._request(end_point, "POST")

    def _put(self, end_point:str) -> Tuple[bool, dict]:
        return self._request(end_point, "PUT")

    def move_to_next(self, participant_index:int|None=None) -> Tuple[bool, dict]:
        """ Moves the pointer to the current block to the next block for `participant_index`.
        if `participant_index` is None, seld.default_participant_index is used."""
        url = _process_participant_index("move-to-next", participant_index)
        return self._post(url)

    def get_config(self, participant_index:int|None=None) -> Tuple[bool, dict]:
        """Return the config of the current block for `participant_index`. 
        if `participant_index` is None, seld.default_participant_index is used.
        If the experiment has not started (`move_to_next` has not
        been called atleast once), this will return `None`."""
        url = _process_participant_index("config", participant_index)
        return self._get(url)

    def server_is_active(self, participant_index:int|None=None) -> Tuple[bool, dict]:
        """Returns the status for `participant-id`, if
        `participant-id` is not provided, will return the status of
        the default participant. Will be `false` if the participant
        was just initialized or the participant has gone through all
        blocks. To initialize the participant's status (or move to a
        given block), use the `move-to-next` or `move-to-block`"""
        url = _process_participant_index("active", participant_index)
        return self._get(url)
    
    def get_blocks_count(self, participant_index:int|None=None) -> Tuple[bool, dict]:
        """Return the number of blocks in the configuration
        loaded. For a given config, the `blocks-count` will be the
        same for all participants."""
        url = _process_participant_index("blocks-count", participant_index)
        return self._get(url)

    def get_all_configs(self, participant_index:int|None=None) -> Tuple[bool, dict]:
        """Returns all the configs as a list for the `participant_index`,
        if `participant_index` is not provided, returns the configs for
        the default participant. This is akin having all the results
        from calling `config` for each block in one list."""
        url = _process_participant_index("all-configs", participant_index)
        return self._get(url)

    def move_to_block(self, block_id:int, participant_index:int|None=None) -> Tuple[bool, dict]:
        """Move `participant-id` to the block number indicated by
        `block_id`, if `participant_index` is not provided, move the
        default participant to the block number indicated by
        `block_id`. If the participant was not initialized (`active`
        is false), will make be marked as active (`active` will be set
        to true). Will fail if the `block_id` is below 0 or above the
        length of the config."""
        assert isinstance(block_id, int), "`block` should be a int"
        url = _process_participant_index("move-to-block", participant_index)
        return self._post(f"{url}/{block_id}")

    def new_participant(self) -> Tuple[bool, dict]:
        """Adds a new participant and returns the new
        participant_index. The new participant_index will be the largest
        current participant_index +1."""
        return self._put("new-participant");

    def add_participant(self, participant_index:int) -> Tuple[bool, dict]:
        """Add a new participant with `participant_index`. If there is already
        a participant with the `participant_index`, this will fail. """
        assert participant_index is not None
        url = _process_participant_index("add-participant", participant_index)
        return self._put(url);

    def shutdown(self) -> Tuple[bool, dict]:
        """Shuts down the server."""
        return self._post("shutdown")


def _process_participant_index(url:str, participant_index:int|None) -> str:
    if participant_index is not None:
        assert isinstance(participant_index, int), "`participant_index` should be a int"
        url += f"/{participant_index}"
    return url
