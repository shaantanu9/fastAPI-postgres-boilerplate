import logging
from loguru import logger
import sys
import json

class JsonSink:
    def __call__(self, message):
        record = message.record
        log = {
            "time": record["time"].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record["level"].name,
            "message": record["message"],
            "name": record["name"],
            "function": record["function"],
            "line": record["line"],
        }
        print(json.dumps(log))

def setup_logging():
    logger.remove()
    logger.add(JsonSink(), level="INFO")
    logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

def bind_request_context(request_id=None):
    if request_id:
        logger.bind(request_id=request_id)
