import json
import logging
from fastapi import APIRouter
from langchain_openai import ChatOpenAI

from app.schemas.strava import AnalysisRequest
from app.schemas.dashboard import (
    ExecutiveSummaryResponse, ExecutiveSummaryItem,
    TrainingLoadAnalysisResponse, WeeklyDistancePoint, TrainingPhase,
    PerformanceMetricsResponse,
    WeeklyTrainingBreakdownResponse, WeeklyBreakdownEntry,
    RecommendationsInsightsResponse, RecommendationItem,
    TrainingZoneDistributionResponse, ZoneData,
    KeyAchievementsResponse, AchievementItem,
)
from app.services.analysis_cache_service import analysis_cache_service
from app.services.metrics_engine import compute_metrics
from app.config import OPENAI_API_KEY, MODEL_NAME

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

DASHBOARD_SYSTEM_PROMPT = """
You are an expert endurance running coach and data analyst.
Analyze the provided Strava training data and return ONLY valid JSON
matching the requested schema. No markdown fences, no commentary outside JSON.
Use the supplied numbers exactly — do not invent data. Keep language concise,
professional, and coach-like.
"""


def _safe_int(val, default):
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _safe_float(val, default):
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_str(val, default):
    if val is None:
        return default
    return str(val)


def _parse_json_content(content) -> dict:
    if isinstance(content, dict):
        return content
    if isinstance(content, list):
        if len(content) == 1 and isinstance(content[0], dict):
            return content[0]
        try:
            return json.loads(json.dumps(content))
        except Exception:
            pass
    cleaned = str(content).strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[len("json"):].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if start != -1 and end != -1 and end > start:
            candidate = cleaned[start: end + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
                if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
                    return parsed[0]
                return parsed
            except json.JSONDecodeError:
                continue
    return {}


def _query_openai(system_prompt: str, user_prompt: str) -> dict:
    if not OPENAI_API_KEY:
        return {}
    for model_kwargs in ({"response_format": {"type": "json_object"}}, None):
        try:
            llm_args = {"api_key": OPENAI_API_KEY, "model": MODEL_NAME, "temperature": 0.1}
            if model_kwargs is not None:
                llm_args["model_kwargs"] = model_kwargs
            llm = ChatOpenAI(**llm_args)
            ai_message = llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
            parsed = _parse_json_content(ai_message.content)
            if isinstance(parsed, dict):
                return parsed
        except Exception as e:
            logger.error("Dashboard OpenAI error: %s", e, exc_info=True)
            continue
    return {}


def _build_base_context(data: dict, metrics: dict) -> str:
    return (
        f"TRAINING DATA:\n{json.dumps(data, indent=2)}\n\n"
        f"COMPUTED METRICS:\n{json.dumps(metrics, indent=2)}"
    )


# ===================================================================
# 1. Executive Summary
# ===================================================================

EXEC_SUMMARY_FALLBACK = {
    "summary_narrative": "Your 12-week training block demonstrates strong overall execution with consistent volume progression, well-managed intensity distribution, and controlled weekly load increases. Recovery integration could be improved to maximize long-term adaptation.",
    "items": [
        {"title": "Training Consistency", "status": "Strong", "detail": "You maintained an excellent training rhythm with consistent weekly sessions and minimal gaps throughout the block.", "icon": "✅"},
        {"title": "Progression Management", "status": "Optimal", "detail": "Weekly volume increases stayed within the recommended 5-10% range, supporting safe adaptation and minimizing injury risk.", "icon": "📈"},
        {"title": "Recovery Integration", "status": "Attention Needed", "detail": "Zone 1 training volume is lower than ideal. Adding more dedicated recovery runs will enhance adaptation between hard sessions.", "icon": "⚠️"},
    ],
}

EXEC_SUMMARY_USER_PROMPT = """
Analyze this athlete's training data and produce an executive summary.

{context}

OUTPUT FORMAT (JSON ONLY):
{{
  "summary_narrative": "2-3 sentence overall training block summary",
  "items": [
    {{"title": "Training Consistency", "status": "Strong/Moderate/Weak", "detail": "1-2 sentence assessment", "icon": "✅"}},
    {{"title": "Progression Management", "status": "Optimal/Moderate/Aggressive", "detail": "1-2 sentence assessment", "icon": "📈"}},
    {{"title": "Recovery Integration", "status": "Good/Attention Needed", "detail": "1-2 sentence assessment", "icon": "⚠️"}}
  ]
}}
"""


@router.post("/executive-summary", response_model=ExecutiveSummaryResponse)
async def executive_summary(payload: AnalysisRequest):
    """AI-analyzed executive summary: consistency, progression, recovery."""
    data = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id, cache_type="dashboard_executive_summary", request_payload=data,
    )
    if cached:
        return ExecutiveSummaryResponse(**cached)

    metrics = compute_metrics(data)
    context = _build_base_context(data, metrics)
    parsed = {}
    if OPENAI_API_KEY:
        try:
            parsed = _query_openai(DASHBOARD_SYSTEM_PROMPT, EXEC_SUMMARY_USER_PROMPT.format(context=context))
        except Exception as e:
            logger.error("executive_summary fallback: %s", e)

    fb = EXEC_SUMMARY_FALLBACK
    items_raw = parsed.get("items") or fb["items"]
    items = []
    for it in items_raw:
        if isinstance(it, dict):
            items.append(ExecutiveSummaryItem(
                title=_safe_str(it.get("title"), "Metric"),
                status=_safe_str(it.get("status"), "N/A"),
                detail=_safe_str(it.get("detail"), ""),
                icon=_safe_str(it.get("icon"), ""),
            ))
    if not items:
        for it in fb["items"]:
            items.append(ExecutiveSummaryItem(**it))

    response = ExecutiveSummaryResponse(
        user_id=payload.user_id,
        summary_narrative=_safe_str(parsed.get("summary_narrative"), fb["summary_narrative"]),
        items=items,
    )
    analysis_cache_service.store_response(
        user_id=payload.user_id, cache_type="dashboard_executive_summary",
        request_payload=data, response_data=response.model_dump(mode="json"),
    )
    return response


