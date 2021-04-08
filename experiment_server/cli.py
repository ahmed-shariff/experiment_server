"""CLI."""

import click

from ._main import _init_api

@click.command()
@click.argument("config-file")
@click.option("-h", "--host", default='127.0.0.1')
@click.option("-p", "--port", default='5000')
def _main(config_file, host, port):
    """Launch server with the `config-file` used to setup the configurations"""
    _init_api(host, port, config_file)


# _main.add_command(test)
# _main.add_command(server)
    

if __name__ == '__main__':  # pragma: no cover
    _main()
