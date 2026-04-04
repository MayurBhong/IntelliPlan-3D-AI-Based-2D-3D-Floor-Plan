# ═══════════════════════════════════════════════════════════════
# utils/logger.py
# Centralised logging for IntelliPlan·3D backend
# ═══════════════════════════════════════════════════════════════

import logging
import sys
from datetime import datetime


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger with consistent formatting.
    All modules should call:  logger = get_logger(__name__)
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s  [%(levelname)-8s]  %(name)s — %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

    return logger


# Module-level convenience logger
log = get_logger("intelliplan")
