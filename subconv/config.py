import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource

from .filters import compile_group_filter


class Group(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    rule: bool = True
    manual: bool = False
    prior: str | None = None
    regex: str | None = None

    @field_validator('regex')
    @classmethod
    def validate_regex(cls, value):
        if value is not None:
            compile_group_filter(value)
        return value


class TemplateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    HEAD: dict[str, object] = Field(default_factory=dict)
    TEST_URL: str = "http://www.gstatic.com/generate_204"
    RULESET: list[tuple[str, str]] = Field(default_factory=list)
    CUSTOM_PROXY_GROUP: list[Group] = Field(default_factory=list)


CONFIG_PATH = Path("config.yaml")
CONFIG_EXAMPLE_PATH = Path("config.yaml.example")
TEMPLATE_DIR = Path("template")
TEMPLATE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(yaml_file=str(CONFIG_PATH))

    HOST: str = "0.0.0.0"
    PORT: int = 8080
    DEFAULT_TEMPLATE: str = "zju"
    DISALLOW_ROBOTS: bool = True
    ALLOW_PRIVATE_NETWORKS: bool = False

    @field_validator("DEFAULT_TEMPLATE")
    @classmethod
    def validate_default_template(cls, value: str) -> str:
        normalized_name = value.strip()
        if normalized_name == "":
            raise ValueError("DEFAULT_TEMPLATE cannot be empty")
        if TEMPLATE_NAME_PATTERN.fullmatch(normalized_name) is None:
            raise ValueError("DEFAULT_TEMPLATE contains invalid characters")
        return normalized_name

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            env_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file=str(CONFIG_PATH)),
            YamlConfigSettingsSource(settings_cls, yaml_file=str(CONFIG_EXAMPLE_PATH)),
        )


appConfigInstance: AppConfig | None = None


def get_app_config() -> AppConfig:
    global appConfigInstance
    if appConfigInstance is None:
        appConfigInstance = AppConfig()
    return appConfigInstance


def default_template_name() -> str:
    return normalize_template_name(get_app_config().DEFAULT_TEMPLATE)


def available_templates() -> list[str]:
    if not TEMPLATE_DIR.is_dir():
        return []
    return sorted(path.stem for path in TEMPLATE_DIR.glob("*.yaml") if path.is_file())


def load_all_templates() -> dict[str, TemplateConfig]:
    template_names = available_templates()
    loaded_templates = {
        template_name: load_template(template_name) for template_name in template_names
    }
    return loaded_templates


def normalize_template_name(template_name: str | None) -> str:
    if template_name is None or template_name.strip() == "":
        return normalize_template_name(get_app_config().DEFAULT_TEMPLATE)

    normalized_name = template_name.strip()
    if TEMPLATE_NAME_PATTERN.fullmatch(normalized_name) is None:
        raise ValueError("Invalid template name")
    return normalized_name


def load_template(template_name: str | None = None) -> TemplateConfig:
    normalized_name = normalize_template_name(template_name)
    template_path = TEMPLATE_DIR / f"{normalized_name}.yaml"

    if not template_path.is_file():
        available = ", ".join(available_templates()) or "none"
        raise FileNotFoundError(
            f"Template '{normalized_name}' not found in {TEMPLATE_DIR}/ (available: {available})"
        )

    with template_path.open("r", encoding="utf-8") as file:
        raw_template = yaml.safe_load(file)

    if raw_template in (None, ""):
        raise ValueError(f"Template '{normalized_name}' is empty")

    return TemplateConfig.model_validate(raw_template)


def load_runtime_template(template_name: str | None = None) -> TemplateConfig:
    return load_template(template_name)


def validate_templates_on_startup() -> None:
    load_all_templates()
    load_runtime_template(default_template_name())
