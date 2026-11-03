"""Validated configuration models."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RuleType = Literal["not_null", "unique", "min", "max", "accepted_values"]

class RuleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: RuleType
    column: str = Field(min_length=1)
    value: Any = None
    values: list[Any] | None = None

    @model_validator(mode="after")
    def validate_arguments(self) -> RuleConfig:
        if self.type in {"min", "max"} and self.value is None:
            raise ValueError(f"{self.type} rule requires value")
        if self.type == "accepted_values" and not self.values:
            raise ValueError("accepted_values rule requires non-empty values")
        return self

class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: str | None = None
    source: str
    rules: list[RuleConfig]
    output: str | None = None
