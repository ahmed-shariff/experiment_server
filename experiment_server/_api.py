from typing import Any, Dict, Iterable, List, Union

from loguru import logger
from experiment_server._process_config import process_config_file
from pathlib import Path
import json

from experiment_server.utils import ExperimentServerExcetion, FileModifiedWatcher


class ParticipantState:
    def __init__(self, config, participant_index, active):
        self.participant_index = participant_index
        self._block_id: int = -1
        self.config = config
        self.active = active  # if not started or has ended, then this will be False

    @property
    def block_id(self) -> int:
        return self._block_id

    @block_id.setter
    def block_id(self, block_id: int):
        if block_id < 0:
            raise AttributeError("Block id cannot be below 0")
        elif block_id >= len(self.config):
            self.active = False
        else:
            self.active = True
        self._block_id = block_id

    @property
    def block(self) -> Dict[str, Any]:
        return self.config[self.block_id]

    def move_to_next_block(self):
        self.block_id += 1
        if self.block_id >= 0 and self.block_id < len(self.config):
            self.active = True

    def status_string(self):
        return f'Participant index: {self.participant_index}    \nBlock: {self._block_id} / {len(self.config)}    \n Name: {self.block["name"] if self.block is not None else "N/A"}'


class Experiment:
    """Load and manage experiemnt from a local file."""
    def __init__(self, config_file:str, default_participant_index:int=0) -> None:
        self.global_state: Dict[int, ParticipantState] = {}
        self.default_participant_index = default_participant_index
        self.watchdog = FileModifiedWatcher(config_file, self._config_file_modified_callback)
        self.config_file = config_file

        if default_participant_index not in self.global_state:
            self.global_state[default_participant_index] = ParticipantState(process_config_file(config_file, default_participant_index),
                                                                            default_participant_index,
                                                                            False)

    def _config_file_modified_callback(self):
        logger.info("Reloading config")
        for participantState in self.global_state.values():
            config = process_config_file(self.config_file, participantState.participant_index)
            participantState.config = config

    def get_next_participant(self) -> int:
        """Return the index of the next participant."""
        new_participant_index = max(self.global_state.keys()) + 1
        self.add_participant_index(new_participant_index)
        return new_participant_index

    def add_participant_index(self, participant_index) -> bool:
        """Add a participant with `participant_index`.
        If `participant_index` already exists, returns False, else return True"""
        if participant_index in self.global_state:
            return False
        self.global_state[participant_index] = ParticipantState(process_config_file(self.config_file, participant_index),
                                                                participant_index,
                                                                False)
        return True

    def get_state(self, participant_index:int|None=None):
        if participant_index is None:
            participant_index = self.default_participant_index
        return self.global_state[participant_index].active

    def move_to_next(self, participant_index:int|None=None) -> str:
        """Moves the pointer to the current block to the next block for `participant_index`.
        if `participant_index` is None, seld.default_participant_index is used.
        """
        if participant_index is None:
            participant_index = self.default_participant_index
        self.global_state[participant_index].move_to_next_block()
        return self.global_state[participant_index].block["name"]

    def get_config(self, participant_index:int|None=None) -> Union[Dict[str, Any], None]:
        """Return the config of the current block for `participant_index`. 
        if `participant_index` is None, seld.default_participant_index is used.
        If the experiment has not started (`move_to_next` has not
        been called atleast once), this will return `None`."""
        if participant_index is None:
            participant_index = self.default_participant_index
        if not self.global_state[participant_index].active:
            return None
        else:
            return self.global_state[participant_index].block["config"]

    def get_blocks_count(self) -> int:
        """Return the total number of blocks."""
        # NOTE:the config length is the same for all participants
        return len(next(iter(self.global_state.values())).config)

    def get_all_configs(self, participant_index:int|None=None) -> List[dict]:
        """Return all configs in order for `participant_index`.
        if `participant_index` is None, seld.default_participant_index is used.
        """
        if participant_index is None:
            participant_index = self.default_participant_index
        return [c["config"] for c in self.global_state[participant_index].config]

    def move_to_block(self, block_id: int, participant_index:int|None=None) -> Union[str, None]:
        """For `participant_index` move the pointer to the current
        block to the block in index a `block_id` in the list of
        blocks. If `participant_index` is None, seld.default_participant_index is used.
        """
        assert isinstance(block_id, int), "`block` should be an int"
        if participant_index is None:
            participant_index = self.default_participant_index
        self.global_state[participant_index].block_id = block_id
        return self.global_state[participant_index].block["name"]


def write_to_file(config_file: Union[str, Path], participant_indices:Iterable[int], out_file_location: Union[str, Path, None] = None) -> None:
    """
    Write out the json files from the `config_file` for participants in `participant_indices`
    in the `out_file_location`. The `out_file_location` should be a directory.
    """
    if out_file_location is None:
        out_file_location = Path(config_file).parent
    elif not Path(out_file_location).is_dir():
        raise ExperimentServerExcetion(f"`out_file_location` should be a directory. Got {out_file_location}")

    out_files = []
    for participant_index in participant_indices:
        config = process_config_file(config_file, participant_index)
        out_file = Path(out_file_location) / f"{Path(config_file).stem}-participant_{participant_index}.json"
        out_files.append(out_file)

        with open(out_file, "w") as f:
            json.dump([c["config"] for c in config], f, indent=2)

    logger.info("Generated files: \n" + "\n".join([str(f) for f in out_files]))
