__version__ = '0.2'

import logging
from loguru import logger

class __InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

logging.basicConfig(handlers=[__InterceptHandler()], level=0)

from experiment_server._main import server_process
from experiment_server._client import Client
from experiment_server._api import Experiment

__all__ = [server_process, Client, Experiment]