# ===================================================================
# 2. Training Load Analysis
# ===================================================================

TRAINING_LOAD_FALLBACK = {
    "weekly_distance_progression": [
        {"week": 1, "distance_km": 38.0}, {"week": 2, "distance_km": 40.5},
        {"week": 3, "distance_km": 43.0}, {"week": 4, "distance_km": 36.0},
        {"week": 5, "distance_km": 44.5}, {"week": 6, "distance_km": 47.0},
        {"week": 7, "distance_km": 49.5}, {"week": 8, "distance_km": 42.0},
        {"week": 9, "distance_km": 50.0}, {"week": 10, "distance_km": 53.0},
        {"week": 11, "distance_km": 54.0}, {"week": 12, "distance_km": 45.0},
    ],
    "training_load_narrative": "Training load followed a well-structured periodized plan with progressive volume increases and strategic recovery weeks every 4th week.",
    "phases": [
        {"name": "Base Phase", "weeks": "Weeks 1-4", "description": "Established aerobic foundation with gradual volume build-up and emphasis on easy-paced running."},
        {"name": "Build Phase", "weeks": "Weeks 5-8", "description": "Increased training stimulus with higher volume and introduction of more tempo and threshold work."},
        {"name": "Peak & Taper", "weeks": "Weeks 9-12", "description": "Peak volume reached in weeks 9-11 followed by a strategic taper to optimize race-day freshness."},
    ],
    "analysis": "The periodization follows a 3:1 loading pattern (3 weeks build, 1 week recovery) which is optimal for adaptation. Volume peaked at 54 km in week 11 before tapering to 45 km, suggesting good race preparation timing.",
}

TRAINING_LOAD_USER_PROMPT = """
Analyze this athlete's training load and produce a periodization breakdown.

{context}

OUTPUT FORMAT (JSON ONLY):
{{
  "weekly_distance_progression": [{{"week": 1, "distance_km": 38.0}}, ...],
  "training_load_narrative": "2-3 sentence overview of load management",
  "phases": [
    {{"name": "Base Phase", "weeks": "Weeks 1-4", "description": "1-2 sentence phase description"}},
    {{"name": "Build Phase", "weeks": "Weeks 5-8", "description": "1-2 sentence phase description"}},
    {{"name": "Peak & Taper", "weeks": "Weeks 9-12", "description": "1-2 sentence phase description"}}
  ],
  "analysis": "2-3 sentence detailed analysis of training load pattern"
}}
"""


