# src/utils.py

import logging
import sys

def setup_logging():
    """Configura un logger básico que imprime a la consola."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)]
    )