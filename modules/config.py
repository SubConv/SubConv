from typing import List, Tuple
from pathlib import Path
import sys

from pydantic import BaseModel
from pydantic_settings_yaml import YamlBaseSettings
from pydantic_settings import SettingsConfigDict, BaseSettings

from . import config_template

class Group(BaseModel):
    name: str
    type: str
    rule: bool = True
    manual: bool = False
    prior: str = None
    regex: str = None

class Config(YamlBaseSettings):
    HEAD: dict
    TEST_URL: str = "http://www.gstatic.com/generate_204"
    RULESET: List[Tuple[str, str]]
    CUSTOM_PROXY_GROUP: List[Group]

    model_config = SettingsConfigDict(
        secrets_dir=".",
        yaml_file="config.yaml"
    )


try:
    if Path("config.yaml").exists():
        with open("config.yaml", "r", encoding="utf-8") as f:
            if f.read() == "":
                raise FileNotFoundError
    configInstance = Config("config.yaml")
except FileNotFoundError:
    print(f"config.yaml not found or empty, please run {sys.argv[0]} -h to see how to generate a default config file")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