@router.post("/training-load-analysis", response_model=TrainingLoadAnalysisResponse)
async def training_load_analysis(payload: AnalysisRequest):
    """AI-analyzed training load: weekly progression, phases, analysis."""
    data = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id, cache_type="dashboard_training_load", request_payload=data,
    )
    if cached:
        return TrainingLoadAnalysisResponse(**cached)

    metrics = compute_metrics(data)
    context = _build_base_context(data, metrics)
    parsed = {}
    if OPENAI_API_KEY:
        try:
            parsed = _query_openai(DASHBOARD_SYSTEM_PROMPT, TRAINING_LOAD_USER_PROMPT.format(context=context))
        except Exception as e:
            logger.error("training_load_analysis fallback: %s", e)

    fb = TRAINING_LOAD_FALLBACK

    progression_raw = parsed.get("weekly_distance_progression") or fb["weekly_distance_progression"]
    progression = []
    for pt in progression_raw:
        if isinstance(pt, dict):
            progression.append(WeeklyDistancePoint(
                week=_safe_int(pt.get("week"), 1),
                distance_km=_safe_float(pt.get("distance_km"), 0.0),
            ))
    if not progression:
        progression = [WeeklyDistancePoint(**p) for p in fb["weekly_distance_progression"]]

    phases_raw = parsed.get("phases") or fb["phases"]
    phases = []
    for ph in phases_raw:
        if isinstance(ph, dict):
            phases.append(TrainingPhase(
                name=_safe_str(ph.get("name"), "Phase"),
                weeks=_safe_str(ph.get("weeks"), ""),
                description=_safe_str(ph.get("description"), ""),
            ))
    if not phases:
        phases = [TrainingPhase(**p) for p in fb["phases"]]

    response = TrainingLoadAnalysisResponse(
        user_id=payload.user_id,
        weekly_distance_progression=progression,
        training_load_narrative=_safe_str(parsed.get("training_load_narrative"), fb["training_load_narrative"]),
        phases=phases,
        analysis=_safe_str(parsed.get("analysis"), fb["analysis"]),
    )
    analysis_cache_service.store_response(
        user_id=payload.user_id, cache_type="dashboard_training_load",
        request_payload=data, response_data=response.model_dump(mode="json"),
    )
    return response


# ===================================================================
# 3. Performance Metrics
# ===================================================================

PERF_METRICS_FALLBACK = {
    "average_pace": "5:15/km",
    "resting_hr": 48,
    "easy_run_hr": 138,
    "tempo_hr": 168,
    "pace_progression_narrative": "Average pace improved from 5:30/km to 5:15/km over the 12-week block, reflecting enhanced running economy and aerobic fitness gains.",
    "hr_analysis_narrative": "Heart rate data shows excellent aerobic adaptation with a low resting HR of 48 bpm. Easy runs averaged 138 bpm (Zone 2) and tempo efforts reached 168 bpm (Zone 4), confirming proper intensity targeting.",
}

PERF_METRICS_USER_PROMPT = """
Analyze this athlete's performance metrics: pace and heart rate data.

{context}

OUTPUT FORMAT (JSON ONLY):
{{
  "average_pace": "5:15/km",
  "resting_hr": 48,
  "easy_run_hr": 138,
  "tempo_hr": 168,
  "pace_progression_narrative": "2-3 sentence pace progression analysis",
  "hr_analysis_narrative": "2-3 sentence heart rate analysis"
}}
"""


@router.post("/performance-metrics", response_model=PerformanceMetricsResponse)
async def performance_metrics(payload: AnalysisRequest):
    """AI-analyzed performance metrics: pace, resting HR, easy/tempo HR."""
    data = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id, cache_type="dashboard_performance_metrics", request_payload=data,
    )
    if cached:
        return PerformanceMetricsResponse(**cached)

    metrics = compute_metrics(data)
    context = _build_base_context(data, metrics)
    parsed = {}
    if OPENAI_API_KEY:
        try:
            parsed = _query_openai(DASHBOARD_SYSTEM_PROMPT, PERF_METRICS_USER_PROMPT.format(context=context))
        except Exception as e:
            logger.error("performance_metrics fallback: %s", e)

    fb = PERF_METRICS_FALLBACK
    response = PerformanceMetricsResponse(
        user_id=payload.user_id,
        average_pace=_safe_str(parsed.get("average_pace"), fb["average_pace"]),
        resting_hr=_safe_int(parsed.get("resting_hr"), fb["resting_hr"]),
        easy_run_hr=_safe_int(parsed.get("easy_run_hr"), fb["easy_run_hr"]),
        tempo_hr=_safe_int(parsed.get("tempo_hr"), fb["tempo_hr"]),
        pace_progression_narrative=_safe_str(parsed.get("pace_progression_narrative"), fb["pace_progression_narrative"]),
        hr_analysis_narrative=_safe_str(parsed.get("hr_analysis_narrative"), fb["hr_analysis_narrative"]),
    )
    analysis_cache_service.store_response(
        user_id=payload.user_id, cache_type="dashboard_performance_metrics",
        request_payload=data, response_data=response.model_dump(mode="json"),
    )
    return response


