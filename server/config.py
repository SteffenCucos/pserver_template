
import json

from dataclasses import dataclass
from typing import cast

from pserialize import deserialize


@dataclass
class DatabaseConfig:
    backend: str
    uri: str
    name: str


@dataclass
class Network:
    host: str
    port: int


@dataclass
class Config:
    database: DatabaseConfig
    network: Network


def __fromFile(configPath: str) -> Config:
    with open(configPath, "rb") as configFile:
        configJson = json.loads(configFile.read())
        return configJson


__config: Config | None = None


def __get_config() -> Config:
    global __config
    if not __config:
        configJson = None
        for n in range(5):
            try:
                configJson = __fromFile("../" * n + "config.json")
            except Exception:
                continue

        if not configJson:
            raise Exception("Could not find config.json file")
        try:
            config = deserialize(configJson, Config)
            __config = cast(Config, config)
        except Exception as e:
            raise Exception("Config is invalid", e)

    return __config


config: Config = __get_config()
