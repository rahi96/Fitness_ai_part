from datetime import date

import json
from fastapi import APIRouter, HTTPException
from langchain_openai import ChatOpenAI

from app.schemas.analysis_request import TrainingData
from app.schemas.analysis_response import (
    AnalysisAchievement,
    AnalysisMetric,
    TrainingAnalysisResponse,
    TrainingSummary,
)
from app.schemas.race_analysis import (
    RaceAnalysisResponse,
    RaceAnalysisRequest,
    RaceSummary,
    TrainingInsight,
    Recommendation,
)
from app.schemas.training_insights import (
    TrainingInsightsRequest,
    TrainingInsightsResponse,
    StrengthInsight,
    Achievement,
)
from app.schemas.improvement_plan import (
    ImprovementPlanRequest,
    ImprovementPlanResponse,
    ImprovementItem,
    GoalItem,
    OptimalDistribution,
)
from app.services.metrics_engine import compute_metrics, build_achievements
from app.services.analysis_cache_service import analysis_cache_service
from app.config import OPENAI_API_KEY, MODEL_NAME
from app.utils.prompt import (
    TRAINING_ANALYSIS_SYSTEM_PROMPT,
    TRAINING_ANALYSIS_USER_PROMPT,
    RACE_ANALYSIS_SYSTEM_PROMPT,
    RACE_ANALYSIS_USER_PROMPT,
    TRAINING_INSIGHTS_SYSTEM_PROMPT,
    TRAINING_INSIGHTS_USER_PROMPT,
    IMPROVEMENT_PLAN_SYSTEM_PROMPT,
    IMPROVEMENT_PLAN_USER_PROMPT,
)


router = APIRouter()


@router.post("/training/analysis", response_model=TrainingAnalysisResponse)
async def get_training_analysis(payload: TrainingData):
    data = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id,
        cache_type="training_analysis",
        request_payload=data,
    )
    if cached:
        return TrainingAnalysisResponse(**cached)

    metrics = compute_metrics(data)
    achievements_raw = build_achievements(data, metrics)

    plan_title = "Training Insights: Half Marathon Build-Up"
    timeframe = f"{data.get('analysis_period', {}).get('weeks', 12)}-week analysis leading to {date.today():%B %d, %Y}"

    user_prompt = TRAINING_ANALYSIS_USER_PROMPT.format(
        athlete_profile=json.dumps(data.get('athlete_profile', {}), indent=2),
        training_data=json.dumps(data, indent=2),
        metrics=json.dumps(metrics, indent=2),
        achievements=json.dumps(achievements_raw, indent=2),
        plan_title=plan_title,
        timeframe=timeframe,
    )

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set.")

    parsed = _query_openai_response(TRAINING_ANALYSIS_SYSTEM_PROMPT, user_prompt)
    if not parsed or not parsed.get('plan_title') or not parsed.get('timeframe') or not parsed.get('summary') or not parsed.get('achievements'):
        raise HTTPException(status_code=500, detail="OpenAI did not return valid training analysis output.")

    response = TrainingAnalysisResponse(**parsed)
    analysis_cache_service.store_response(
        user_id=payload.user_id,
        cache_type="training_analysis",
        request_payload=data,
        response_data=response.model_dump(mode="json"),
    )
    return response


def _find_prediction(predictions: list, distance: str, default_time: str) -> str:
    for item in predictions:
        if item.get("distance") == distance:
            return item.get("time", default_time)
    return default_time


def _parse_json_content(content: str) -> dict:
    """Handle common AI output patterns (e.g., fenced code blocks)."""
    if isinstance(content, dict):
        return content
    if isinstance(content, list):
        # If the model returns a list with a single dict, unwrap it.
        if len(content) == 1 and isinstance(content[0], dict):
            return content[0]
        try:
            return json.loads(json.dumps(content))
        except Exception:
            pass

    cleaned = str(content).strip()
    if cleaned.startswith("```"):
        # Strip code fences like ```json ... ```
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[len("json"):].strip()

    # Try direct JSON parsing first.
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Attempt to recover a JSON object or list from wrapped text.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if start != -1 and end != -1 and end > start:
            candidate = cleaned[start : end + 1]
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


