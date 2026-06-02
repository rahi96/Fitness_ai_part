from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.services.metrics_engine import compute_metrics, build_achievements
from app.services.openai_service import render_analysis_text
from app.schemas.strava import (
    AnalysisRequest,
    PerformanceGrades,
    PerformanceGrade,
)

router = APIRouter(prefix="/api/v1/overview", tags=["Overview"])


@router.post("/ai-summary")
async def ai_summary(payload: AnalysisRequest):
    """
    Generate a concise AI-style summary for the provided training data.
    Uses existing template renderer and metrics/achievements helpers.
    """
    try:
        data: Dict[str, Any] = payload.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}")

    metrics = compute_metrics(data)
    achievements = build_achievements(data, metrics)

    plan_title = "Training Insights Summary"
    timeframe = f"{data.get('analysis_period', {}).get('weeks', '?')}-week analysis"

    narrative = (
        "This training block shows the core trends for the analyzed period: "
        f"easy running {metrics.get('easy_running')}%, weekly growth {metrics.get('weekly_growth')}%, "
        f"and overall performance score {metrics.get('training_performance')}.")

    summary_text = render_analysis_text(
        plan_title=plan_title,
        timeframe=timeframe,
        narrative=narrative,
        metrics=metrics,
        achievements=achievements,
    )

    return {"ai_summary": summary_text}


@router.post("/performance-grades", response_model=PerformanceGrades)
async def performance_grades(payload: AnalysisRequest):
    """
    Return simple performance grade descriptions for five areas:
    frequency, volume, intensity, recovery, progression.
    """
    try:
        data = payload.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}")

    weeks = int(data.get("analysis_period", {}).get("weeks", 1))

    # Frequency: estimate average runs per week from run_duration_tracking counts
    run_counts = data.get("run_duration_tracking", {}) or {}
    total_runs = sum([int(run_counts.get(k, 0)) for k in run_counts])
    avg_runs_per_week = total_runs / max(1, weeks)

    if avg_runs_per_week >= 5:
        freq_desc = f"Excellent frequency — ~{avg_runs_per_week:.1f} runs/week"
    elif avg_runs_per_week >= 3:
        freq_desc = f"Good frequency — ~{avg_runs_per_week:.1f} runs/week"
    elif avg_runs_per_week >= 1.5:
        freq_desc = f"Average frequency — ~{avg_runs_per_week:.1f} runs/week"
    else:
        freq_desc = f"Low frequency — ~{avg_runs_per_week:.1f} runs/week"

    # Volume: use average_weekly_distance_km
    weekly = data.get("weekly_progression", {}) or {}
    avg_weekly_km = float(weekly.get("average_weekly_distance_km", 0.0))
    if avg_weekly_km >= 70:
        vol_desc = f"Excellent volume — avg {avg_weekly_km:.1f} km/week"
    elif avg_weekly_km >= 50:
        vol_desc = f"Good volume — avg {avg_weekly_km:.1f} km/week"
    elif avg_weekly_km >= 30:
        vol_desc = f"Moderate volume — avg {avg_weekly_km:.1f} km/week"
    else:
        vol_desc = f"Low volume — avg {avg_weekly_km:.1f} km/week"

    # Intensity: check pace zone distribution polarization
    pace = data.get("computed_training_metrics", {}).get("pace_zone_distribution_percent", {}) or {}
    easy_pct = float(pace.get("easy_recovery", 0))
    tempo_pct = float(pace.get("tempo", 0))
    hard_pct = float(pace.get("hard", 0))

    if easy_pct >= 70 and hard_pct <= 20:
        int_desc = f"Excellent polarization ({easy_pct:.0f}% easy / {tempo_pct:.0f}% tempo / {hard_pct:.0f}% hard)"
    elif hard_pct >= 30:
        int_desc = f"High intensity focus ({hard_pct:.0f}% hard) — monitor recovery"
    else:
        int_desc = f"Balanced intensity ({easy_pct:.0f}% easy / {tempo_pct:.0f}% tempo / {hard_pct:.0f}% hard)"

    # Recovery: estimate from heart rate zone 1 share and efficiency indicators
    hr = data.get("computed_training_metrics", {}).get("heart_rate_zone_distribution_percent", {}) or {}
    zone1 = float(hr.get("zone_1", 0))
    eff = data.get("efficiency_indicators", {}) or {}
    hr_drift = eff.get("heart_rate_drift", "")
    if zone1 >= 40:
        rec_desc = f"Good recovery integration ({zone1:.0f}% zone 1). {hr_drift}"
    elif zone1 >= 20:
        rec_desc = f"Reasonable recovery ({zone1:.0f}% zone 1). {hr_drift}"
    else:
        rec_desc = f"Recovery may be insufficient ({zone1:.0f}% zone 1). {hr_drift}"

    # Progression: use max_weekly_increase_percent
    max_inc = float(weekly.get("max_weekly_increase_percent", 0.0))
    if max_inc <= 10:
        prog_desc = f"Safe progression ({max_inc:.1f}% max weekly increase)"
    elif max_inc <= 20:
        prog_desc = f"Moderate progression ({max_inc:.1f}% max weekly increase)"
    else:
        prog_desc = f"Aggressive progression ({max_inc:.1f}% max weekly increase) — risk of overload"

    return PerformanceGrades(
        volume=PerformanceGrade(description=vol_desc),
        frequency=PerformanceGrade(description=freq_desc),
        intensity=PerformanceGrade(description=int_desc),
        recovery=PerformanceGrade(description=rec_desc),
        progression=PerformanceGrade(description=prog_desc),
    )
