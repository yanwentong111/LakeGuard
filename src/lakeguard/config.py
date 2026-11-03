from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .exceptions import ConfigError
from .models import ConfigModel


def load_config(path: str | Path) -> tuple[ConfigModel, Path]:
    config_path = Path(path).expanduser().resolve()
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        config = ConfigModel.model_validate(raw)
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError, TypeError) as exc:
        raise ConfigError(f"Invalid config {config_path}: {exc}") from exc
    source_path = Path(config.source).expanduser()
    if not source_path.is_absolute():
        source_path = config_path.parent / source_path
    return config, source_path
