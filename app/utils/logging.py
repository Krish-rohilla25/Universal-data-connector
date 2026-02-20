"""Logging setup for the application."""

import logging
import sys


def configure_logging(debug: bool = False) -> None:
    """Configure root logger with a readable format.

    We send everything to stdout so Docker / container platforms can pick it up
    without any extra configuration.
    """
    level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Quieten noisy libraries a bit
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
