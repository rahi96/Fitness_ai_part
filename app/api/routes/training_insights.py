from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.schemas.strava import AnalysisRequest

router = APIRouter(prefix="/api/v1/training-insights", tags=["Training Insights"])


@router.post("/optimal-pace-distribution")
async def optimal_pace_distribution(payload: AnalysisRequest):
    """Analyze pace distribution and return an AI-style summary.

    This endpoint synthesizes a short narrative describing how the athlete's
    pace distribution maps to polarized training principles (mirrors the provided image).
    """
    try:
        data: Dict[str, Any] = payload.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}")

    pace = data.get("computed_training_metrics", {}).get("pace_zone_distribution_percent", {}) or {}
    easy = float(pace.get("easy_recovery", 0))
    tempo = float(pace.get("tempo", 0))
    hard = float(pace.get("hard", 0))

    total = easy + tempo + hard
    # Normalize to percentages if values appear as absolute distances
    if total > 0 and total != 100:
        easy_pct = round((easy / total) * 100)
        tempo_pct = round((tempo / total) * 100)
        hard_pct = round((hard / total) * 100)
    else:
        easy_pct = int(easy)
        tempo_pct = int(tempo)
        hard_pct = int(hard)

    majority = "easy zones (Zone 1-2)" if easy_pct >= 50 else ("tempo/higher-intensity zones" if tempo_pct + hard_pct >= 50 else "mixed zones")

    narrative = (
        f"Your pace distribution shows excellent adherence to polarized training principles. "
        f"The majority of your running ({easy_pct}% ) was in {majority}, allowing for proper recovery while building aerobic base. "
        f"This distribution helps athletes target specific training adaptations each week and maintain consistency throughout the training block."
    )

    return {"title": "Optimal Pace Distribution", "narrative": narrative, "distribution": {"easy": easy_pct, "tempo": tempo_pct, "hard": hard_pct}}


@router.post("/pace-distribution-raw")
async def pace_distribution_raw(payload: AnalysisRequest):
    """Return raw pace zone distribution data for the athlete."""
    try:
        data: Dict[str, Any] = payload.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}")

    pace = data.get("computed_training_metrics", {}).get("pace_zone_distribution_percent", {}) or {}
    return {"pace_zone_distribution_percent": pace}


@router.post("/pace-recommendations")
async def pace_recommendations(payload: AnalysisRequest):
    """Offer targeted pace distribution recommendations based on current data."""
    try:
        data: Dict[str, Any] = payload.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}")

    pace = data.get("computed_training_metrics", {}).get("pace_zone_distribution_percent", {}) or {}
    easy = float(pace.get("easy_recovery", 0))
    tempo = float(pace.get("tempo", 0))
    hard = float(pace.get("hard", 0))
    total = easy + tempo + hard
    if total > 0 and total != 100:
        easy_pct = round((easy / total) * 100)
        tempo_pct = round((tempo / total) * 100)
        hard_pct = round((hard / total) * 100)
    else:
        easy_pct = int(easy)
        tempo_pct = int(tempo)
        hard_pct = int(hard)

    recommendations = []
    if easy_pct < 60:
        recommendations.append("Increase easy running to support endurance and recovery.")
    else:
        recommendations.append("Keep your easy run volume high to maintain aerobic fitness.")

    if tempo_pct < 20:
        recommendations.append("Add a few tempo efforts to improve lactate threshold.")
    else:
        recommendations.append("Your tempo work looks well balanced for this phase.")

    if hard_pct < 7:
        recommendations.append("Include a short quality session to preserve top-end speed.")
    else:
        recommendations.append("Your hard sessions are providing enough stimulus for adaptation.")

    return {"recommendations": recommendations}


@router.post("/optimal-hr-distribution")
async def optimal_hr_distribution(payload: AnalysisRequest):
    """Analyze heart rate zone distribution and return an AI-style summary.

    Mirrors the 'Optimal Heart Rate Distribution' card: evaluates zones, computes
    proportion in low-effort zones and provides a concise narrative and distribution.
    """
    try:
        data: Dict[str, Any] = payload.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}")

    hr = data.get("computed_training_metrics", {}).get("heart_rate_zone_distribution_percent", {}) or {}
    z1 = float(hr.get("zone_1", 0))
    z2 = float(hr.get("zone_2", 0))
    z3 = float(hr.get("zone_3", 0))
    z4 = float(hr.get("zone_4", 0))
    z5 = float(hr.get("zone_5", 0))

    total = z1 + z2 + z3 + z4 + z5
    if total > 0 and total != 100:
        z1_pct = round((z1 / total) * 100)
        z2_pct = round((z2 / total) * 100)
        z3_pct = round((z3 / total) * 100)
        z4_pct = round((z4 / total) * 100)
        z5_pct = round((z5 / total) * 100)
    else:
        z1_pct = int(z1)
        z2_pct = int(z2)
        z3_pct = int(z3)
        z4_pct = int(z4)
        z5_pct = int(z5)

    low_effort = z1_pct + z2_pct
    narrative = (
        f"Your heart rate distribution aligns well with your pace zones, confirming proper effort management. "
        f"The consistent low heart rate work (Zones 1-2: {low_effort}% ) built a strong aerobic foundation while keeping stress manageable. "
        f"Maintain this balance to support long-term aerobic gains and reduce injury risk."
    )

    return {
        "title": "Optimal Heart Rate Distribution",
        "narrative": narrative,
        "distribution": {
            "zone_1": z1_pct,
            "zone_2": z2_pct,
            "zone_3": z3_pct,
            "zone_4": z4_pct,
            "zone_5": z5_pct,
        },
    }


@router.post("/optimal-power-distribution")
async def optimal_power_distribution(payload: AnalysisRequest):
    """Analyze power zone distribution and return an AI-style summary.

    Mirrors the 'Optimal Power Zone' card: evaluates power zones, computes
    proportion in lower-intensity zones and provides a concise narrative and distribution.
    """
    try:
        data: Dict[str, Any] = payload.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}")

    power = data.get("computed_training_metrics", {}).get("power_zone_distribution_percent", {}) or {}
    z1 = float(power.get("zone_1", 0))
    z2 = float(power.get("zone_2", 0))
    z3 = float(power.get("zone_3", 0))
    z4 = float(power.get("zone_4", 0))
    z5 = float(power.get("zone_5", 0))

    total = z1 + z2 + z3 + z4 + z5
    if total > 0 and total != 100:
        z1_pct = round((z1 / total) * 100)
        z2_pct = round((z2 / total) * 100)
        z3_pct = round((z3 / total) * 100)
        z4_pct = round((z4 / total) * 100)
        z5_pct = round((z5 / total) * 100)
    else:
        z1_pct = int(z1)
        z2_pct = int(z2)
        z3_pct = int(z3)
        z4_pct = int(z4)
        z5_pct = int(z5)

    low_intensity = z1_pct + z2_pct
    high_intensity = z4_pct + z5_pct
    narrative = (
        f"Your power zone distribution shows strong consistency with pace and heart rate metrics, confirming proper effort management. "
        f"The {low_intensity}% of training time in lower power zones (Zones 1-2) demonstrates excellent discipline in keeping easy runs easy. "
        f"Controlled high-intensity work in Zones 4-5 ({high_intensity}%) provides sufficient stimulus for performance gains while minimizing injury risk."
    )

    return {
        "title": "Optimal Power Zone",
        "narrative": narrative,
        "distribution": {
            "zone_1": z1_pct,
            "zone_2": z2_pct,
            "zone_3": z3_pct,
            "zone_4": z4_pct,
            "zone_5": z5_pct,
        },
    }
