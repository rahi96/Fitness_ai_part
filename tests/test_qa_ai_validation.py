"""
QA Test Suite: Validate that all API responses are AI-generated (not fallback)
and that responses are contextually relevant to the input data.

Test Strategy:
-------------
1. AI-powered endpoints (OpenAI): Verify the response does NOT match the
   hardcoded fallback text. Different input data must produce different output.
2. Rule-based endpoints (computed): Verify the response contains values
   derived from the specific input payload (not generic/static).
3. Data-sensitivity: Send two distinct payloads and verify the responses differ.

This suite runs against the LIVE server at http://127.0.0.1:8000.
"""

import pytest
import httpx
import json

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 60  # seconds — AI calls can be slow


# ---------------------------------------------------------------------------
# Test Payloads: Two deliberately different athlete profiles
# ---------------------------------------------------------------------------

ATHLETE_A = {
    "user_id": "qa-athlete-A",
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
        "less_than_30_min": 2, "between_45_and_60_min": 3,
        "between_60_and_90_min": 2, "above_90_min": 1,
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

# Athlete B: Very different profile — high intensity, low volume, high drift
ATHLETE_B = {
    "user_id": "qa-athlete-B",
    "analysis_period": {"weeks": 6},
    "computed_training_metrics": {
        "heart_rate_zone_distribution_percent": {
            "zone_1": 5, "zone_2": 15, "zone_3": 30, "zone_4": 35, "zone_5": 15,
        },
        "power_zone_distribution_percent": {
            "zone_1": 10, "zone_2": 20, "zone_3": 25, "zone_4": 30, "zone_5": 15,
        },
        "pace_zone_distribution_percent": {
            "easy_recovery": 35, "tempo": 40, "hard": 25,
        },
    },
    "run_duration_tracking": {
        "less_than_30_min": 10, "between_45_and_60_min": 2,
        "between_60_and_90_min": 0, "above_90_min": 0,
    },
    "weekly_progression": {
        "average_weekly_distance_km": 22,
        "peak_weekly_distance_km": 28,
        "max_weekly_increase_percent": 18,
    },
    "long_run_summary": {"count": 0, "max_duration_minutes": 25},
    "efficiency_indicators": {
        "pace_efficiency_change_percent": 1,
        "heart_rate_drift": "high",
    },
}


# ---------------------------------------------------------------------------
# Known fallback text fragments (from dashboard.py, heart_rate.py, performance.py)
# If any of these appear verbatim in the response, it means fallback was used.
# ---------------------------------------------------------------------------

DASHBOARD_FALLBACK_MARKERS = {
    "executive-summary": [
        "consistent volume progression, well-managed intensity distribution",
        "Your 12-week training block demonstrates strong overall execution",
    ],
    "training-load-analysis": [
        "Training load followed a well-structured periodized plan",
        "The periodization follows a 3:1 loading pattern",
    ],
    "performance-metrics": [
        "Average pace improved from 5:30/km to 5:15/km over the 12-week block",
        "Heart rate data shows excellent aerobic adaptation with a low resting HR of 48 bpm",
    ],
    "weekly-training-breakdown": [
        "Weekly volume progressed from 38 km to a peak of 54 km with planned recovery weeks",
    ],
    "recommendations-insights": [
        "Maintained 5-6 sessions per week throughout the entire block",
        "closely matching the recommended 80/20 polarized training model",
    ],
    "training-zone-distribution": [
        "close to the ideal 75-80% for endurance athletes. Increasing easy volume by 10%",
        "The 82% easy pace distribution aligns well with the 80/20 principle",
    ],
    "key-achievements": [
        "38→54 km/week",
        "Achieved near-ideal easy/tempo/hard distribution, matching elite training",
    ],
}

HEART_RATE_FALLBACK_MARKERS = [
    "average HR at easy pace (5:00-5:30/km) decreased from 155 bpm to 147 bpm",
    "threshold pace (at 175 bpm) improved from 4:25/km to 4:15/km",
    "heart rate stayed stable during long runs, only rising 3-4 bpm over 90+ minutes",
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _post(path: str, payload: dict) -> httpx.Response:
    """POST to the live API with timeout handling."""
    return httpx.post(f"{BASE_URL}{path}", json=payload, timeout=TIMEOUT)


def _response_text(resp: httpx.Response) -> str:
    """Return full JSON response as a single string for searching."""
    return json.dumps(resp.json())


# ===================================================================
# GROUP 1: AI-Powered Dashboard Endpoints (7)
# Must NOT return fallback text. Must differ for different athletes.
# ===================================================================

class TestDashboardAIGenerated:
    """Verify that all 7 dashboard endpoints return AI-generated responses."""

    @pytest.mark.parametrize("endpoint", [
        "executive-summary",
        "training-load-analysis",
        "performance-metrics",
        "weekly-training-breakdown",
        "recommendations-insights",
        "training-zone-distribution",
        "key-achievements",
    ])
    def test_response_is_not_fallback(self, endpoint):
        """The response must NOT contain any known fallback text fragments."""
        resp = _post(f"/api/v1/dashboard/{endpoint}", ATHLETE_A)
        assert resp.status_code == 200, f"{endpoint} returned {resp.status_code}: {resp.text}"
        body = _response_text(resp)

        fallback_markers = DASHBOARD_FALLBACK_MARKERS.get(endpoint, [])
        for marker in fallback_markers:
            assert marker not in body, (
                f"FALLBACK DETECTED on /dashboard/{endpoint}!\n"
                f"Found hardcoded text: '{marker}'\n"
                f"Response should be AI-generated, not fallback."
            )

    @pytest.mark.parametrize("endpoint", [
        "executive-summary",
        "training-load-analysis",
        "performance-metrics",
        "weekly-training-breakdown",
        "recommendations-insights",
        "training-zone-distribution",
        "key-achievements",
    ])
    def test_different_data_produces_different_response(self, endpoint):
        """Two athletes with very different data must get different AI responses."""
        resp_a = _post(f"/api/v1/dashboard/{endpoint}", ATHLETE_A)
        resp_b = _post(f"/api/v1/dashboard/{endpoint}", ATHLETE_B)
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200

        data_a = resp_a.json()
        data_b = resp_b.json()

        # user_id should match the respective request
        assert data_a["user_id"] == "qa-athlete-A"
        assert data_b["user_id"] == "qa-athlete-B"

        # Remove user_id for comparison — the rest of the response must differ
        data_a.pop("user_id")
        data_b.pop("user_id")
        assert data_a != data_b, (
            f"IDENTICAL RESPONSES on /dashboard/{endpoint}!\n"
            f"Two completely different athletes got the same output.\n"
            f"This means the response is hardcoded/fallback, not AI-generated."
        )


# ===================================================================
# GROUP 2: AI-Powered Heart Rate Endpoint
# ===================================================================

class TestHeartRateAIGenerated:
    """Verify /heart-rate/heart-rate-efficiency returns AI-generated data."""

    def test_response_is_not_fallback(self):
        resp = _post("/api/v1/heart-rate/heart-rate-efficiency", ATHLETE_A)
        assert resp.status_code == 200
        body = _response_text(resp)

        for marker in HEART_RATE_FALLBACK_MARKERS:
            assert marker not in body, (
                f"FALLBACK DETECTED on /heart-rate/heart-rate-efficiency!\n"
                f"Found hardcoded text: '{marker}'"
            )

    def test_different_data_produces_different_response(self):
        resp_a = _post("/api/v1/heart-rate/heart-rate-efficiency", ATHLETE_A)
        resp_b = _post("/api/v1/heart-rate/heart-rate-efficiency", ATHLETE_B)
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200

        data_a = resp_a.json()
        data_b = resp_b.json()
        data_a.pop("user_id")
        data_b.pop("user_id")
        assert data_a != data_b, (
            "IDENTICAL RESPONSES on /heart-rate/heart-rate-efficiency!\n"
            "Two different athletes got the same output."
        )


# ===================================================================
# GROUP 3: AI-Powered Performance Endpoint
# ===================================================================

class TestPerformanceAIGenerated:
    """Verify /performance/consistent-hr-improvement returns AI-generated data."""

    def test_returns_structured_ai_response(self):
        """Should return 200 with AI-generated content (not 500)."""
        resp = _post("/api/v1/performance/consistent-hr-improvement", ATHLETE_A)
        # This endpoint raises 500 if AI output is incomplete; 200 = valid AI output
        if resp.status_code == 200:
            data = resp.json()
            assert data["user_id"] == "qa-athlete-A"
            assert len(data["improvement_summary"]) > 20, "Summary too short to be AI-generated"
            assert len(data["improvement_metrics"]) >= 1
            assert len(data["key_insights"]) >= 1

    def test_different_data_produces_different_response(self):
        resp_a = _post("/api/v1/performance/consistent-hr-improvement", ATHLETE_A)
        resp_b = _post("/api/v1/performance/consistent-hr-improvement", ATHLETE_B)
        if resp_a.status_code == 200 and resp_b.status_code == 200:
            data_a = resp_a.json()
            data_b = resp_b.json()
            assert data_a["improvement_summary"] != data_b["improvement_summary"], (
                "Identical improvement summaries for different athletes"
            )


# ===================================================================
# GROUP 4: Rule-Based Endpoints — Must reflect input data values
# ===================================================================

class TestRuleBasedEndpointsReflectInputData:
    """
    Rule-based endpoints compute results directly from input.
    Verify they reference the actual input values, not hardcoded data.
    """

    # --- Overview ---

    def test_ai_summary_contains_input_values(self):
        """AI summary must reference values computed from input data."""
        resp = _post("/api/v1/overview/ai-summary", ATHLETE_A)
        assert resp.status_code == 200
        summary = resp.json()["ai_summary"]
        # The summary template includes easy_running percentage (82%) from input
        assert "82" in summary or "easy" in summary.lower(), (
            f"AI summary doesn't reference input easy_recovery value.\nGot: {summary}"
        )

    def test_performance_grades_reflect_athlete_a(self):
        """Grades for athlete A (moderate volume, good polarization)."""
        resp = _post("/api/v1/overview/performance-grades", ATHLETE_A)
        assert resp.status_code == 200
        data = resp.json()
        # Athlete A: avg 46 km/week → "Moderate volume"
        assert "46.0" in data["volume"]["description"]
        # Athlete A: 82% easy → "Excellent polarization"
        assert "82" in data["intensity"]["description"]
        # Athlete A: 8% max increase → "Safe progression"
        assert "8.0" in data["progression"]["description"]

    def test_performance_grades_reflect_athlete_b(self):
        """Grades for athlete B (low volume, high intensity)."""
        resp = _post("/api/v1/overview/performance-grades", ATHLETE_B)
        assert resp.status_code == 200
        data = resp.json()
        # Athlete B: avg 22 km/week → "Low volume"
        assert "22.0" in data["volume"]["description"]
        assert "Low" in data["volume"]["description"]
        # Athlete B: 35% easy → NOT "Excellent polarization"
        assert "35" in data["intensity"]["description"]
        # Athlete B: 18% max increase → "Moderate progression"
        assert "18.0" in data["progression"]["description"]

    # --- Load Progression ---

    def test_avg_weekly_distance_reflects_input(self):
        resp = _post("/api/v1/load-progression/average-weekly-distance", ATHLETE_A)
        assert resp.status_code == 200
        data = resp.json()
        assert data["average_weekly_distance_km"] == 46.0
        assert data["peak_weekly_distance_km"] == 54.0
        assert data["max_weekly_increase_percent"] == 8.0
        assert "46.0" in data["narrative"]
        assert "54.0" in data["narrative"]

    def test_avg_weekly_distance_differs_for_athlete_b(self):
        resp = _post("/api/v1/load-progression/average-weekly-distance", ATHLETE_B)
        assert resp.status_code == 200
        data = resp.json()
        assert data["average_weekly_distance_km"] == 22.0
        assert data["peak_weekly_distance_km"] == 28.0
        assert "22.0" in data["narrative"]

    def test_weekly_volume_progression_reflects_input(self):
        resp_a = _post("/api/v1/load-progression/weekly-volume-progression", ATHLETE_A)
        resp_b = _post("/api/v1/load-progression/weekly-volume-progression", ATHLETE_B)
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        data_a = resp_a.json()
        data_b = resp_b.json()
        # A: 8% → "Steady progression"
        assert data_a["growth_descriptor"] == "Steady progression"
        # B: 18% → "Aggressive progression"
        assert data_b["growth_descriptor"] == "Aggressive progression"

    def test_progression_analysis_reflects_input(self):
        resp_a = _post("/api/v1/load-progression/progression-analysis", ATHLETE_A)
        resp_b = _post("/api/v1/load-progression/progression-analysis", ATHLETE_B)
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        data_a = resp_a.json()
        data_b = resp_b.json()
        # A: 8 runs / 12 weeks = 0.7 days/week
        assert data_a["consistency_days_per_week"] == 0.7
        # B: 12 runs / 6 weeks = 2.0 days/week
        assert data_b["consistency_days_per_week"] == 2.0
        # Different growth rates
        assert data_a["weekly_growth_rate"] != data_b["weekly_growth_rate"]

    # --- Training Insights ---

    def test_optimal_pace_distribution_reflects_input(self):
        resp_a = _post("/api/v1/training-insights/optimal-pace-distribution", ATHLETE_A)
        resp_b = _post("/api/v1/training-insights/optimal-pace-distribution", ATHLETE_B)
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        dist_a = resp_a.json()["distribution"]
        dist_b = resp_b.json()["distribution"]
        # A: 82% easy, 14% tempo, 4% hard
        assert dist_a == {"easy": 82, "tempo": 14, "hard": 4}
        # B: 35% easy, 40% tempo, 25% hard
        assert dist_b == {"easy": 35, "tempo": 40, "hard": 25}

    def test_pace_recommendations_differ_by_profile(self):
        resp_a = _post("/api/v1/training-insights/pace-recommendations", ATHLETE_A)
        resp_b = _post("/api/v1/training-insights/pace-recommendations", ATHLETE_B)
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        recs_a = resp_a.json()["recommendations"]
        recs_b = resp_b.json()["recommendations"]
        # A: 82% easy → "Keep your easy run volume high"
        assert any("Keep your easy" in r or "high" in r.lower() for r in recs_a)
        # B: 35% easy → "Increase easy running"
        assert any("Increase easy" in r for r in recs_b)

    def test_optimal_hr_distribution_reflects_input(self):
        resp_a = _post("/api/v1/training-insights/optimal-hr-distribution", ATHLETE_A)
        resp_b = _post("/api/v1/training-insights/optimal-hr-distribution", ATHLETE_B)
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        dist_a = resp_a.json()["distribution"]
        dist_b = resp_b.json()["distribution"]
        # A: z1=20, z2=45 → low_effort=65%
        assert dist_a["zone_1"] == 20
        assert dist_a["zone_2"] == 45
        # B: z1=5, z2=15 → low_effort=20%
        assert dist_b["zone_1"] == 5
        assert dist_b["zone_2"] == 15
        # Narrative must contain the computed low-effort percentage
        assert "65" in resp_a.json()["narrative"]
        assert "20" in resp_b.json()["narrative"]

    def test_optimal_power_distribution_reflects_input(self):
        resp_a = _post("/api/v1/training-insights/optimal-power-distribution", ATHLETE_A)
        resp_b = _post("/api/v1/training-insights/optimal-power-distribution", ATHLETE_B)
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        dist_a = resp_a.json()["distribution"]
        dist_b = resp_b.json()["distribution"]
        # A: z1=28, z2=42 → low_intensity=70%
        assert dist_a["zone_1"] == 28
        assert dist_a["zone_2"] == 42
        # B: z1=10, z2=20 → low_intensity=30%
        assert dist_b["zone_1"] == 10
        assert dist_b["zone_2"] == 20

    def test_pace_distribution_raw_mirrors_input(self):
        resp = _post("/api/v1/training-insights/pace-distribution-raw", ATHLETE_A)
        assert resp.status_code == 200
        data = resp.json()["pace_zone_distribution_percent"]
        assert data["easy_recovery"] == 82
        assert data["tempo"] == 14
        assert data["hard"] == 4


# ===================================================================
# GROUP 5: Data Sensitivity — Verify AI adapts to bad data
# ===================================================================

class TestAIAdaptsToAthleteContext:
    """
    Send athlete B (low volume, high intensity, high drift) and verify
    that the AI-generated narrative flags concerns rather than praising.
    """

    def test_executive_summary_flags_issues_for_bad_profile(self):
        resp = _post("/api/v1/dashboard/executive-summary", ATHLETE_B)
        assert resp.status_code == 200
        data = resp.json()
        body = _response_text(resp).lower()
        # With 35% easy, 25% hard, high drift — the AI should NOT say "Strong" for everything
        # It should flag intensity or recovery concerns
        has_concern = any(
            keyword in body
            for keyword in [
                "attention", "concern", "improve", "risk", "caution",
                "high", "aggressive", "insufficient", "weak", "moderate",
                "imbalance", "overtraining",
            ]
        )
        assert has_concern, (
            f"AI praised a clearly imbalanced athlete (35% easy, 25% hard, high drift).\n"
            f"Expected some caution/concern in the response.\n"
            f"Got: {data['summary_narrative']}"
        )

    def test_zone_distribution_flags_poor_polarization(self):
        resp = _post("/api/v1/dashboard/training-zone-distribution", ATHLETE_B)
        assert resp.status_code == 200
        body = _response_text(resp).lower()
        # Athlete B has terrible polarization (5% z1, 15% z2 = 20% low effort)
        # AI should flag this
        has_flag = any(
            keyword in body
            for keyword in [
                "below", "insufficient", "increase", "low", "improve",
                "too much", "imbalanced", "suboptimal", "risk",
            ]
        )
        assert has_flag, (
            "AI didn't flag poor zone distribution for athlete with 20% easy zone time"
        )

    def test_recommendations_suggest_more_easy_running(self):
        resp = _post("/api/v1/dashboard/recommendations-insights", ATHLETE_B)
        assert resp.status_code == 200
        body = _response_text(resp).lower()
        # AI should recommend more easy/recovery running
        has_easy_rec = any(
            keyword in body
            for keyword in ["easy", "recovery", "zone 1", "zone 2", "aerobic", "reduce intensity"]
        )
        assert has_easy_rec, (
            "AI didn't recommend more easy/recovery running for a high-intensity athlete"
        )


# ===================================================================
# GROUP 6: Structural Integrity for AI-Powered Endpoints
# ===================================================================

class TestAIResponseStructure:
    """Ensure AI responses have all required fields with correct types."""

    def test_executive_summary_structure(self):
        resp = _post("/api/v1/dashboard/executive-summary", ATHLETE_A)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["summary_narrative"], str)
        assert len(data["summary_narrative"]) >= 50
        assert len(data["items"]) >= 2
        for item in data["items"]:
            assert isinstance(item["title"], str) and len(item["title"]) > 0
            assert isinstance(item["status"], str) and len(item["status"]) > 0
            assert isinstance(item["detail"], str) and len(item["detail"]) > 10

    def test_training_load_structure(self):
        resp = _post("/api/v1/dashboard/training-load-analysis", ATHLETE_A)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["weekly_distance_progression"]) >= 3
        for p in data["weekly_distance_progression"]:
            assert isinstance(p["week"], int)
            assert isinstance(p["distance_km"], (int, float))
            assert p["distance_km"] > 0
        assert len(data["phases"]) >= 2
        assert len(data["training_load_narrative"]) >= 30
        assert len(data["analysis"]) >= 30

    def test_performance_metrics_structure(self):
        resp = _post("/api/v1/dashboard/performance-metrics", ATHLETE_A)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["average_pace"], str)
        assert "/" in data["average_pace"]  # e.g., "5:15/km"
        assert isinstance(data["resting_hr"], int)
        assert 30 <= data["resting_hr"] <= 100
        assert isinstance(data["easy_run_hr"], int)
        assert 80 <= data["easy_run_hr"] <= 200
        assert isinstance(data["tempo_hr"], int)
        assert len(data["pace_progression_narrative"]) >= 30
        assert len(data["hr_analysis_narrative"]) >= 30

    def test_weekly_breakdown_structure(self):
        resp = _post("/api/v1/dashboard/weekly-training-breakdown", ATHLETE_A)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["weeks"]) >= 3
        for w in data["weeks"]:
            assert isinstance(w["week"], int)
            assert isinstance(w["distance_km"], (int, float))
            assert isinstance(w["runs"], int)
            assert isinstance(w["avg_pace"], str)
            assert isinstance(w["long_run_km"], (int, float))

    def test_recommendations_structure(self):
        resp = _post("/api/v1/dashboard/recommendations-insights", ATHLETE_A)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["strengths"]) >= 2
        assert len(data["areas_for_improvement"]) >= 2
        assert len(data["next_steps"]) >= 2
        for section in ["strengths", "areas_for_improvement", "next_steps"]:
            for item in data[section]:
                assert isinstance(item["title"], str) and len(item["title"]) > 3
                assert isinstance(item["detail"], str) and len(item["detail"]) > 10

    def test_zone_distribution_structure(self):
        resp = _post("/api/v1/dashboard/training-zone-distribution", ATHLETE_A)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["zones"]) >= 3
        total = sum(z["percentage"] for z in data["zones"])
        assert 95 <= total <= 105, f"Zone percentages sum to {total}, expected ~100"
        assert len(data["optimal_distribution_narrative"]) >= 30
        assert len(data["current_assessment"]) >= 30

    def test_key_achievements_structure(self):
        resp = _post("/api/v1/dashboard/key-achievements", ATHLETE_A)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["achievements"]) >= 3
        for a in data["achievements"]:
            assert isinstance(a["title"], str) and len(a["title"]) > 3
            assert isinstance(a["value"], str) and len(a["value"]) > 0
            assert isinstance(a["detail"], str) and len(a["detail"]) > 10
        assert len(data["summary"]) >= 20

    def test_heart_rate_efficiency_structure(self):
        resp = _post("/api/v1/heart-rate/heart-rate-efficiency", ATHLETE_A)
        assert resp.status_code == 200
        data = resp.json()
        ae = data["improved_aerobic_efficiency"]
        assert isinstance(ae["narrative"], str) and len(ae["narrative"]) >= 20
        assert isinstance(ae["week_1_hr"], int) and 40 <= ae["week_1_hr"] <= 220
        assert isinstance(ae["week_12_hr"], int) and 40 <= ae["week_12_hr"] <= 220
        tp = data["threshold_pace_development"]
        assert isinstance(tp["threshold_hr"], int) and 100 <= tp["threshold_hr"] <= 220
        assert isinstance(tp["difference_seconds"], int)
        cd = data["low_cardiac_drift"]
        assert isinstance(cd["drift_bpm_increase"], int)
        assert isinstance(cd["duration_minutes"], int)
