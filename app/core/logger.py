import logging
import os
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, "ers_app.log")

logger = logging.getLogger("ers_logger")
logger.setLevel(logging.INFO)

handler = TimedRotatingFileHandler(
    log_file,
    when="midnight",      # rotate daily
    interval=1,
    backupCount=30,       # keep last 30 days logs
    encoding="utf-8"
)

handler.suffix = "%Y-%m-%d.log"

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s",
    "%Y-%m-%d %H:%M:%S"
)

handler.setFormatter(formatter)
logger.addHandler(handler)