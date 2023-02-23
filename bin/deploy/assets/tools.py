import logging

LOGGING_LEVEL = logging.DEBUG

class DuplicateFilter(logging.Filter):
    def filter(self, record):
        current_log = (record.module, record.levelno, record.msg)
        if current_log != getattr(self, "last_log", None):
            self.last_log = current_log
            return True
        return False

def get_logger(appname):
    logger = logging.getLogger(appname)
    logger_formatter = logging.Formatter(
        fmt = "%(asctime)s [%(levelname)s]\t{app} : %(message)s".format(app = appname),
        datefmt= "%Y-%m-%d %H:%M:%S")
    logger.setLevel(LOGGING_LEVEL)
    console_logger = logging.StreamHandler()
    console_logger.setFormatter(logger_formatter)
    if not logger.handlers:
        logger.addHandler(console_logger)
    logger.addFilter(DuplicateFilter())

    
    return logger

def subtract_lists(list1, list2):
    return list(set(list1) - set(list2))

def seconds2hms(sec):
    hours, remainder = divmod(sec, 60 * 60)
    minutes, seconds = divmod(remainder,60)
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)

