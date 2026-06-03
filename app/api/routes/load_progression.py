from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from app.schemas.strava import (
    AnalysisRequest,
    AverageWeeklyDistanceResponse,
    WeeklyVolumeProgressionResponse,
    ProgressionAnalysisResponse,
)
from app.services.analysis_cache_service import analysis_cache_service

router = APIRouter(prefix="/api/v1/load-progression", tags=["Load & Progression"])


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _format_zone_distribution(zones: dict[str, Any]) -> dict[str, int]:
    return {key: _safe_int(value) for key, value in zones.items()}


def _consistency_text(runs_per_week: float) -> str:
    if runs_per_week >= 5:
        return f"Excellent consistency at {runs_per_week:.1f} days per week."
    if runs_per_week >= 3:
        return f"Good consistency at {runs_per_week:.1f} days per week."
    return f"Lower consistency at {runs_per_week:.1f} days per week; aim for more regular sessions."


@router.post("/average-weekly-distance", response_model=AverageWeeklyDistanceResponse)
async def average_weekly_distance(payload: AnalysisRequest):
    request_payload = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id,
        cache_type="load_progression_average_weekly_distance",
        request_payload=request_payload,
    )
    if cached:
        return AverageWeeklyDistanceResponse(**cached)

    try:
        data: Dict[str, Any] = request_payload
        weekly = data.get("weekly_progression", {}) or {}
        zones = data.get("computed_training_metrics", {}).get(
            "heart_rate_zone_distribution_percent", {}
        ) or {}
        avg_distance = _safe_float(weekly.get("average_weekly_distance_km"))
        peak_distance = _safe_float(weekly.get("peak_weekly_distance_km"))
        max_increase = _safe_float(weekly.get("max_weekly_increase_percent"))
        zone_distribution = _format_zone_distribution(zones)

        narrative = (
            f"Your average weekly distance of {avg_distance:.1f} km shows a strong endurance base. "
            f"A peak week at {peak_distance:.1f} km and a controlled max increase of {max_increase:.1f}% "
            "suggest the program is progressing safely while maintaining volume."
        )

        recommendations: List[str] = []
        if avg_distance >= 70:
            recommendations.append("Maintain your high weekly load while keeping recovery sessions easy.")
        elif avg_distance >= 50:
            recommendations.append("This is a solid weekly volume; focus on consistency and quality sessions.")
        else:
            recommendations.append("Build volume gradually with an additional easy run or longer recovery run.")

        if max_increase <= 10:
            recommendations.append("Your progression is well-managed with low risk of overtraining.")
        else:
            recommendations.append("Monitor fatigue closely as weekly increases move above the 10% guideline.")

        response = AverageWeeklyDistanceResponse(
            user_id=payload.user_id,
            average_weekly_distance_km=avg_distance,
            peak_weekly_distance_km=peak_distance,
            max_weekly_increase_percent=max_increase,
            zone_distribution=zone_distribution,
            narrative=narrative,
            recommendations=recommendations,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}")

    analysis_cache_service.store_response(
        user_id=payload.user_id,
        cache_type="load_progression_average_weekly_distance",
        request_payload=request_payload,
        response_data=response.model_dump(mode="json"),
    )
    return response


@router.post("/weekly-volume-progression", response_model=WeeklyVolumeProgressionResponse)
async def weekly_volume_progression(payload: AnalysisRequest):
    request_payload = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id,
        cache_type="load_progression_weekly_volume_progression",
        request_payload=request_payload,
    )
    if cached:
        return WeeklyVolumeProgressionResponse(**cached)

    try:
        data: Dict[str, Any] = request_payload
        weekly = data.get("weekly_progression", {}) or {}
        avg_distance = _safe_float(weekly.get("average_weekly_distance_km"))
        peak_distance = _safe_float(weekly.get("peak_weekly_distance_km"))
        max_increase = _safe_float(weekly.get("max_weekly_increase_percent"))

        if max_increase <= 8:
            growth_descriptor = "Steady progression"
        elif max_increase <= 12:
            growth_descriptor = "Moderate progression"
        else:
            growth_descriptor = "Aggressive progression"

        volume_summary = (
            f"Weekly volume progression is healthy, with an average of {avg_distance:.1f} km and "
            f"a peak of {peak_distance:.1f} km. The program is increasing at about {max_increase:.1f}% per week, "
            "which supports adaptation if recovery is maintained."
        )

        recommended_advice: List[str] = [
            "Continue the current progression pattern if you feel recovered.",
            "Use easy days to preserve form and avoid fatigue build-up.",
        ]
        if max_increase > 12:
            recommended_advice.append(
                "Consider a short recovery week to prevent overload after high-volume weeks."
            )

        response = WeeklyVolumeProgressionResponse(
            user_id=payload.user_id,
            average_weekly_distance_km=avg_distance,
            peak_weekly_distance_km=peak_distance,
            max_weekly_increase_percent=max_increase,
            growth_descriptor=growth_descriptor,
            volume_summary=volume_summary,
            recommended_advice=recommended_advice,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}")

    analysis_cache_service.store_response(
        user_id=payload.user_id,
        cache_type="load_progression_weekly_volume_progression",
        request_payload=request_payload,
        response_data=response.model_dump(mode="json"),
    )
    return response


@router.post("/progression-analysis", response_model=ProgressionAnalysisResponse)
async def progression_analysis(payload: AnalysisRequest):
    request_payload = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id,
        cache_type="load_progression_progression_analysis",
        request_payload=request_payload,
    )
    if cached:
        return ProgressionAnalysisResponse(**cached)

    try:
        data: Dict[str, Any] = request_payload
        weekly = data.get("weekly_progression", {}) or {}
        run_counts = data.get("run_duration_tracking", {}) or {}
        total_runs = sum([_safe_int(run_counts.get(k, 0)) for k in run_counts])
        weeks = _safe_int(data.get("analysis_period", {}).get("weeks", 1))
        consistency = total_runs / max(1, weeks)
        max_increase = _safe_float(weekly.get("max_weekly_increase_percent"))
        recovery_weeks = 3 if max_increase <= 10 else 2 if max_increase <= 15 else 1

        growth_rate = (
            f"{max_increase:.1f}% average weekly increase, which is "
            + ("very safe" if max_increase <= 10 else "moderate" if max_increase <= 15 else "high")
        )
        summary = (
            f"Progression is managed well with {consistency:.1f} training days per week and "
            f"a recovery focus built into the block. The current load change is {growth_rate}."
        )

        recommendations: List[str] = [
            _consistency_text(consistency),
            "Keep the progression under 10% when possible to reduce injury risk.",
        ]
        if recovery_weeks < 3:
            recommendations.append(
                "Add an extra recovery week if you notice fatigue rising or performance dipping."
            )

        response = ProgressionAnalysisResponse(
            user_id=payload.user_id,
            weekly_growth_rate=growth_rate,
            consistency_days_per_week=round(consistency, 1),
            recovery_weeks=recovery_weeks,
            progression_summary=summary,
            recommendations=recommendations,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}")

    analysis_cache_service.store_response(
        user_id=payload.user_id,
        cache_type="load_progression_progression_analysis",
        request_payload=request_payload,
        response_data=response.model_dump(mode="json"),
    )
    return response