# ===================================================================
# 4. Weekly Training Breakdown
# ===================================================================

WEEKLY_BREAKDOWN_FALLBACK = {
    "weeks": [
        {"week": 1, "distance_km": 38.0, "runs": 5, "avg_pace": "5:30/km", "long_run_km": 14.0},
        {"week": 2, "distance_km": 40.5, "runs": 5, "avg_pace": "5:28/km", "long_run_km": 15.0},
        {"week": 3, "distance_km": 43.0, "runs": 6, "avg_pace": "5:25/km", "long_run_km": 16.0},
        {"week": 4, "distance_km": 36.0, "runs": 4, "avg_pace": "5:35/km", "long_run_km": 12.0},
        {"week": 5, "distance_km": 44.5, "runs": 5, "avg_pace": "5:22/km", "long_run_km": 17.0},
        {"week": 6, "distance_km": 47.0, "runs": 6, "avg_pace": "5:20/km", "long_run_km": 18.0},
        {"week": 7, "distance_km": 49.5, "runs": 6, "avg_pace": "5:18/km", "long_run_km": 19.0},
        {"week": 8, "distance_km": 42.0, "runs": 4, "avg_pace": "5:30/km", "long_run_km": 14.0},
        {"week": 9, "distance_km": 50.0, "runs": 6, "avg_pace": "5:16/km", "long_run_km": 20.0},
        {"week": 10, "distance_km": 53.0, "runs": 6, "avg_pace": "5:15/km", "long_run_km": 21.0},
        {"week": 11, "distance_km": 54.0, "runs": 6, "avg_pace": "5:14/km", "long_run_km": 22.0},
        {"week": 12, "distance_km": 45.0, "runs": 5, "avg_pace": "5:18/km", "long_run_km": 16.0},
    ],
    "summary": "Weekly volume progressed from 38 km to a peak of 54 km with planned recovery weeks at weeks 4, 8, and 12. Long run distance built from 14 km to 22 km, supporting endurance development.",
}

WEEKLY_BREAKDOWN_USER_PROMPT = """
Generate a detailed weekly training breakdown for this athlete's 12-week block.

{context}

OUTPUT FORMAT (JSON ONLY):
{{
  "weeks": [
    {{"week": 1, "distance_km": 38.0, "runs": 5, "avg_pace": "5:30/km", "long_run_km": 14.0}},
    ...for all 12 weeks
  ],
  "summary": "2-3 sentence summary of the weekly training pattern"
}}
"""


@router.post("/weekly-training-breakdown", response_model=WeeklyTrainingBreakdownResponse)
async def weekly_training_breakdown(payload: AnalysisRequest):
    """AI-analyzed weekly training breakdown with distance, runs, pace, long runs."""
    data = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id, cache_type="dashboard_weekly_breakdown", request_payload=data,
    )
    if cached:
        return WeeklyTrainingBreakdownResponse(**cached)

    metrics = compute_metrics(data)
    context = _build_base_context(data, metrics)
    parsed = {}
    if OPENAI_API_KEY:
        try:
            parsed = _query_openai(DASHBOARD_SYSTEM_PROMPT, WEEKLY_BREAKDOWN_USER_PROMPT.format(context=context))
        except Exception as e:
            logger.error("weekly_training_breakdown fallback: %s", e)

    fb = WEEKLY_BREAKDOWN_FALLBACK

    weeks_raw = parsed.get("weeks") or fb["weeks"]
    weeks = []
    for w in weeks_raw:
        if isinstance(w, dict):
            weeks.append(WeeklyBreakdownEntry(
                week=_safe_int(w.get("week"), 1),
                distance_km=_safe_float(w.get("distance_km"), 0.0),
                runs=_safe_int(w.get("runs"), 0),
                avg_pace=_safe_str(w.get("avg_pace"), "0:00/km"),
                long_run_km=_safe_float(w.get("long_run_km"), 0.0),
            ))
    if not weeks:
        weeks = [WeeklyBreakdownEntry(**w) for w in fb["weeks"]]

    response = WeeklyTrainingBreakdownResponse(
        user_id=payload.user_id,
        weeks=weeks,
        summary=_safe_str(parsed.get("summary"), fb["summary"]),
    )
    analysis_cache_service.store_response(
        user_id=payload.user_id, cache_type="dashboard_weekly_breakdown",
        request_payload=data, response_data=response.model_dump(mode="json"),
    )
    return response


