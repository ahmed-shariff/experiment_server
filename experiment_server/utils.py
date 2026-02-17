from pathlib import Path
from typing import Callable, Union, Optional, Any
from loguru import logger
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


class FileModifiedWatcher(PatternMatchingEventHandler):
    def __init__(self, config_file: Union[Path, str], callback:Callable) -> None:
        super().__init__(patterns=[str(config_file)])
        self._observer = Observer()
        self._observer.schedule(self, path=Path(config_file).parent, recursive=False)
        self._observer.start()
        self._callback = callback

    def on_modified(self, event):
        logger.info(f"File modified: {event.src_path}")
        try:
            self._callback()
        except:
            logger.error("Callback after file modified failed")

    def end_watch(self):
        self._observer.stop()
        self._observer.join()

class ExperimentServerException(Exception):
    def __init__(self, message:Optional[str]=None, *args: Any, **kwargs: Any) -> None:
        self.message = message

        if message is not None:
            super().__init__(message, *args, **kwargs)
        else:
            super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        if self.message is not None:
            return self.message
        return super().__str__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r})"


class ExperimentServerConfigurationException(ExperimentServerException):
    def __init__(self, message:Optional[str]=None, *args:Any, **kwargs:Any) -> None:
        super().__init__(message, *args, **kwargs)


# From: https://cs.uwaterloo.ca/~dmasson/tools/latin_square/
# Based on "Bradley, J. V. Complete counterbalancing of immediate sequential effects in a Latin square design. J. Amer. Statist. Ass.,.1958, 53, 525-528. "
def balanced_latin_square(number_of_conditions):
    latin_square = []

    for participant_idx in range(number_of_conditions):
        j = 0
        h = 0

        trials = []
        for trial_idx in range(number_of_conditions):
            val = 0
            if trial_idx < 2 or trial_idx % 2 != 0:
                val = j
                j += 1
            else:
                val = number_of_conditions - h -1
                h += 1

            trials.append((val + participant_idx) % number_of_conditions)

        latin_square.append(trials)
        if number_of_conditions % 2 != 0:
            latin_square.append(trials[::-1])

    return latin_square


def merge_dicts(dict_a, dict_b):
    """
    Merge the values from dict_a and dict_b recursively. If there is a conflict, 
    the value in dict_a will be selected.
    """
    new_dict = {}
    keys = []

    if isinstance(dict_a, dict):
        keys += list(dict_a.keys())
    if isinstance(dict_b, dict):
        keys += list(dict_b.keys())

    for k in keys:
        try:
            value_a = dict_a[k]
        except (TypeError, KeyError):
            value_a = None

        try:
            value_b = dict_b[k]
        except (TypeError, KeyError):
            value_b = None

        value_a_is_dict = isinstance(value_a, dict)
        value_b_is_dict = isinstance(value_b, dict)

        if value_a_is_dict and value_b_is_dict:
            value = merge_dicts(value_a, value_b)
        else: # If only one is a dict, still it's treated the same, the value a is priority
            value = value_a if value_a is not None else value_b  # Whichever is not None, prioritizing value_a

        new_dict[k] = value

    return new_dict


def new_config_file(new_file_location):
    """Create a new config file.

    If parameter does not end with `.toml` assums it is a directory and create a directory.
    If parameter is directory, creates a file named `new_config.toml` in the directory.
    If parents do not exists, create them all!.
    """
    out_location = Path(new_file_location)

    if out_location.suffix != ".toml":
        if out_location.exists():
            logger.error(f"{out_location} exists and does not end with `.toml`")
            return
        else:
            out_location.mkdir(parents=True, exist_ok=True)

    if out_location.is_dir():
        out_location = out_location / "new_config.toml"

    if out_location.exists():
        logger.error(f"{out_location} already exists!")
        return

    with open(Path(__file__).parent.parent / "sample_config.toml", "r") as in_f:
        with open(out_location, "w") as out_f:
            out_f.writelines(in_f.readlines())

    logger.info(f"New config at: {out_location}")