def _query_openai_response(system_prompt: str, user_prompt: str) -> dict:
    """Call OpenAI and return parsed JSON output, or empty dict on failure."""
    if not OPENAI_API_KEY:
        return {}

    for model_kwargs in (
        {"response_format": {"type": "json_object"}},
        None,
    ):
        try:
            llm_args = {
                "api_key": OPENAI_API_KEY,
                "model": MODEL_NAME,
                "temperature": 0.1,
            }
            if model_kwargs is not None:
                llm_args["model_kwargs"] = model_kwargs
            llm = ChatOpenAI(**llm_args)
            ai_message = llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
            parsed = _parse_json_content(ai_message.content)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue
    return {}


@router.post("/ai/race-analysis", response_model=RaceAnalysisResponse)
async def ai_race_analysis(payload: RaceAnalysisRequest):
    request_payload = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id,
        cache_type="race_analysis",
        request_payload=request_payload,
    )
    if cached:
        return RaceAnalysisResponse(**cached)

    profile = payload.athlete_profile
    training_summary = payload.training_summary
    race_result = payload.race_analysis
    performance_predictions = payload.performance_predictions
    training_context = payload.training_context

    user_prompt = RACE_ANALYSIS_USER_PROMPT.format(
        athlete_profile=json.dumps(profile, indent=2),
        training_summary=json.dumps(training_summary, indent=2),
        training_context=json.dumps(training_context, indent=2),
        race_result=json.dumps(race_result, indent=2),
        performance_predictions=json.dumps(performance_predictions, indent=2),
    )

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set.")

    parsed = _query_openai_response(RACE_ANALYSIS_SYSTEM_PROMPT, user_prompt)
    if not parsed or not parsed.get("race_summary") or not parsed.get("training_analysis") or not parsed.get("recommendations"):
        raise HTTPException(status_code=500, detail="OpenAI did not return valid race analysis output.")

    response = _build_race_analysis_response(
        parsed=parsed,
        profile=profile,
        training_summary=training_summary,
        race_result=race_result,
        performance_predictions=performance_predictions,
    )
    analysis_cache_service.store_response(
        user_id=payload.user_id,
        cache_type="race_analysis",
        request_payload=request_payload,
        response_data=response.model_dump(mode="json"),
    )
    return response


@router.post("/ai/training-insights", response_model=TrainingInsightsResponse)
async def ai_training_insights(payload: TrainingInsightsRequest):
    request_payload = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id,
        cache_type="training_insights",
        request_payload=request_payload,
    )
    if cached:
        return TrainingInsightsResponse(**cached)

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set.")

    user_prompt = TRAINING_INSIGHTS_USER_PROMPT.format(
        athlete_profile=json.dumps(payload.athlete_profile, indent=2),
        training_summary=json.dumps(payload.training_summary, indent=2),
        race_analysis=json.dumps(payload.race_analysis, indent=2),
        performance_predictions=json.dumps(payload.performance_predictions, indent=2),
        training_context=json.dumps(payload.training_context, indent=2),
    )

    parsed = _query_openai_response(TRAINING_INSIGHTS_SYSTEM_PROMPT, user_prompt)
    if not parsed or not parsed.get("strengths") or not parsed.get("achievements"):
        raise HTTPException(status_code=500, detail="OpenAI did not return valid training insights output.")

    strengths = []
    for item in parsed.get("strengths", []):
        if isinstance(item, dict) and item.get("title") and item.get("insight"):
            strengths.append(StrengthInsight(title=str(item["title"]), insight=str(item["insight"])))
    achievements = []
    for item in parsed.get("achievements", []):
        if isinstance(item, dict) and item.get("title") and item.get("value"):
            achievements.append(
                Achievement(
                    title=str(item["title"]),
                    value=str(item["value"]),
                    detail=str(item.get("detail", "")),
                )
            )

    if not strengths or not achievements:
        raise HTTPException(status_code=500, detail="OpenAI returned incomplete training insights output.")

    response = TrainingInsightsResponse(
        strengths=strengths,
        achievements=achievements,
    )
    analysis_cache_service.store_response(
        user_id=payload.user_id,
        cache_type="training_insights",
        request_payload=request_payload,
        response_data=response.model_dump(mode="json"),
    )
    return response