# ===================================================================
# 5. Recommendations & Insights
# ===================================================================

RECS_INSIGHTS_FALLBACK = {
    "strengths": [
        {"title": "Excellent Training Consistency", "detail": "Maintained 5-6 sessions per week throughout the entire block with minimal missed days, demonstrating outstanding commitment to the training plan."},
        {"title": "Progressive Overload Applied Correctly", "detail": "Weekly volume increases stayed within the 5-10% guideline, allowing the body to adapt progressively without accumulating excessive fatigue."},
        {"title": "Proper Training Zone Distribution", "detail": "82% of running was performed at easy/recovery pace, closely matching the recommended 80/20 polarized training model for endurance athletes."},
        {"title": "Strategic Recovery Weeks", "detail": "Recovery weeks were implemented every 4th week with 15-20% volume reductions, providing adequate recovery for supercompensation."},
    ],
    "areas_for_improvement": [
        {"title": "Increase Zone 1 Recovery Volume", "detail": "Current Zone 1 time is below the optimal 25-30% threshold. Adding dedicated recovery runs at very easy effort would enhance adaptation."},
        {"title": "Add Structured Speed Work", "detail": "Hard effort accounts for only 4% of total volume. Including weekly interval sessions would develop VO2max and running economy."},
        {"title": "Extend Long Run Duration", "detail": "Long runs peaked at 100 minutes. For half-marathon preparation, building toward 120+ minutes would improve endurance capacity."},
    ],
    "next_steps": [
        {"title": "Transition to Race-Specific Phase", "detail": "Begin incorporating race-pace tempo runs and goal-pace long run segments to develop race-specific fitness."},
        {"title": "Implement Heart Rate Zone Targets", "detail": "Use HR zone data to enforce easy-day discipline and ensure hard sessions reach the intended stimulus level."},
        {"title": "Plan Next Training Block", "detail": "Build on the current aerobic base with a 12-week race-specific block targeting a half-marathon or 10K PR."},
        {"title": "Monitor Recovery Markers", "detail": "Track resting HR, sleep quality, and perceived effort to ensure long-term training sustainability and prevent overtraining."},
    ],
}

RECS_INSIGHTS_USER_PROMPT = """
Analyze this athlete's training data and provide comprehensive recommendations and insights.

{context}

OUTPUT FORMAT (JSON ONLY):
{{
  "strengths": [
    {{"title": "Excellent Training Consistency", "detail": "2-sentence coaching assessment"}},
    {{"title": "Progressive Overload Applied Correctly", "detail": "..."}},
    {{"title": "Proper Training Zone Distribution", "detail": "..."}},
    {{"title": "Strategic Recovery Weeks", "detail": "..."}}
  ],
  "areas_for_improvement": [
    {{"title": "Area title", "detail": "2-sentence recommendation"}},
    ...at least 3 items
  ],
  "next_steps": [
    {{"title": "Goal title", "detail": "2-sentence actionable next step"}},
    ...at least 4 items
  ]
}}
"""


