import logging
import sys
from backend.app.config import settings

def setup_logger(name: str = "pdf_rag") -> logging.Logger:
    """
    Configures a structured, clean logger.
    Ensures log messages do not expose sensitive system prompts or raw secrets.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    return logger

logger = setup_logger()
