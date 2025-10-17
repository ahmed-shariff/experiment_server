from sys import stdout
from typing import Any, Dict, Iterable, List, Union

from loguru import logger
from experiment_server._process_config import process_config_file
from pathlib import Path
import json

from experiment_server.utils import ExperimentServerExcetion, FileModifiedWatcher


class ParticipantState:
    def __init__(self, config, participant_index, active):
        """
        Track a single participant's progress through an experiment configuration.

        Args:
            config (List[Dict[str, Any]]): Ordered list of block dictionaries for this participant.
            participant_index (int): 1-based participant index.
            active (bool): True if participant is currently between START and END (inclusive of blocks).
        """
        self.participant_index = participant_index
        self._block_id: int = -1
        self.config = config
        self.active = active  # if not started or has ended, then this will be False

    @property
    def block_id(self) -> int:
        """Current zero-based index of the active block, -1 if before START, len(config) if after END."""
        return self._block_id

    @block_id.setter
    def block_id(self, block_id: int):
        """
        Set the current block index and update the active flag.

        If block_id < 0 -> mark as not active (before start).
        If block_id >= len(config) -> mark as not active (after end).
        Otherwise active = True.
        An assertion ensures consistency between block_id and the block's own 'config.block_id'.
        """
        if block_id < 0:
            self._block_id = -1
            self.active = False
        elif block_id >= len(self.config):
            self._block_id = len(self.config)
            self.active = False
        else:
            self.active = True
            self._block_id = block_id
        if self.active:
            assert self._block_id == self.config[self._block_id]["config"]["block_id"]

    @property
    def block(self) -> Dict[str, Any]|None:
        """Return the current block dict or None if before START or after END."""
        if self.block_id >= len(self.config) or self.block_id < 0:
            return None
        return self.config[self.block_id]

    @property
    def block_name(self) -> str:
        """Human-readable block position: 'START', 'END' or the current block name."""
        if self.block_id >= len(self.config):
            return "END"
        if self.block_id < 0:
            return "START"
        return self.config[self.block_id]["name"]

    def move_to_next_block(self) -> str:
        """Advance to the next block and return its block_name."""
        self.block_id += 1
        return self.block_name

    def status_string(self) -> str:
        """Single-line status summary suitable for logs or simple UIs."""
        name = self.block["name"] if self.block is not None else "N/A"
        return f'Participant index: {self.participant_index}    \nBlock: {self._block_id} / {len(self.config)}    \n Name: {name}'


