import logging.handlers
import os
from datetime import datetime

import pytz

JP = pytz.timezone("Asia/Tokyo")
discord_logger = logging.getLogger("WNHHelper")
server_logger = logging.getLogger("Server")

fmt = "[{asctime}] [{levelname:<8}] {name}: {message}"
dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(fmt, dt_fmt, style="{")


def logger_setting(logger_type: str, logger_: logging.Logger):
    if logger_type == "discord":
        logging.getLogger("discord").setLevel(logging.INFO)
        logging.getLogger("discord.http").setLevel(logging.WARNING)
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 f"logs/{logger_type}/{datetime.now(JP).strftime('%Y-%m-%d %H-%M-%S')}.log")
    logger_.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(filename=filename, encoding="utf-8",
                                                   maxBytes=100 * 1024,  # 100 KiB
                                                   backupCount=5, )  # Rotate through 5 files
    handler.setFormatter(formatter)
    logger_.addHandler(handler)
    return handler

discord_handler = logger_setting("discord", discord_logger)
server_handler = logger_setting("server", server_logger)
