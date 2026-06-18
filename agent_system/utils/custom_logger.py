import os, logging
from datetime import datetime
from collections import deque


class CustomFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, style='%', validate=True):
        if not fmt:
            fmt = "%(asctime)s - %(levelname)s - %(relpath)s:%(lineno)d - %(funcName)s - %(message)s"
        super().__init__(fmt, datefmt, style, validate)

    def format(self, record):
        try:
            record.relpath = os.path.relpath(record.pathname)
        except ValueError:
            record.relpath = record.pathname
        return super().format(record)

    def formatTime(self, record, datefmt=None):
        datefmt = datefmt or '%Y-%m-%d %H:%M:%S'
        return datetime.fromtimestamp(record.created).strftime(datefmt)


class BaseFileHandler(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding='utf-8'):
        directory = os.path.dirname(filename)
        if directory:
            os.makedirs(directory, exist_ok=True)
        super().__init__(filename, mode, encoding)


class CustomLogging(logging.Logger):
    def __init__(self, name):
        super().__init__(name)
        self.setLevel(logging.DEBUG)

    def add_file_handler(self, filename, fmt=None, mode='a', encoding='utf-8'):
        if filename is None:
            raise ValueError("filename cannot be None. A valid log file path is required.")
        for handler in self.handlers:
            if isinstance(handler, BaseFileHandler) and handler.baseFilename == os.path.abspath(filename):
                return
        handler = BaseFileHandler(filename, mode, encoding)
        handler.setFormatter(CustomFormatter(fmt))
        super().addHandler(handler)


_instances = {}

def GetLogger(logger_type, logger_name=None, fmt=None) -> CustomLogging:
    if logger_type not in _instances:
        logger = CustomLogging(logger_type)
        logger.add_file_handler(logger_name, fmt)
        _instances[logger_type] = logger
    return _instances[logger_type]


def read_logs(filename, encoding="utf-8", num_lines=None) -> str:
    try:
        with open(filename, 'r', encoding=encoding) as log_file:
            if num_lines is None:
                return log_file.read()
            else:
                return ''.join(deque(log_file, maxlen=num_lines))
    except FileNotFoundError:
        return f"Log file '{filename}' not found."
    except Exception as e:
        return f"Error reading log file: {e}"
