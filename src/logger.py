import logging
import os
import sys

def setup_logger():
    logger = logging.getLogger("Lumina")
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    
    # File handler
    fh = logging.FileHandler("lumina.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    
    # Formatting
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    
    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger

log = setup_logger()
