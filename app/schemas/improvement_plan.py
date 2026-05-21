import json
from pathlib import Path
from typing import Any, Dict, List
from pydantic import BaseModel, Field


def _load_defaults() -> Dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "dummy_data.json"
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


_DEFAULTS = _load_defaults()


class ImprovementItem(BaseModel):
    title: str
    analysis: str
    recommendation: str


class GoalItem(BaseModel):
    title: str
    insight: str


class OptimalDistribution(BaseModel):
    title: str
    detail: str


class ImprovementPlanRequest(BaseModel):
    user_id: str | int = Field(..., description="User identifier used for MongoDB response caching")
    athlete_profile: Dict[str, Any] = Field(default_factory=lambda: _DEFAULTS.get("athlete_profile", {}))
    training_summary: Dict[str, Any] = Field(default_factory=lambda: _DEFAULTS.get("training_summary", {}))
    race_analysis: Dict[str, Any] = Field(default_factory=lambda: _DEFAULTS.get("race_analysis", {}))
    performance_predictions: Dict[str, Any] = Field(default_factory=lambda: _DEFAULTS.get("performance_predictions", {}))
    training_context: Dict[str, Any] = Field(default_factory=lambda: _DEFAULTS.get("training_context", {}))

    model_config = {
        "extra": "allow",  # ignore unknown keys like optimal_distribution in requests
        "json_schema_extra": {
            "example": {
                "user_id": "demo-user",
                "athlete_profile": _DEFAULTS.get("athlete_profile", {}),
                "training_summary": _DEFAULTS.get("training_summary", {}),
                "race_analysis": _DEFAULTS.get("race_analysis", {}),
                "performance_predictions": _DEFAULTS.get("performance_predictions", {}),
                "training_context": _DEFAULTS.get("training_context", {}),
            }
        },
    }


class ImprovementPlanResponse(BaseModel):
    optimal_distribution: OptimalDistribution
    areas_for_improvement: List[ImprovementItem]
    next_steps: List[GoalItem]
