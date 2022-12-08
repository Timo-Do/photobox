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
    logger.addHandler(console_logger)
    logger.addFilter(DuplicateFilter())

    
    return logger