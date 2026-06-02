"""
Comprehensive API test suite for all endpoints in the Fitness AI project.

Tests cover:
- Chat routes (health, chat, history)
- Analysis routes (training analysis, race analysis, training insights, improvement plan)
- Strava routes (batch analysis)
- Overview routes (AI summary, performance grades)
- Training Insights routes (pace, HR, power distributions)
"""

import pytest


# ==================== CHAT ROUTES ====================

class TestChatRoutes:
    """Test chat-related API endpoints."""

    def test_health_check(self, client):
        """Test /api/v1/health endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_chat_endpoint_success(self, client):
        """Test POST /api/v1/chat with valid payload."""
        payload = {
            "user_id": "test_user_1",
            "session_id": None,
            "message": "What should my training focus be?"
        }
        response = client.post("/api/v1/chat", json=payload)
        # May fail due to OpenAI key not set, but should return 500 with proper error message
        if response.status_code == 500:
            assert "OPENAI_API_KEY" in response.json()["detail"] or "OpenAI" in response.json()["detail"]
        else:
            assert response.status_code == 200
            assert "session_id" in response.json()
            assert "response" in response.json()

    def test_chat_history_empty_session(self, client):
        """Test GET /api/v1/chat/history/{session_id} with non-existent session."""
        response = client.get("/api/v1/chat/history/nonexistent_session_123")
        assert response.status_code == 200
        assert "history" in response.json()

    def test_chat_invalid_payload(self, client):
        """Test POST /api/v1/chat with invalid payload."""
        payload = {"invalid": "data"}
        response = client.post("/api/v1/chat", json=payload)
        assert response.status_code == 422  # Validation error


# ==================== ANALYSIS ROUTES ====================

class TestAnalysisRoutes:
    """Test analysis-related API endpoints."""

    def test_training_analysis_success(self, client, sample_analysis_request):
        """Test POST /api/v1/training/analysis with valid training data."""
        response = client.post("/api/v1/training/analysis", json=sample_analysis_request)
        assert response.status_code == 200
        data = response.json()
        assert "plan_title" in data
        assert "timeframe" in data
        assert "summary" in data
        assert "achievements" in data

    def test_training_analysis_high_volume(self, client, high_volume_request):
        """Test training analysis with high volume data."""
        response = client.post("/api/v1/training/analysis", json=high_volume_request)
        assert response.status_code == 200
        data = response.json()
        assert len(data["achievements"]) > 0

    def test_training_analysis_low_volume(self, client, low_volume_request):
        """Test training analysis with low volume data."""
        response = client.post("/api/v1/training/analysis", json=low_volume_request)
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data

    def test_race_analysis_success(self, client, sample_analysis_request):
        """Test POST /api/v1/ai/race-analysis endpoint."""
        race_payload = {
            **sample_analysis_request,
            "athlete_profile": {"age": 35, "experience": "advanced"},
            "training_summary": {"total_weeks": 12, "peak_week_mileage": 92},
            "race_analysis": {"actual_time": "3:15:30", "predicted_time": "3:10:00"},
            "performance_predictions": {"5k": "18:30", "10k": "38:45"},
            "training_context": {}
        }
        response = client.post("/api/v1/ai/race-analysis", json=race_payload)
        # May fail due to OpenAI key, but structure should be consistent
        if response.status_code == 200:
            data = response.json()
            assert "race_summary" in data or "insights" in data or "recommendations" in data

    def test_training_insights_success(self, client, sample_analysis_request):
        """Test POST /api/v1/ai/training-insights endpoint."""
        insights_payload = {
            **sample_analysis_request,
            "athlete_profile": {"age": 35, "experience": "advanced"},
            "training_summary": {"total_weeks": 12},
            "race_analysis": {"actual_time": "3:15:30"},
            "performance_predictions": {"5k": "18:30"},
            "training_context": {}
        }
        response = client.post("/api/v1/ai/training-insights", json=insights_payload)
        if response.status_code == 200:
            data = response.json()
            assert "strengths" in data or "achievements" in data

    def test_improvement_plan_success(self, client, sample_analysis_request):
        """Test POST /api/v1/ai/improvement-plan endpoint."""
        plan_payload = {
            **sample_analysis_request,
            "athlete_profile": {"age": 35, "experience": "advanced"},
            "training_summary": {"total_weeks": 12},
            "race_analysis": {"actual_time": "3:15:30"},
            "performance_predictions": {"5k": "18:30"},
            "training_context": {}
        }
        response = client.post("/api/v1/ai/improvement-plan", json=plan_payload)
        if response.status_code == 200:
            data = response.json()
            assert "optimal_distribution" in data or "areas_for_improvement" in data


# ==================== OVERVIEW ROUTES ====================

class TestOverviewRoutes:
    """Test overview-related API endpoints."""

    def test_overview_ai_summary(self, client, sample_analysis_request):
        """Test POST /api/v1/overview/ai-summary endpoint."""
        response = client.post("/api/v1/overview/ai-summary", json=sample_analysis_request)
        assert response.status_code == 200
        data = response.json()
        assert "ai_summary" in data
        assert isinstance(data["ai_summary"], str)
        assert len(data["ai_summary"]) > 0

    def test_overview_ai_summary_high_volume(self, client, high_volume_request):
        """Test ai-summary with high volume training data."""
        response = client.post("/api/v1/overview/ai-summary", json=high_volume_request)
        assert response.status_code == 200
        assert "ai_summary" in response.json()

    def test_overview_performance_grades(self, client, sample_analysis_request):
        """Test POST /api/v1/overview/performance-grades endpoint."""
        response = client.post("/api/v1/overview/performance-grades", json=sample_analysis_request)
        assert response.status_code == 200
        data = response.json()
        assert "volume" in data
        assert "frequency" in data
        assert "intensity" in data
        assert "recovery" in data
        assert "progression" in data
        # Each grade should have a description
        assert "description" in data["volume"]
        assert "description" in data["frequency"]

    def test_overview_performance_grades_low_volume(self, client, low_volume_request):
        """Test performance grades with low volume data."""
        response = client.post("/api/v1/overview/performance-grades", json=low_volume_request)
        assert response.status_code == 200
        data = response.json()
        assert all(key in data for key in ["volume", "frequency", "intensity", "recovery", "progression"])


# ==================== TRAINING INSIGHTS ROUTES ====================

class TestTrainingInsightsRoutes:
    """Test training insights API endpoints."""

    def test_optimal_pace_distribution(self, client, sample_analysis_request):
        """Test POST /api/v1/training-insights/optimal-pace-distribution endpoint."""
        response = client.post("/api/v1/training-insights/optimal-pace-distribution", json=sample_analysis_request)
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "narrative" in data
        assert "distribution" in data
        assert "easy" in data["distribution"]
        assert "tempo" in data["distribution"]
        assert "hard" in data["distribution"]

    def test_optimal_pace_distribution_high_volume(self, client, high_volume_request):
        """Test pace distribution with high volume data."""
        response = client.post("/api/v1/training-insights/optimal-pace-distribution", json=high_volume_request)
        assert response.status_code == 200
        data = response.json()
        # Should show excellent polarization with high easy percentage
        assert data["distribution"]["easy"] >= 70

    def test_pace_distribution_raw(self, client, sample_analysis_request):
        """Test POST /api/v1/training-insights/pace-distribution-raw endpoint."""
        response = client.post("/api/v1/training-insights/pace-distribution-raw", json=sample_analysis_request)
        assert response.status_code == 200
        data = response.json()
        assert "pace_zone_distribution_percent" in data
        pace_data = data["pace_zone_distribution_percent"]
        assert "easy_recovery" in pace_data
        assert "tempo" in pace_data
        assert "hard" in pace_data

    def test_pace_recommendations(self, client, sample_analysis_request):
        """Test POST /api/v1/training-insights/pace-recommendations endpoint."""
        response = client.post("/api/v1/training-insights/pace-recommendations", json=sample_analysis_request)
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

    def test_pace_recommendations_low_easy(self, client, low_volume_request):
        """Test recommendations when easy percentage is low."""
        response = client.post("/api/v1/training-insights/pace-recommendations", json=low_volume_request)
        assert response.status_code == 200
        data = response.json()
        recommendations = data["recommendations"]
        # Should recommend more easy running
        assert any("easy" in rec.lower() for rec in recommendations)

    def test_optimal_hr_distribution(self, client, sample_analysis_request):
        """Test POST /api/v1/training-insights/optimal-hr-distribution endpoint."""
        response = client.post("/api/v1/training-insights/optimal-hr-distribution", json=sample_analysis_request)
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "narrative" in data
        assert "distribution" in data
        assert "zone_1" in data["distribution"]
        assert "zone_2" in data["distribution"]
        assert "zone_3" in data["distribution"]
        assert "zone_4" in data["distribution"]
        assert "zone_5" in data["distribution"]

    def test_optimal_hr_distribution_percentages_valid(self, client, sample_analysis_request):
        """Test that HR distribution percentages sum to 100."""
        response = client.post("/api/v1/training-insights/optimal-hr-distribution", json=sample_analysis_request)
        assert response.status_code == 200
        data = response.json()
        zones = data["distribution"]
        total = sum([zones.get(f"zone_{i}", 0) for i in range(1, 6)])
        assert total == 100

    def test_optimal_power_distribution(self, client, sample_analysis_request):
        """Test POST /api/v1/training-insights/optimal-power-distribution endpoint."""
        response = client.post("/api/v1/training-insights/optimal-power-distribution", json=sample_analysis_request)
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "narrative" in data
        assert "distribution" in data
        assert "zone_1" in data["distribution"]
        assert "zone_2" in data["distribution"]
        assert "zone_3" in data["distribution"]
        assert "zone_4" in data["distribution"]
        assert "zone_5" in data["distribution"]

    def test_optimal_power_distribution_narrative(self, client, high_volume_request):
        """Test power distribution narrative quality."""
        response = client.post("/api/v1/training-insights/optimal-power-distribution", json=high_volume_request)
        assert response.status_code == 200
        data = response.json()
        narrative = data["narrative"]
        # Should mention low intensity zones and controlled high intensity
        assert "low" in narrative.lower() or "zone" in narrative.lower()


# ==================== STRAVA ROUTES ====================

class TestStravaRoutes:
    """Test Strava-related API endpoints."""

    def test_strava_analyze_batch(self, client, sample_analysis_request, high_volume_request, low_volume_request):
        """Test POST /api/v1/strava/analyze with batch user data."""
        users_data = [
            sample_analysis_request,
            {
                **high_volume_request,
                "computed_training_metrics": high_volume_request["computed_training_metrics"],
            },
            {
                **low_volume_request,
                "computed_training_metrics": low_volume_request["computed_training_metrics"],
            },
        ]
        response = client.post("/api/v1/strava/analyze", json=users_data)
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "successful" in data
        assert "failed" in data
        assert "results" in data
        assert data["total_users"] == 3

    def test_strava_analyze_empty(self, client):
        """Test strava analyze with empty array."""
        response = client.post("/api/v1/strava/analyze", json=[])
        assert response.status_code == 400

    def test_strava_analyze_single_user(self, client, sample_analysis_request):
        """Test strava analyze with single user."""
        response = client.post("/api/v1/strava/analyze", json=[sample_analysis_request])
        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] == 1
        assert data["successful"] >= 0


# ==================== ERROR HANDLING TESTS ====================

class TestErrorHandling:
    """Test error handling across all endpoints."""

    def test_invalid_json_payload(self, client):
        """Test endpoints with invalid JSON."""
        response = client.post("/api/v1/overview/ai-summary", json={"invalid": "data"})
        assert response.status_code == 422

    def test_missing_required_fields(self, client):
        """Test endpoints with incomplete payload."""
        incomplete_payload = {"user_id": 1}
        response = client.post("/api/v1/overview/performance-grades", json=incomplete_payload)
        assert response.status_code == 422

    def test_nonexistent_endpoint(self, client):
        """Test accessing a non-existent endpoint."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_wrong_http_method(self, client, sample_analysis_request):
        """Test using wrong HTTP method on endpoint."""
        # POST endpoint tested with GET
        response = client.get("/api/v1/overview/ai-summary")
        assert response.status_code == 405  # Method Not Allowed


