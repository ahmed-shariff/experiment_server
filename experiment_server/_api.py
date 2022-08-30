from typing import Any, Dict, Iterable, List, Union

from loguru import logger
from experiment_server._process_config import process_config_file
from pathlib import Path
import json

from experiment_server.utils import ExperimentServerExcetion


class GlobalState:
    def __init__(self, config_file, participant_index):
        self.config_file = config_file
        self.change_participant_index(participant_index)

    def change_participant_index(self, participant_index):
        self._participant_index = participant_index
        self._block_id = None
        self.block = None
        self.config = process_config_file(self.config_file, participant_index)

    def set_block(self, block_id):
        self._block_id = block_id
        self.block = self.config[block_id]

    def move_to_next_block(self):
        self.set_block(self._block_id + 1)


class Experiment:
    """Load and manage experiemnt from a local file."""
    def __init__(self, config_file:str, participant_index:int) -> None:
        self.global_state = GlobalState(config_file, participant_index)

    def move_to_next(self) -> None:
        """Moves the pointer to the current block to the next block."""
        return self.global_state.move_to_next_block()

    def get_config(self) -> Union[Dict[str, Any], None]:
        """Return the config of the current block. 
        If the experiment has not started (`move_to_next` has not
        been called atleast once), this will return `None`."""
        if self.global_state is None:
            return None
        else:
            return self.global_state.block["config"]

    def get_blocks_count(self) -> int:
        """Return the total number of blocks."""
        return len(self.global_state.config)

    def get_all_configs(self) -> List[dict]:
        """Return all configs in order for the configured participant index."""
        return [c["config"] for c in self.global_state.config]

    def move_to_block(self, block_id: int) -> None:
        """Move the pointer to the current block to the block in index 
        `block_id` in the list of blocks"""
        assert isinstance(block_id, int), "`block` should be an int"
        return self.global_state.set_block(block_id)

    def change_participant_index(self, participant_index: int) -> None:
        """Change the index of the participant to"""
        assert isinstance(participant_index, int), "`block` should be a int"
        return self.global_state.change_participant_index(participant_index)


def write_to_file(config_file: Union[str, Path], participant_indices:Iterable[int], out_file_location: Union[str, Path, None] = None) -> None:
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
