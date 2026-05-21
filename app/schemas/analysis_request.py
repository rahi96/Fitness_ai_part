import copy
import json
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel, Field


def _load_default_data() -> Dict[str, Any]:
    data_path = Path(__file__).resolve().parents[2] / "dummy_data.json"
    if data_path.exists():
        with data_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


_DEFAULT_DATA = _load_default_data()


def _default_section(key: str) -> Dict[str, Any]:
    return copy.deepcopy(_DEFAULT_DATA.get(key, {}))


class TrainingData(BaseModel):
    user_id: str | int = Field(..., description="User identifier used for MongoDB response caching")
    analysis_period: Dict[str, Any] = Field(default_factory=lambda: _default_section("analysis_period"))
    zone_configuration: Dict[str, Any] = Field(default_factory=lambda: _default_section("zone_configuration"))
    computed_training_metrics: Dict[str, Any] = Field(default_factory=lambda: _default_section("computed_training_metrics"))
    run_duration_tracking: Dict[str, Any] = Field(default_factory=lambda: _default_section("run_duration_tracking"))
    weekly_progression: Dict[str, Any] = Field(default_factory=lambda: _default_section("weekly_progression"))
    long_run_summary: Dict[str, Any] = Field(default_factory=lambda: _default_section("long_run_summary"))
    efficiency_indicators: Dict[str, Any] = Field(default_factory=lambda: _default_section("efficiency_indicators"))

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "user_id": "demo-user",
                "analysis_period": _default_section("analysis_period"),
                "zone_configuration": _default_section("zone_configuration"),
                "computed_training_metrics": _default_section("computed_training_metrics"),
                "run_duration_tracking": _default_section("run_duration_tracking"),
                "weekly_progression": _default_section("weekly_progression"),
                "long_run_summary": _default_section("long_run_summary"),
                "efficiency_indicators": _default_section("efficiency_indicators"),
            }
        },
    }