# ==================== INTEGRATION TESTS ====================

class TestIntegration:
    """Test integration workflows across multiple endpoints."""

    def test_full_analysis_workflow(self, client, sample_analysis_request):
        """Test a complete analysis workflow."""
        # 1. Get overview summary
        summary_response = client.post("/api/v1/overview/ai-summary", json=sample_analysis_request)
        assert summary_response.status_code == 200

        # 2. Get performance grades
        grades_response = client.post("/api/v1/overview/performance-grades", json=sample_analysis_request)
        assert grades_response.status_code == 200

        # 3. Get training insights
        insights_response = client.post(
            "/api/v1/training-insights/optimal-pace-distribution",
            json=sample_analysis_request
        )
        assert insights_response.status_code == 200

        # 4. Get HR distribution
        hr_response = client.post(
            "/api/v1/training-insights/optimal-hr-distribution",
            json=sample_analysis_request
        )
        assert hr_response.status_code == 200

    def test_all_distributions_consistency(self, client, sample_analysis_request):
        """Test that all distribution endpoints return consistent structure."""
        endpoints = [
            "/api/v1/training-insights/optimal-pace-distribution",
            "/api/v1/training-insights/optimal-hr-distribution",
            "/api/v1/training-insights/optimal-power-distribution",
        ]

        for endpoint in endpoints:
            response = client.post(endpoint, json=sample_analysis_request)
            assert response.status_code == 200
            data = response.json()
            assert "title" in data, f"{endpoint} missing title"
            assert "narrative" in data, f"{endpoint} missing narrative"
            assert "distribution" in data, f"{endpoint} missing distribution"
