
import logging
import logging.config

import uvicorn

from fastapi import FastAPI

from api.v1.api import api_router
from config import config


log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(asctime)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",

        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        None: {"handlers": ["default"], "level": "DEBUG"},
    },
}

# setup loggers
logging.config.dictConfig(log_config)

# get root logger
logger = logging.getLogger(__name__) 

app = FastAPI()

app.include_router(api_router)


if __name__ == "__main__":
    host = config.network.host
    port = config.network.port

    uvicorn.run("main:app", port=port, host=host, reload=True)
