"""CLI."""

import click

from ._main import _init_api

@click.group()
def _main():
    pass


@_main.command()
@click.option("-h", "--host", default='127.0.0.1')
@click.option("-p", "--port", default='5000')
@click.option("-c", "--config-file", default="config_file.txt")
def server(host, port, config_file):
    _init_api(host, port, config_file)


# _main.add_command(test)
# _main.add_command(server)
    

if __name__ == '__main__':  # pragma: no cover
    _main()
