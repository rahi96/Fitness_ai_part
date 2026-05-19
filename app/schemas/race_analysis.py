import json
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class TrainingInsight(BaseModel):
    title: str
    insight: str


class Recommendation(BaseModel):
    title: str
    priority: str
    explanation: str
    estimated_impact: str


class RaceSummary(BaseModel):
    actual_time: str
    predicted_time: str
    performance_delta: str
    status: str


def _load_defaults() -> Dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "dummy_data.json"
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


_DEFAULTS = _load_defaults()


def _best_time(distance: str, fallback: str) -> str:
    for pb in _DEFAULTS.get("personal_bests", []):
        if pb.get("distance") == distance:
            return pb.get("time", fallback)
    return fallback


def _default_training_context() -> Dict[str, Any]:
    ctx = _DEFAULTS.get("training_context")
    if ctx:
        return ctx
    return {
        "zone_configuration": _DEFAULTS.get("zone_configuration", {}),
        "computed_training_metrics": _DEFAULTS.get("computed_training_metrics", {}),
        "run_duration_tracking": _DEFAULTS.get("run_duration_tracking", {}),
        "weekly_progression": _DEFAULTS.get("weekly_progression", {}),
        "long_run_summary": _DEFAULTS.get("long_run_summary", {}),
        "efficiency_indicators": _DEFAULTS.get("efficiency_indicators", {}),
    }


class RaceAnalysisRequest(BaseModel):
    user_id: str | int = Field(default="demo-user")
    athlete_profile: Dict[str, Any] = Field(
        default_factory=lambda: {
            "age": _DEFAULTS.get("personal_info", {}).get("age", 32),
            "gender": (_DEFAULTS.get("personal_info", {}).get("gender") or "female").lower(),
            "threshold_hr": _DEFAULTS.get("heart_rate_zones", {}).get("threshold_hr_bpm", 175),
            "threshold_pace": _DEFAULTS.get("performance_metrics", {}).get("threshold_pace_min_per_km", "4:15"),
            "ftp": _DEFAULTS.get("performance_metrics", {}).get("ftp_watts", 285),
            "personal_bests": {
                "5k": _best_time("5K", "19:45"),
                "10k": _best_time("10K", "41:30"),
                "half_marathon": _best_time("Half Marathon", "1:32:18"),
            },
        }
    )
    training_summary: Dict[str, Any] = Field(
        default_factory=lambda: {
            "easy_running_percent": _DEFAULTS.get("computed_training_metrics", {})
            .get("pace_zone_distribution_percent", {})
            .get("easy_recovery", 85),
            "zone_4_time_percent": 6,
            "vo2_zone_detected": False,
            "long_run_max_minutes": _DEFAULTS.get("long_run_summary", {}).get("max_duration_minutes", 105),
            "weekly_volume_trend": "consistent",
            "taper_weeks": 2,
        }
    )
    race_analysis: Dict[str, Any] = Field(
        default_factory=lambda: {
            "race": "Half Marathon",
            "predicted_time": "1:43:15",
            "actual_time": "1:42:37",
            "performance_delta_seconds": -38,
            "prediction_accuracy_percent": 98.4,
        }
    )
    performance_predictions: Dict[str, Any] = Field(
        default_factory=lambda: {
            "5k": {"time": "20:15", "confidence": "High"},
            "10k": {"time": "42:18", "confidence": "High"},
            "half_marathon": {"time": "1:42:37", "confidence": "Actual"},
            "marathon": {"time": "3:38:45", "confidence": "Medium"},
        }
    )
    training_context: Dict[str, Any] = Field(
        default_factory=_default_training_context
    )

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "user_id": "demo-user",
                "athlete_profile": {
                    "age": 32,
                    "gender": "female",
                    "threshold_hr": 175,
                    "threshold_pace": "4:15",
                    "ftp": 285,
                    "personal_bests": {
                        "5k": "19:45",
                        "10k": "41:30",
                        "half_marathon": "1:32:18",
                    },
                },
                "training_summary": {
                    "easy_running_percent": 85,
                    "zone_4_time_percent": 6,
                    "vo2_zone_detected": False,
                    "long_run_max_minutes": 105,
                    "weekly_volume_trend": "consistent",
                    "taper_weeks": 2,
                },
                "race_analysis": {
                    "race": "Half Marathon",
                    "predicted_time": "1:43:15",
                    "actual_time": "1:42:37",
                    "performance_delta_seconds": -38,
                    "prediction_accuracy_percent": 98.4,
                },
                "performance_predictions": {
                    "5k": {"time": "20:15", "confidence": "High"},
                    "10k": {"time": "42:18", "confidence": "High"},
                    "half_marathon": {"time": "1:42:37", "confidence": "Actual"},
                    "marathon": {"time": "3:38:45", "confidence": "Medium"},
                },
                "training_context": {
                    "zone_configuration": _default_training_context().get("zone_configuration", {}),
                    "computed_training_metrics": _default_training_context().get("computed_training_metrics", {}),
                    "run_duration_tracking": _default_training_context().get("run_duration_tracking", {}),
                    "weekly_progression": _default_training_context().get("weekly_progression", {}),
                    "long_run_summary": _default_training_context().get("long_run_summary", {}),
                    "efficiency_indicators": _default_training_context().get("efficiency_indicators", {}),
                },
            }
        },
    }


class RaceAnalysisResponse(BaseModel):
    race_summary: RaceSummary
    training_analysis: List[TrainingInsight]
    recommendations: List[Recommendation]
    predicted_performance: Dict[str, str]
    build_up_summary: str
