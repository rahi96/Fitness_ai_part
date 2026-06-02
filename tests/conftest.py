import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_analysis_request():
    """Provide a sample AnalysisRequest payload for testing."""
    return {
        "user_id": 1,
        "analysis_period": {"weeks": 8},
        "computed_training_metrics": {
            "heart_rate_zone_distribution_percent": {
                "zone_1": 50,
                "zone_2": 30,
                "zone_3": 15,
                "zone_4": 4,
                "zone_5": 1,
            },
            "power_zone_distribution_percent": {
                "zone_1": 50,
                "zone_2": 30,
                "zone_3": 15,
                "zone_4": 4,
                "zone_5": 1,
            },
            "pace_zone_distribution_percent": {
                "easy_recovery": 72,
                "tempo": 20,
                "hard": 8,
            },
        },
        "run_duration_tracking": {
            "less_than_30_min": 5,
            "between_45_and_60_min": 10,
            "between_60_and_90_min": 4,
            "above_90_min": 1,
        },
        "weekly_progression": {
            "average_weekly_distance_km": 60,
            "peak_weekly_distance_km": 92,
            "max_weekly_increase_percent": 8,
        },
        "long_run_summary": {"count": 6, "max_duration_minutes": 150},
        "efficiency_indicators": {
            "pace_efficiency_change_percent": 5,
            "heart_rate_drift": "low",
        },
    }


@pytest.fixture
def high_volume_request():
    """Provide a high-volume training request."""
    return {
        "user_id": 2,
        "analysis_period": {"weeks": 12},
        "computed_training_metrics": {
            "heart_rate_zone_distribution_percent": {
                "zone_1": 60,
                "zone_2": 25,
                "zone_3": 10,
                "zone_4": 3,
                "zone_5": 2,
            },
            "power_zone_distribution_percent": {
                "zone_1": 60,
                "zone_2": 25,
                "zone_3": 10,
                "zone_4": 3,
                "zone_5": 2,
            },
            "pace_zone_distribution_percent": {
                "easy_recovery": 80,
                "tempo": 15,
                "hard": 5,
            },
        },
        "run_duration_tracking": {
            "less_than_30_min": 8,
            "between_45_and_60_min": 18,
            "between_60_and_90_min": 12,
            "above_90_min": 4,
        },
        "weekly_progression": {
            "average_weekly_distance_km": 80,
            "peak_weekly_distance_km": 110,
            "max_weekly_increase_percent": 6,
        },
        "long_run_summary": {"count": 10, "max_duration_minutes": 180},
        "efficiency_indicators": {
            "pace_efficiency_change_percent": 8,
            "heart_rate_drift": "low",
        },
    }


@pytest.fixture
def low_volume_request():
    """Provide a low-volume training request."""
    return {
        "user_id": 3,
        "analysis_period": {"weeks": 4},
        "computed_training_metrics": {
            "heart_rate_zone_distribution_percent": {
                "zone_1": 40,
                "zone_2": 30,
                "zone_3": 20,
                "zone_4": 7,
                "zone_5": 3,
            },
            "power_zone_distribution_percent": {
                "zone_1": 40,
                "zone_2": 30,
                "zone_3": 20,
                "zone_4": 7,
                "zone_5": 3,
            },
            "pace_zone_distribution_percent": {
                "easy_recovery": 60,
                "tempo": 25,
                "hard": 15,
            },
        },
        "run_duration_tracking": {
            "less_than_30_min": 3,
            "between_45_and_60_min": 4,
            "between_60_and_90_min": 2,
            "above_90_min": 0,
        },
        "weekly_progression": {
            "average_weekly_distance_km": 30,
            "peak_weekly_distance_km": 40,
            "max_weekly_increase_percent": 15,
        },
        "long_run_summary": {"count": 2, "max_duration_minutes": 90},
        "efficiency_indicators": {
            "pace_efficiency_change_percent": 2,
            "heart_rate_drift": "moderate",
        },
    }
