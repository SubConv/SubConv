from typing import List, Tuple
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings_yaml import YamlBaseSettings
from pydantic_settings import SettingsConfigDict
import yaml

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
    configInstance = Config()
except FileNotFoundError:
    print("config.yaml not found, creating a default one")
    with open("config.yaml", "w", encoding="utf-8") as f:
        yaml.SafeDumper.ignore_aliases = lambda *args : True
        yaml.safe_dump(config_template.template, f, allow_unicode=True, sort_keys=False)
    configInstance = Config()
    print("config.yaml created")
except Exception as e:
    print(f"Error: {e}")
    exit(1)
