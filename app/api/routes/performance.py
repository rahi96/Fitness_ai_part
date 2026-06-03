import json
import logging
from fastapi import APIRouter, HTTPException
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

from app.schemas.strava import (
    AnalysisRequest,
    ConsistentHRImprovementResponse,
    HRImprovementMetric,
    HRImprovementInsight,
)
from app.services.analysis_cache_service import analysis_cache_service
from app.services.metrics_engine import compute_metrics
from app.config import OPENAI_API_KEY, MODEL_NAME
from app.utils.prompt import (
    CONSISTENT_HR_IMPROVEMENT_SYSTEM_PROMPT,
    CONSISTENT_HR_IMPROVEMENT_USER_PROMPT,
)

router = APIRouter(prefix="/api/v1/performance", tags=["Performance"])


def _parse_json_content(content: str) -> dict:
    """Handle common AI output patterns (e.g., fenced code blocks)."""
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
        except Exception as e:
            logger.error(f"Error querying OpenAI in performance route: {e}", exc_info=True)
            continue
    return {}


@router.post("/consistent-hr-improvement", response_model=ConsistentHRImprovementResponse)
async def consistent_hr_improvement(payload: AnalysisRequest):
    """Analyze heart rate improvement consistency with OpenAI."""
    data = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id,
        cache_type="performance_consistent_hr_improvement",
        request_payload=data,
    )
    if cached:
        return ConsistentHRImprovementResponse(**cached)

    metrics = compute_metrics(data)
    heart_rate_zones = data.get("computed_training_metrics", {}).get(
        "heart_rate_zone_distribution_percent", {}
    ) or {}

    user_prompt = CONSISTENT_HR_IMPROVEMENT_USER_PROMPT.format(
        athlete_profile=json.dumps(data.get("athlete_profile", {}), indent=2),
        training_data=json.dumps(data, indent=2),
        heart_rate_zones=json.dumps(heart_rate_zones, indent=2),
        metrics=json.dumps(metrics, indent=2),
    )

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set.")

    parsed = _query_openai_response(
        CONSISTENT_HR_IMPROVEMENT_SYSTEM_PROMPT, user_prompt
    )
    if (
        not parsed
        or not parsed.get("improvement_summary")
        or parsed.get("hr_efficiency_score") is None
        or not parsed.get("improvement_metrics")
        or not parsed.get("key_insights")
    ):
        raise HTTPException(
            status_code=500,
            detail="OpenAI did not return valid heart rate improvement output.",
        )

    # Parse improvement metrics
    improvement_metrics = []
    for item in parsed.get("improvement_metrics", []):
        if isinstance(item, dict) and item.get("label"):
            improvement_metrics.append(
                HRImprovementMetric(
                    label=str(item.get("label", "")),
                    value=float(item.get("value", 0.0)),
                    unit=str(item.get("unit", "%")),
                )
            )

    # Parse key insights
    key_insights = []
    for item in parsed.get("key_insights", []):
        if isinstance(item, dict) and item.get("title") and item.get("detail"):
            key_insights.append(
                HRImprovementInsight(
                    title=str(item.get("title", "")),
                    detail=str(item.get("detail", "")),
                )
            )

    # Parse recommendations
    recommendations = []
    for rec in parsed.get("recommendations", []):
        if isinstance(rec, str):
            recommendations.append(rec)
        elif isinstance(rec, dict) and rec.get("text"):
            recommendations.append(str(rec.get("text", "")))

    # Validate minimum requirements
    if not improvement_metrics or not key_insights:
        raise HTTPException(
            status_code=500,
            detail="OpenAI returned incomplete heart rate improvement output.",
        )

    response = ConsistentHRImprovementResponse(
        user_id=payload.user_id,
        improvement_summary=str(parsed.get("improvement_summary", "")),
        hr_efficiency_score=float(parsed.get("hr_efficiency_score", 0.0)),
        baseline_hr_zones={
            k: int(v) for k, v in parsed.get("baseline_hr_zones", {}).items()
        },
        improvement_metrics=improvement_metrics,
        key_insights=key_insights,
        recommendations=recommendations,
    )

    analysis_cache_service.store_response(
        user_id=payload.user_id,
        cache_type="performance_consistent_hr_improvement",
        request_payload=data,
        response_data=response.model_dump(mode="json"),
    )
    return response
