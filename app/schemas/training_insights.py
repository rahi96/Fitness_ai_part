from typing import List, Dict, Any
from pydantic import BaseModel, Field
import json
from pathlib import Path


def _load_defaults() -> Dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "dummy_data.json"
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


_DEFAULTS = _load_defaults()


class StrengthInsight(BaseModel):
    title: str
    insight: str


class Achievement(BaseModel):
    title: str
    value: str
    detail: str


class TrainingInsightsRequest(BaseModel):
    athlete_profile: Dict[str, Any] = Field(default_factory=lambda: _DEFAULTS.get("athlete_profile", {}))
    training_summary: Dict[str, Any] = Field(default_factory=lambda: _DEFAULTS.get("training_summary", {}))
    race_analysis: Dict[str, Any] = Field(default_factory=lambda: _DEFAULTS.get("race_analysis", {}))
    performance_predictions: Dict[str, Any] = Field(default_factory=lambda: _DEFAULTS.get("performance_predictions", {}))
    training_context: Dict[str, Any] = Field(default_factory=lambda: _DEFAULTS.get("training_context", {}))

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "athlete_profile": {
                    "age": _DEFAULTS.get("personal_info", {}).get("age", 32),
                    "gender": (_DEFAULTS.get("personal_info", {}).get("gender") or "female").lower(),
                    "threshold_hr": _DEFAULTS.get("heart_rate_zones", {}).get("threshold_hr_bpm", 175),
                    "threshold_pace": _DEFAULTS.get("performance_metrics", {}).get("threshold_pace_min_per_km", "4:15"),
                    "ftp": _DEFAULTS.get("performance_metrics", {}).get("ftp_watts", 285),
                    "personal_bests": {
                        "5k": next((pb["time"] for pb in _DEFAULTS.get("personal_bests", []) if pb.get("distance") == "5K"), "19:45"),
                        "10k": next((pb["time"] for pb in _DEFAULTS.get("personal_bests", []) if pb.get("distance") == "10K"), "41:30"),
                        "half_marathon": next((pb["time"] for pb in _DEFAULTS.get("personal_bests", []) if pb.get("distance") == "Half Marathon"), "1:32:18"),
                    },
                },
                "training_summary": _DEFAULTS.get("training_summary", {}),
                "race_analysis": _DEFAULTS.get("race_analysis", {}),
                "performance_predictions": _DEFAULTS.get("performance_predictions", {}),
                "training_context": _DEFAULTS.get("training_context", {}),
            }
        },
    }


class TrainingInsightsResponse(BaseModel):
    strengths: List[StrengthInsight]
    achievements: List[Achievement]
