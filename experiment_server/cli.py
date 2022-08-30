"""CLI."""

import click

from experiment_server._server import _server
from experiment_server._process_config import verify_config

@click.group()
def cli():
    pass


@cli.command()
@click.argument("config-file")
@click.option("-i", "--participant-index", default=0)
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
