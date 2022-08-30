"""CLI."""

import click

from experiment_server._server import _server
from experiment_server._process_config import verify_config
from experiment_server._api import write_to_file
from loguru import logger

from experiment_server.utils import ExperimentServerExcetion

@click.group()
def cli():
    pass


@cli.command()
@click.argument("config-file")
@click.option("-i", "--participant-index", default=0, type=int)
@click.option("-h", "--host", default='127.0.0.1')
@click.option("-p", "--port", default='5000')
def run(participant_index, config_file, host, port):
    """Launch server with the `config-file` used to setup the configurations"""
    _server(participant_index if participant_index > 0 else None, host, port, config_file)


@cli.command()
@click.argument("config-file", type=click.Path())
def verify_config_file(config_file):
    """Verify if the config-file provided is valid"""
    verify_config(config_file)


@cli.command()
@click.argument("config-file", type=click.Path())
@click.option("-i", "--participant-index", default=None, type=int)
@click.option("-r", "--participant-range", default=None, type=int)
@click.option("-l", "--out-file-location", default=None, type=click.Path(file_okay=False))
def generate_config_json(config_file, participant_index, participant_range, out_file_location):
    """Generate json config files after processing config-file for participant_index or 
    till participant_range."""
    if participant_index is None and participant_range is None:
        logger.error("Both `participant-index` and `participant-range` cannot be empty.")
        return
    elif participant_index is not None and participant_range is not None:
        logger.error("Both `participant-index` and `participant-range` provided. Ignoring `participant-index`.")

    with logger.catch(ExperimentServerExcetion, reraise=False):
        write_to_file(config_file, range(1, participant_range + 1) if participant_range is not None else [participant_index, ], out_file_location)
