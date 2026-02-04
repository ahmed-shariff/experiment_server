"""CLI."""

import click
from click.core import ParameterSource
from loguru import logger
from pathlib import Path
from click_aliases import ClickAliasedGroup

from experiment_server._server import _server
from experiment_server._ui import ExperimentTextualApp
from experiment_server._process_config import verify_config
from experiment_server._api import _generate_config_json
from experiment_server.utils import ExperimentServerExcetion


@click.group(cls=ClickAliasedGroup)
def cli():
    pass


def _ask_default_participant_index_callback(ctx:click.Context, _, flag_value:bool):
    """Callback used to process the ask-default-participant-index in the run."""
    if not flag_value:
        return

    if ctx.get_parameter_source("default_participant_index") != ParameterSource.DEFAULT:
        logger.warning("The value passed for `default_participant_index` (-i) is being overwritten with `ask_default_participant_index` (-a).")
    if "default_participant_index" in ctx.params:
        default_value = ctx.params["default_participant_index"]
    else:
        default_value = 1
    ctx.params["default_participant_index"] = click.prompt("Default participant index",
                                                           default_value,
                                                           type=click.IntRange(min=1, max_open=True))


@cli.command(aliases=["r"])
@click.argument("config-file")
# NOTE: making this eager to make sure the data is set for the ask callback
@click.option("-i", "--default-participant-index", default=1, type=click.IntRange(min=1, max_open=True), is_eager=True)
@click.option("-h", "--host", default='127.0.0.1')
@click.option("-p", "--port", default='5000')
@click.option("-a", "--ask-default-participant-index", is_flag=True, default=False, expose_value=False, callback=_ask_default_participant_index_callback)
def run(default_participant_index, config_file, host, port):
    """Launch server with the `config-file` used to setup the configurations"""
    _server(default_participant_index=default_participant_index if default_participant_index > 0 else None, host=host, port=port, config_file=config_file)


@cli.command(aliases=["v", "verify"])
@click.argument("config-file", type=click.Path())
def verify_config_file(config_file):
    """Verify if the config-file provided is valid"""
    verify_config(f=config_file)


@cli.command(aliases=["g", "generate"])
@click.argument("config-file", type=click.Path())
@click.option("-i", "--participant-index", default=None, type=int)
@click.option("-r", "--participant-range", default=None, type=int)
@click.option("-d", "--out-dir", default=None, type=click.Path(file_okay=False))
def generate_config_json(config_file, participant_index, participant_range, out_dir):
    """Generate json config files after processing config-file for participant_index or 
    till participant_range. If `out_location` is passed, it is expected to be a directory.
    If not passed will write out the config's to stdout, one line per participant.
    """
    if participant_index is None and participant_range is None:
        logger.error("Both `participant-index` and `participant-range` cannot be empty.")
        return
    elif participant_index is not None and participant_range is not None:
        logger.error("Both `participant-index` and `participant-range` provided. Ignoring `participant-index`.")

    with logger.catch(ExperimentServerExcetion, reraise=False):
        _generate_config_json(config_file=config_file, participant_indices=range(1, participant_range + 1) if participant_range is not None else [participant_index, ], out_dir=out_dir)


@cli.command(aliases=["n", "new"])
@click.argument("new-file-location")
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

@cli.command(aliases=["ui"])
@click.argument("config-file")
def ui(config_file):
    app = ExperimentTextualApp(config_file, css_path=Path(__file__).parent / "static" / "css" / "app.tcss", watch_css=True)
    app.run()
