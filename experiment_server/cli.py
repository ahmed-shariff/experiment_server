"""CLI."""

import click

from experiment_server._main import _main
from experiment_server._process_config import verify_config

@click.group()
def cli():
    pass


@cli.command()
@click.argument("config-file")
@click.option("-h", "--host", default='127.0.0.1')
@click.option("-p", "--port", default='5000')
def run(config_file, host, port):
    """Launch server with the `config-file` used to setup the configurations"""
    _main(None, host, port, config_file)


@cli.command()
@click.argument("config-file", type=click.Path())
def verify_config_file(config_file):
    """Verify if the config-file provided is valid"""
    verify_config(config_file)
    
# _main.add_command(test)
# _main.add_command(server)
    

if __name__ == '__main__':  # pragma: no cover
    _main()