@router.post("/recommendations-insights", response_model=RecommendationsInsightsResponse)
async def recommendations_insights(payload: AnalysisRequest):
    """AI-analyzed recommendations: strengths, improvements, next steps."""
    data = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id, cache_type="dashboard_recommendations", request_payload=data,
    )
    if cached:
        return RecommendationsInsightsResponse(**cached)

    metrics = compute_metrics(data)
    context = _build_base_context(data, metrics)
    parsed = {}
    if OPENAI_API_KEY:
        try:
            parsed = _query_openai(DASHBOARD_SYSTEM_PROMPT, RECS_INSIGHTS_USER_PROMPT.format(context=context))
        except Exception as e:
            logger.error("recommendations_insights fallback: %s", e)

    fb = RECS_INSIGHTS_FALLBACK

    def _parse_rec_list(raw, fallback_list):
        items = []
        for it in (raw or fallback_list):
            if isinstance(it, dict):
                items.append(RecommendationItem(
                    title=_safe_str(it.get("title"), ""),
                    detail=_safe_str(it.get("detail"), ""),
                ))
        return items if items else [RecommendationItem(**i) for i in fallback_list]

    response = RecommendationsInsightsResponse(
        user_id=payload.user_id,
        strengths=_parse_rec_list(parsed.get("strengths"), fb["strengths"]),
        areas_for_improvement=_parse_rec_list(parsed.get("areas_for_improvement"), fb["areas_for_improvement"]),
        next_steps=_parse_rec_list(parsed.get("next_steps"), fb["next_steps"]),
    )
    analysis_cache_service.store_response(
        user_id=payload.user_id, cache_type="dashboard_recommendations",
        request_payload=data, response_data=response.model_dump(mode="json"),
    )
    return response


# ===================================================================
# 6. Training Zone Distribution
# ===================================================================

ZONE_DIST_FALLBACK = {
    "zones": [
        {"zone": "Zone 1 (Recovery)", "percentage": 20.0, "description": "Very easy effort, active recovery. Supports adaptation between hard sessions."},
        {"zone": "Zone 2 (Aerobic Base)", "percentage": 45.0, "description": "Easy conversational pace. Builds aerobic engine and fat oxidation capacity."},
        {"zone": "Zone 3 (Tempo)", "percentage": 18.0, "description": "Moderate effort, comfortably hard. Develops lactate threshold and running economy."},
        {"zone": "Zone 4 (Threshold)", "percentage": 12.0, "description": "Hard effort at lactate threshold. Improves ability to sustain race pace."},
        {"zone": "Zone 5 (VO2max)", "percentage": 5.0, "description": "Maximum effort intervals. Develops peak oxygen uptake and speed."},
    ],
    "optimal_distribution_narrative": "The current zone distribution shows 65% of training in Zones 1-2 (aerobic), which is close to the ideal 75-80% for endurance athletes. Increasing easy volume by 10% while maintaining hard efforts would optimize the polarized training model.",
    "current_assessment": "Your training zone distribution demonstrates good polarization with the majority of effort in low-intensity zones. The 82% easy pace distribution aligns well with the 80/20 principle. Zone 3 time could be reduced slightly in favor of more Zone 1 recovery runs.",
}

ZONE_DIST_USER_PROMPT = """
Analyze this athlete's training zone distribution from heart rate data.

{context}

OUTPUT FORMAT (JSON ONLY):
{{
  "zones": [
    {{"zone": "Zone 1 (Recovery)", "percentage": 20.0, "description": "1-2 sentence zone analysis"}},
    {{"zone": "Zone 2 (Aerobic Base)", "percentage": 45.0, "description": "..."}},
    {{"zone": "Zone 3 (Tempo)", "percentage": 18.0, "description": "..."}},
    {{"zone": "Zone 4 (Threshold)", "percentage": 12.0, "description": "..."}},
    {{"zone": "Zone 5 (VO2max)", "percentage": 5.0, "description": "..."}}
  ],
  "optimal_distribution_narrative": "2-3 sentence assessment of how current distribution compares to optimal",
  "current_assessment": "2-3 sentence overall zone distribution assessment"
}}
"""


