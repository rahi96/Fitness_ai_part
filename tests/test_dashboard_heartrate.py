"""
Tests for Dashboard endpoints (7 routes) and Heart Rate endpoint (1 route).

These routes were missing from the original test_api.py test suite.
All dashboard and heart-rate endpoints use the same AnalysisRequest payload
and return fallback data when OPENAI_API_KEY is not set.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_payload():
    """Standard AnalysisRequest payload used across all dashboard/heart-rate tests."""
    return {
        "user_id": "test-dash-1",
        "analysis_period": {"weeks": 12},
        "computed_training_metrics": {
            "heart_rate_zone_distribution_percent": {
                "zone_1": 20, "zone_2": 45, "zone_3": 18, "zone_4": 12, "zone_5": 5,
            },
            "power_zone_distribution_percent": {
                "zone_1": 28, "zone_2": 42, "zone_3": 18, "zone_4": 8, "zone_5": 4,
            },
            "pace_zone_distribution_percent": {
                "easy_recovery": 82, "tempo": 14, "hard": 4,
            },
        },
        "run_duration_tracking": {
            "less_than_30_min": 2,
            "between_45_and_60_min": 3,
            "between_60_and_90_min": 2,
            "above_90_min": 1,
        },
        "weekly_progression": {
            "average_weekly_distance_km": 46,
            "peak_weekly_distance_km": 54,
            "max_weekly_increase_percent": 8,
        },
        "long_run_summary": {"count": 4, "max_duration_minutes": 100},
        "efficiency_indicators": {
            "pace_efficiency_change_percent": 7,
            "heart_rate_drift": "low",
        },
    }


# ==================== DASHBOARD ROUTES ====================


class TestDashboardExecutiveSummary:
    """Test POST /api/v1/dashboard/executive-summary."""

    def test_executive_summary_success(self, client, sample_payload):
        response = client.post("/api/v1/dashboard/executive-summary", json=sample_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-dash-1"
        assert "summary_narrative" in data
        assert isinstance(data["summary_narrative"], str)
        assert len(data["summary_narrative"]) > 0
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 1
        for item in data["items"]:
            assert "title" in item
            assert "status" in item
            assert "detail" in item

    def test_executive_summary_invalid_payload(self, client):
        response = client.post("/api/v1/dashboard/executive-summary", json={"bad": "data"})
        assert response.status_code == 422

    def test_executive_summary_idempotent(self, client, sample_payload):
        """Same payload should return the same structure (fallback or cached)."""
        r1 = client.post("/api/v1/dashboard/executive-summary", json=sample_payload)
        r2 = client.post("/api/v1/dashboard/executive-summary", json=sample_payload)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["summary_narrative"] == r2.json()["summary_narrative"]


class TestDashboardTrainingLoadAnalysis:
    """Test POST /api/v1/dashboard/training-load-analysis."""

    def test_training_load_analysis_success(self, client, sample_payload):
        response = client.post("/api/v1/dashboard/training-load-analysis", json=sample_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-dash-1"
        assert "weekly_distance_progression" in data
        assert isinstance(data["weekly_distance_progression"], list)
        assert len(data["weekly_distance_progression"]) >= 1
        # Validate structure of a single point
        point = data["weekly_distance_progression"][0]
        assert "week" in point
        assert "distance_km" in point
        assert "training_load_narrative" in data
        assert "phases" in data
        assert isinstance(data["phases"], list)
        for phase in data["phases"]:
            assert "name" in phase
            assert "weeks" in phase
            assert "description" in phase
        assert "analysis" in data

    def test_training_load_analysis_invalid_payload(self, client):
        response = client.post("/api/v1/dashboard/training-load-analysis", json={})
        assert response.status_code == 422


class TestDashboardPerformanceMetrics:
    """Test POST /api/v1/dashboard/performance-metrics."""

    def test_performance_metrics_success(self, client, sample_payload):
        response = client.post("/api/v1/dashboard/performance-metrics", json=sample_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-dash-1"
        assert "average_pace" in data
        assert isinstance(data["average_pace"], str)
        assert "resting_hr" in data
        assert isinstance(data["resting_hr"], int)
        assert "easy_run_hr" in data
        assert isinstance(data["easy_run_hr"], int)
        assert "tempo_hr" in data
        assert isinstance(data["tempo_hr"], int)
        assert "pace_progression_narrative" in data
        assert "hr_analysis_narrative" in data


class TestDashboardWeeklyTrainingBreakdown:
    """Test POST /api/v1/dashboard/weekly-training-breakdown."""

    def test_weekly_training_breakdown_success(self, client, sample_payload):
        response = client.post("/api/v1/dashboard/weekly-training-breakdown", json=sample_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-dash-1"
        assert "weeks" in data
        assert isinstance(data["weeks"], list)
        assert len(data["weeks"]) >= 1
        week = data["weeks"][0]
        assert "week" in week
        assert "distance_km" in week
        assert "runs" in week
        assert "avg_pace" in week
        assert "long_run_km" in week
        assert "summary" in data

    def test_weekly_breakdown_week_numbers_sequential(self, client, sample_payload):
        """Validate that fallback weeks are in sequential order."""
        response = client.post("/api/v1/dashboard/weekly-training-breakdown", json=sample_payload)
        data = response.json()
        weeks = [w["week"] for w in data["weeks"]]
        assert weeks == sorted(weeks)


class TestDashboardRecommendationsInsights:
    """Test POST /api/v1/dashboard/recommendations-insights."""

    def test_recommendations_insights_success(self, client, sample_payload):
        response = client.post("/api/v1/dashboard/recommendations-insights", json=sample_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-dash-1"
        assert "strengths" in data
        assert isinstance(data["strengths"], list)
        assert len(data["strengths"]) >= 1
        assert "areas_for_improvement" in data
        assert isinstance(data["areas_for_improvement"], list)
        assert len(data["areas_for_improvement"]) >= 1
        assert "next_steps" in data
        assert isinstance(data["next_steps"], list)
        assert len(data["next_steps"]) >= 1
        # Validate item structure
        for item in data["strengths"]:
            assert "title" in item
            assert "detail" in item

    def test_recommendations_insights_invalid(self, client):
        response = client.post("/api/v1/dashboard/recommendations-insights", json={"user_id": "x"})
        assert response.status_code == 422


class TestDashboardTrainingZoneDistribution:
    """Test POST /api/v1/dashboard/training-zone-distribution."""

    def test_training_zone_distribution_success(self, client, sample_payload):
        response = client.post("/api/v1/dashboard/training-zone-distribution", json=sample_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-dash-1"
        assert "zones" in data
        assert isinstance(data["zones"], list)
        assert len(data["zones"]) >= 1
        for zone in data["zones"]:
            assert "zone" in zone
            assert "percentage" in zone
            assert "description" in zone
        assert "optimal_distribution_narrative" in data
        assert "current_assessment" in data

    def test_training_zone_percentages_sum(self, client, sample_payload):
        """Verify that zone percentages sum to 100."""
        response = client.post("/api/v1/dashboard/training-zone-distribution", json=sample_payload)
        data = response.json()
        total = sum(z["percentage"] for z in data["zones"])
        assert total == pytest.approx(100.0, abs=1.0)


class TestDashboardKeyAchievements:
    """Test POST /api/v1/dashboard/key-achievements."""

    def test_key_achievements_success(self, client, sample_payload):
        response = client.post("/api/v1/dashboard/key-achievements", json=sample_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-dash-1"
        assert "achievements" in data
        assert isinstance(data["achievements"], list)
        assert len(data["achievements"]) >= 1
        for achievement in data["achievements"]:
            assert "title" in achievement
            assert "value" in achievement
            assert "detail" in achievement
        assert "summary" in data
        assert isinstance(data["summary"], str)


# ==================== HEART RATE ROUTE ====================


class TestHeartRateEfficiency:
    """Test POST /api/v1/heart-rate/heart-rate-efficiency."""

    def test_heart_rate_efficiency_success(self, client, sample_payload):
        response = client.post("/api/v1/heart-rate/heart-rate-efficiency", json=sample_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-dash-1"

        # improved_aerobic_efficiency
        aero = data["improved_aerobic_efficiency"]
        assert "narrative" in aero
        assert "week_1_hr" in aero
        assert isinstance(aero["week_1_hr"], int)
        assert "week_1_pace" in aero
        assert "week_12_hr" in aero
        assert isinstance(aero["week_12_hr"], int)
        assert "week_12_pace" in aero

        # threshold_pace_development
        threshold = data["threshold_pace_development"]
        assert "narrative" in threshold
        assert "threshold_hr" in threshold
        assert isinstance(threshold["threshold_hr"], int)
        assert "initial_pace" in threshold
        assert "improved_pace" in threshold
        assert "difference_seconds" in threshold
        assert isinstance(threshold["difference_seconds"], int)

        # low_cardiac_drift
        drift = data["low_cardiac_drift"]
        assert "narrative" in drift
        assert "drift_bpm_increase" in drift
        assert isinstance(drift["drift_bpm_increase"], int)
        assert "duration_minutes" in drift
        assert isinstance(drift["duration_minutes"], int)

    def test_heart_rate_efficiency_invalid_payload(self, client):
        response = client.post("/api/v1/heart-rate/heart-rate-efficiency", json={"missing": "fields"})
        assert response.status_code == 422

    def test_heart_rate_efficiency_values_reasonable(self, client, sample_payload):
        """Ensure fallback HR values are in a physiologically reasonable range."""
        response = client.post("/api/v1/heart-rate/heart-rate-efficiency", json=sample_payload)
        data = response.json()
        aero = data["improved_aerobic_efficiency"]
        assert 40 <= aero["week_1_hr"] <= 220
        assert 40 <= aero["week_12_hr"] <= 220
        threshold = data["threshold_pace_development"]
        assert 100 <= threshold["threshold_hr"] <= 220


# ==================== CROSS-DASHBOARD INTEGRATION ====================


class TestDashboardIntegration:
    """Integration tests that hit all 7 dashboard endpoints with the same payload."""

    DASHBOARD_ENDPOINTS = [
        "/api/v1/dashboard/executive-summary",
        "/api/v1/dashboard/training-load-analysis",
        "/api/v1/dashboard/performance-metrics",
        "/api/v1/dashboard/weekly-training-breakdown",
        "/api/v1/dashboard/recommendations-insights",
        "/api/v1/dashboard/training-zone-distribution",
        "/api/v1/dashboard/key-achievements",
    ]

    def test_all_dashboard_endpoints_return_200(self, client, sample_payload):
        """All dashboard endpoints should return 200 with valid payload."""
        for endpoint in self.DASHBOARD_ENDPOINTS:
            response = client.post(endpoint, json=sample_payload)
            assert response.status_code == 200, f"{endpoint} returned {response.status_code}"

    def test_all_dashboard_endpoints_return_user_id(self, client, sample_payload):
        """All dashboard responses should include the user_id from the request."""
        for endpoint in self.DASHBOARD_ENDPOINTS:
            response = client.post(endpoint, json=sample_payload)
            data = response.json()
            assert data["user_id"] == sample_payload["user_id"], f"{endpoint} has wrong user_id"

    def test_all_dashboard_endpoints_reject_empty_payload(self, client):
        """All dashboard endpoints should return 422 for empty payload."""
        for endpoint in self.DASHBOARD_ENDPOINTS:
            response = client.post(endpoint, json={})
            assert response.status_code == 422, f"{endpoint} accepted empty payload"

    def test_wrong_method_on_dashboard(self, client):
        """GET on POST-only dashboard endpoints should return 405."""
        for endpoint in self.DASHBOARD_ENDPOINTS:
            response = client.get(endpoint)
            assert response.status_code == 405, f"{endpoint} allowed GET"