@router.post("/ai/improvement-plan", response_model=ImprovementPlanResponse)
async def ai_improvement_plan(payload: ImprovementPlanRequest):
    request_payload = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id,
        cache_type="improvement_plan",
        request_payload=request_payload,
    )
    if cached:
        return ImprovementPlanResponse(**cached)

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set.")

    user_prompt = IMPROVEMENT_PLAN_USER_PROMPT.format(
        athlete_profile=json.dumps(payload.athlete_profile, indent=2),
        training_summary=json.dumps(payload.training_summary, indent=2),
        race_analysis=json.dumps(payload.race_analysis, indent=2),
        performance_predictions=json.dumps(payload.performance_predictions, indent=2),
        training_context=json.dumps(payload.training_context, indent=2),
    )

    parsed = _query_openai_response(IMPROVEMENT_PLAN_SYSTEM_PROMPT, user_prompt)
    if not parsed or not parsed.get("optimal_distribution") or not parsed.get("areas_for_improvement") or not parsed.get("next_steps"):
        raise HTTPException(status_code=500, detail="OpenAI did not return valid improvement plan output.")

    optimal_raw = parsed.get("optimal_distribution") or {}
    optimal_title = _normalize_optimal_title(str(optimal_raw.get("title") or ""))
    optimal_detail = str(optimal_raw.get("detail") or "")
    optimal = OptimalDistribution(
        title=optimal_title,
        detail=optimal_detail,
    )

    areas = []
    for item in parsed.get("areas_for_improvement", []):
        if isinstance(item, dict) and item.get("title") and item.get("analysis") and item.get("recommendation"):
            areas.append(
                ImprovementItem(
                    title=str(item["title"]),
                    analysis=str(item["analysis"]),
                    recommendation=str(item["recommendation"]),
                )
            )

    goals = []
    for item in parsed.get("next_steps", []):
        if isinstance(item, dict) and item.get("title") and item.get("insight"):
            goals.append(
                GoalItem(
                    title=str(item["title"]),
                    insight=str(item["insight"]),
                )
            )

    if not areas or not goals:
        raise HTTPException(status_code=500, detail="OpenAI returned incomplete improvement plan output.")
        goals.append(
            GoalItem(
                title="Maintain Your Fitness",
                insight="AI output missing; consider a short recovery block followed by a steady maintenance phase.",
            )
        )

    response = ImprovementPlanResponse(
        optimal_distribution=optimal,
        areas_for_improvement=areas,
        next_steps=goals,
    )
    analysis_cache_service.store_response(
        user_id=payload.user_id,
        cache_type="improvement_plan",
        request_payload=request_payload,
        response_data=response.model_dump(mode="json"),
    )
    return response


def _coerce_insight(item: dict) -> TrainingInsight | None:
    if not isinstance(item, dict):
        return None
    title = item.get("title") or item.get("aspect")
    insight = item.get("insight") or item.get("detail") or item.get("summary")
    if not (title and insight):
        return None
    try:
        return TrainingInsight(title=str(title), insight=str(insight))
    except Exception:
        return None


def _coerce_recommendation(item: dict) -> Recommendation | None:
    if not isinstance(item, dict):
        return None
    title = item.get("title") or item.get("aspect")
    priority = item.get("priority") or item.get("importance") or ""
    explanation = item.get("explanation") or item.get("detail") or item.get("insight") or ""
    estimated_impact = item.get("estimated_impact") or item.get("impact") or ""
    if not title:
        return None
    try:
        return Recommendation(
            title=str(title),
            priority=str(priority),
            explanation=str(explanation),
            estimated_impact=str(estimated_impact),
        )
    except Exception:
        return None


