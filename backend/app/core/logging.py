import logging
import sys
from logging.config import dictConfig


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        },
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": sys.stdout,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["stdout"],
    },
    "loggers": {
        "uvicorn": {"level": "INFO", "handlers": ["stdout"], "propagate": False},
        "uvicorn.error": {"level": "INFO", "handlers": ["stdout"], "propagate": False},
        "uvicorn.access": {"level": "INFO", "handlers": ["stdout"], "propagate": False},
        "app": {"level": "INFO", "handlers": ["stdout"], "propagate": False},
    },
}


def configure_logging() -> None:
    dictConfig(LOGGING_CONFIG)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
