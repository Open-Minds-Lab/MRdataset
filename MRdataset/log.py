"""Logging setup for MRdataset."""
import logging
from logging import Filter
from MRdataset.config import CACHE_DIR
import time


def setup_logger(name, filename, level=logging.INFO):
    format_string = '%(asctime)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt=format_string)
    handler = logging.StreamHandler()
    dup_filter = DuplicateFilter()
    logger_ = logging.getLogger(name)
    logger_.setLevel(level)
    handler.addFilter(dup_filter)
    handler.setFormatter(formatter)
    logger_.addHandler(handler)
    return logger_


class DuplicateFilter(Filter):
    def __init__(self):
        super().__init__()
        self.msgs = set()

    def filter(self, record):
        rv = record.msg not in self.msgs
        self.msgs.add(record.msg)
        return rv


log_filename = CACHE_DIR / '{}.log'.format(time.strftime("%m_%d_%Y_%H_%M"))
logger = setup_logger('root', log_filename, logging.INFO)