def _coerce_predicted_perf(raw: dict) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, str] = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            result[k] = v.get("time") or ""
        else:
            result[k] = str(v)
    return result


def _expand_insight(item: TrainingInsight) -> TrainingInsight:
    # If only one sentence, append a short supportive sentence.
    if item.insight.count(".") < 2:
        extra = " This pattern reinforces aerobic durability and should be maintained alongside targeted intensity."
        combined = item.insight.strip()
        if not combined.endswith("."):
            combined += "."
        combined += extra
        return TrainingInsight(title=item.title, insight=combined)
    return item


def _ensure_training_analysis(items: list[TrainingInsight]) -> list[TrainingInsight]:
    titles_needed = ["Prediction Accuracy", "Taper Effectiveness", "Pacing Insight"]
    existing_titles = {i.title for i in items}
    for t in titles_needed:
        if t not in existing_titles:
            items.append(
                TrainingInsight(
                    title=t,
                    insight=f"{t} is expected here. Please include this insight in 2–3 sentences based on the provided data."
                )
            )
    items = [_expand_insight(i) for i in items]
    # Cap at 5 items if model over-produces
    return items[:5]


def _normalize_optimal_title(title: str) -> str:
    # Normalize to single-word categories based on known patterns
    title_lower = title.lower()
    if any(word in title_lower for word in ["optimal", "best", "high"]):
        return "Optimal"
    if any(word in title_lower for word in ["average", "standard", "acceptable"]):
        return "Average"
    if any(word in title_lower for word in ["suboptimal", "poor", "low"]):
        return "Suboptimal"
    # Default to Optimal if unclear
    return "Optimal"


def _expand_summary(text: str) -> str:
    if not text:
        return (
            "Your build demonstrated consistent aerobic work, effective tapering, and solid pacing control. "
            "To progress, layer in race-pace and higher-intensity intervals while keeping easy volume steady."
        )
    if len(text) < 180:
        text = text.rstrip(".") + ". "
        text += (
            "Maintaining easy mileage while adding targeted intensity will strengthen efficiency and durability, "
            "supporting further performance gains."
        )
    return text


def _build_race_analysis_response(
    parsed: dict,
    profile: dict,
    training_summary: dict,
    race_result: dict,
    performance_predictions: dict,
) -> RaceAnalysisResponse:
    parsed_summary = parsed.get("race_summary") or {}
    race_summary = RaceSummary(
        actual_time=parsed_summary.get("actual_time", race_result.get("actual_time", "")),
        predicted_time=parsed_summary.get("predicted_time", race_result.get("predicted_time", "")),
        performance_delta=parsed_summary.get(
            "performance_delta",
            f"{race_result.get('performance_delta_seconds', '')} seconds",
        ),
        status=parsed_summary.get("status", race_result.get("goal_status", "")),
    )

    training_items: list[TrainingInsight] = []
    for item in parsed.get("training_analysis", []):
        coerced = _coerce_insight(item)
        if coerced:
            training_items.append(coerced)

    recommendations: list[Recommendation] = []
    for item in parsed.get("recommendations", []):
        coerced = _coerce_recommendation(item)
        if coerced:
            recommendations.append(coerced)

    predicted_perf_raw = parsed.get("predicted_performance") or performance_predictions
    predicted_perf = _coerce_predicted_perf(predicted_perf_raw)
    build_up_summary = parsed.get("build_up_summary") or ""

    # Minimal fallbacks for missing fields
    if not training_items:
        training_items.append(
            TrainingInsight(
                title="Training Summary",
                insight="AI output missing training analysis; please review training load and pacing trends.",
            )
        )

    # Ensure insight depth (2-3 sentences) and enforce required categories if missing
    training_items = _ensure_training_analysis(training_items)

    # Do not inject default recommendations; keep only model output (coerced)
    # Build-up summary: use model output as-is (no local expansion)

    return RaceAnalysisResponse(
        race_summary=race_summary,
        training_analysis=training_items,
        recommendations=recommendations,
        predicted_performance=predicted_perf,
        build_up_summary=build_up_summary,
    )