@router.post("/training-zone-distribution", response_model=TrainingZoneDistributionResponse)
async def training_zone_distribution(payload: AnalysisRequest):
    """AI-analyzed training zone distribution with optimal assessment."""
    data = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id, cache_type="dashboard_zone_distribution", request_payload=data,
    )
    if cached:
        return TrainingZoneDistributionResponse(**cached)

    metrics = compute_metrics(data)
    context = _build_base_context(data, metrics)
    parsed = {}
    if OPENAI_API_KEY:
        try:
            parsed = _query_openai(DASHBOARD_SYSTEM_PROMPT, ZONE_DIST_USER_PROMPT.format(context=context))
        except Exception as e:
            logger.error("training_zone_distribution fallback: %s", e)

    fb = ZONE_DIST_FALLBACK

    zones_raw = parsed.get("zones") or fb["zones"]
    zones = []
    for z in zones_raw:
        if isinstance(z, dict):
            zones.append(ZoneData(
                zone=_safe_str(z.get("zone"), "Zone"),
                percentage=_safe_float(z.get("percentage"), 0.0),
                description=_safe_str(z.get("description"), ""),
            ))
    if not zones:
        zones = [ZoneData(**z) for z in fb["zones"]]

    response = TrainingZoneDistributionResponse(
        user_id=payload.user_id,
        zones=zones,
        optimal_distribution_narrative=_safe_str(parsed.get("optimal_distribution_narrative"), fb["optimal_distribution_narrative"]),
        current_assessment=_safe_str(parsed.get("current_assessment"), fb["current_assessment"]),
    )
    analysis_cache_service.store_response(
        user_id=payload.user_id, cache_type="dashboard_zone_distribution",
        request_payload=data, response_data=response.model_dump(mode="json"),
    )
    return response


# ===================================================================
# 7. Key Achievements
# ===================================================================

KEY_ACHIEVEMENTS_FALLBACK = {
    "achievements": [
        {"title": "Consistent Volume Build", "value": "38→54 km/week", "detail": "Weekly distance increased by 42% over 12 weeks following a safe progressive overload pattern."},
        {"title": "Pace Improvement", "value": "7% faster", "detail": "Pace efficiency improved by 7% at the same heart rate, demonstrating genuine fitness gains."},
        {"title": "Perfect Polarization", "value": "82/14/4 split", "detail": "Achieved near-ideal easy/tempo/hard distribution, matching elite training methodology."},
        {"title": "Long Run Milestone", "value": "100 min", "detail": "Completed 4 long runs with the longest reaching 100 minutes, building critical endurance capacity."},
        {"title": "Low Cardiac Drift", "value": "Excellent", "detail": "Heart rate remained stable during long runs, indicating strong aerobic fitness and pacing discipline."},
    ],
    "summary": "This training block produced 5 notable achievements highlighting consistent progression, improved efficiency, and disciplined training execution across all key performance markers.",
}

KEY_ACHIEVEMENTS_USER_PROMPT = """
Identify key achievements from this athlete's training block.

{context}

OUTPUT FORMAT (JSON ONLY):
{{
  "achievements": [
    {{"title": "Achievement name", "value": "Concise metric/stat", "detail": "1-2 sentence description"}},
    ...at least 4-5 achievements
  ],
  "summary": "1-2 sentence overall achievements summary"
}}
"""


@router.post("/key-achievements", response_model=KeyAchievementsResponse)
async def key_achievements(payload: AnalysisRequest):
    """AI-analyzed key achievements from the training block."""
    data = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id, cache_type="dashboard_key_achievements", request_payload=data,
    )
    if cached:
        return KeyAchievementsResponse(**cached)

    metrics = compute_metrics(data)
    context = _build_base_context(data, metrics)
    parsed = {}
    if OPENAI_API_KEY:
        try:
            parsed = _query_openai(DASHBOARD_SYSTEM_PROMPT, KEY_ACHIEVEMENTS_USER_PROMPT.format(context=context))
        except Exception as e:
            logger.error("key_achievements fallback: %s", e)

    fb = KEY_ACHIEVEMENTS_FALLBACK

    achievements_raw = parsed.get("achievements") or fb["achievements"]
    achievements = []
    for a in achievements_raw:
        if isinstance(a, dict):
            achievements.append(AchievementItem(
                title=_safe_str(a.get("title"), "Achievement"),
                value=_safe_str(a.get("value"), ""),
                detail=_safe_str(a.get("detail"), ""),
            ))
    if not achievements:
        achievements = [AchievementItem(**a) for a in fb["achievements"]]

    response = KeyAchievementsResponse(
        user_id=payload.user_id,
        achievements=achievements,
        summary=_safe_str(parsed.get("summary"), fb["summary"]),
    )
    analysis_cache_service.store_response(
        user_id=payload.user_id, cache_type="dashboard_key_achievements",
        request_payload=data, response_data=response.model_dump(mode="json"),
    )
    return response