class Experiment:
    """Load and manage an experiment configuration file and participant states."""

    def __init__(self, config_file: str, default_participant_index: int = 1) -> None:
        """
        Initialize experiment state and watch the configuration file for changes.

        Args:
            config_file (str): Path to the TOML configuration file.
            default_participant_index (int): Default 1-based index used when none is provided.
        """
        assert default_participant_index > 0, "Default participant index should be >0"
        self.global_state: Dict[int, ParticipantState] = {}
        self.default_participant_index = default_participant_index
        self.watchdog = FileModifiedWatcher(config_file, self._config_file_modified_callback)
        self.config_file = config_file

        if default_participant_index not in self.global_state:
            self.global_state[default_participant_index] = ParticipantState(
                process_config_file(config_file, default_participant_index),
                default_participant_index,
                False,
            )

    def _config_file_modified_callback(self):
        """Reload configurations for all known participants when the file changes."""
        logger.info("Reloading config")
        for participantState in self.global_state.values():
            config = process_config_file(self.config_file, participantState.participant_index)
            participantState.config = config

    def get_next_participant(self) -> int:
        """Allocate and return the next participant index (max existing + 1)."""
        new_participant_index = max(self.global_state.keys()) + 1
        self.add_participant_index(new_participant_index)
        return new_participant_index

    def add_participant_index(self, participant_index) -> bool:
        """
        Add a participant by index.

        Returns True if added, False if the index already exists.
        """
        if participant_index in self.global_state:
            return False
        self.global_state[participant_index] = ParticipantState(
            process_config_file(self.config_file, participant_index),
            participant_index,
            False,
        )
        return True

    def get_participant_state(self, participant_index) -> ParticipantState:
        """
        Return the ParticipantState for the given index.

        If participant_index is None, uses the default. Raises ExperimentServerExcetion if not present.
        """
        if participant_index is None:
            participant_index = self.default_participant_index
        if participant_index not in self.global_state:
            raise ExperimentServerExcetion(f"participant with index {participant_index} is not set. Consider using `add_participant_index`")
        return self.global_state[participant_index]

    def get_state(self, participant_index:int|None=None) -> bool:
        """Return whether the participant is active."""
        if participant_index is None:
            participant_index = self.default_participant_index
        return self.global_state[participant_index].active

    def move_to_next(self, participant_index:int|None=None) -> str:
        """Advance the participant to the next block and return the new block_name."""
        if participant_index is None:
            participant_index = self.default_participant_index
        return self.global_state[participant_index].move_to_next_block()

    def get_config(self, participant_index:int|None=None) -> Union[Dict[str, Any], None]:
        """
        Return the current block's config for the participant, or None if experiment not started or finished.
        """
        if participant_index is None:
            participant_index = self.default_participant_index
        block = self.global_state[participant_index].block
        if block is None:
            return None
        return block["config"]

    def reset_participant(self, participant_index:int|None=None) -> bool:
        """Reload the participant's configuration from file and replace their stored config."""
        if participant_index is None:
            participant_index = self.default_participant_index
        self.global_state[participant_index].config = process_config_file(self.config_file, participant_index)
        return True

    def get_blocks_count(self, participant_index:int|None=None) -> int:
        """Return the number of blocks for the participant."""
        if participant_index is None:
            participant_index = self.default_participant_index
        return len(self.global_state[participant_index].config)

    def get_all_configs(self, participant_index:int|None=None) -> List[dict]:
        """Return the list of all block 'config' dicts for the participant in order."""
        if participant_index is None:
            participant_index = self.default_participant_index
        return [c["config"] for c in self.global_state[participant_index].config]

    def move_to_block(self, block_id: int, participant_index:int|None=None) -> str:
        """
        Move the participant pointer to a specific block index and return its block_name.

        block_id must be an integer.
        """
        assert isinstance(block_id, int), "`block` should be an int"
        if participant_index is None:
            participant_index = self.default_participant_index
        self.global_state[participant_index].block_id = block_id
        return self.global_state[participant_index].block_name

    def move_all_to_block(self, block_id: int) -> str:
        """
        Move every participant's pointer to `block_id`.

        Returns the block_name of the first participant after the move.
        """
        assert isinstance(block_id, int), "`block` should be an int"
        for participantState in self.global_state.values():
            participantState.block_id = block_id
        return list(self.global_state.values())[0].block_name


def _generate_config_json(config_file: Union[str, Path], participant_indices: Iterable[int], out_dir: Union[str, Path, None]=None) -> None:
    """
    Emit the resolved JSON configuration for the given participant indices.

    If out_dir is provided, writes one file per participant named "<config_stem>-participant_<i>.json".
    If out_dir is None, writes each participant's JSON to stdout (one line per participant).

    Args:
        config_file: Path to the TOML configuration file.
        participant_indices: Iterable of 1-based participant indices to generate.
        out_dir: Optional directory to write files into. Created if missing.
    """
    if out_dir is not None:
        out_dir = Path(out_dir)
        if not out_dir.exists():
            logger.info(f"Creating direcotry {out_dir}")
            out_dir.mkdir(parents=True)
        elif not out_dir.is_dir():
            raise ExperimentServerExcetion(f"`out_file_location` should be a directory. Got {out_dir}")

    out_files = []
    for participant_index in participant_indices:
        config = process_config_file(config_file, participant_index, supress_message=True)
        if out_dir is not None:
            out_file = Path(out_dir) / f"{Path(config_file).stem}-participant_{participant_index}.json"
            out_files.append(out_file)

            with open(out_file, "w") as f:
                json.dump([c["config"] for c in config], f, indent=2)
        else:
            stdout.write(json.dumps([c["config"] for c in config]))

    if len(out_files) != 0:
        logger.info("Generated files: \n" + "\n".join([str(f) for f in out_files]))
