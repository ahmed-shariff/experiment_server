"""CLI."""

import click
import log

from ._main import main, _init_api

@click.group()
def _main():
    log.init()


@click.command()
def test():
    main()


@click.command()
@click.option("-h", "--host", default='127.0.0.1')
@click.option("-p", "--port", default='5000')
@click.option("-c", "--config-file", default="config_file.txt")
def server(host, port, config_file):
    _init_api(host, port, config_file)


# _main.add_command(test)
_main.add_command(server)
    

if __name__ == '__main__':  # pragma: no cover
    _main()
