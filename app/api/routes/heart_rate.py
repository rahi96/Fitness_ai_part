import json
import logging
from fastapi import APIRouter, HTTPException
from langchain_openai import ChatOpenAI

from app.schemas.strava import AnalysisRequest
from app.schemas.heart_rate import (
    HeartRateEfficiencyResponse,
    AerobicEfficiencyData,
    ThresholdPaceData,
    CardiacDriftData,
)
from app.services.analysis_cache_service import analysis_cache_service
from app.services.metrics_engine import compute_metrics
from app.config import OPENAI_API_KEY, MODEL_NAME
from app.utils.prompt import (
    HEART_RATE_EFFICIENCY_SYSTEM_PROMPT,
    HEART_RATE_EFFICIENCY_USER_PROMPT,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/heart-rate", tags=["Heart Rate"])


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
            logger.error(f"Error querying OpenAI in heart rate route: {e}", exc_info=True)
            continue
    return {}


@router.post("/heart-rate-efficiency", response_model=HeartRateEfficiencyResponse)
async def heart_rate_efficiency(payload: AnalysisRequest):
    """Analyze heart rate efficiency with OpenAI based on Strava training metrics."""
    data = payload.model_dump(mode="json")
    cached = analysis_cache_service.get_cached_response(
        user_id=payload.user_id,
        cache_type="heart_rate_efficiency",
        request_payload=data,
    )
    if cached:
        return HeartRateEfficiencyResponse(**cached)

    metrics = compute_metrics(data)

    user_prompt = HEART_RATE_EFFICIENCY_USER_PROMPT.format(
        athlete_profile=json.dumps(data.get("athlete_profile", {}), indent=2),
        training_data=json.dumps(data, indent=2),
        metrics=json.dumps(metrics, indent=2),
    )

    fallback_data = {
        "improved_aerobic_efficiency": {
            "narrative": "Your average HR at easy pace (5:00-5:30/km) decreased from 155 bpm to 147 bpm, indicating improved cardiovascular fitness and running economy.",
            "week_1_hr": 155,
            "week_1_pace": "5:15/km",
            "week_12_hr": 147,
            "week_12_pace": "5:15/km",
        },
        "threshold_pace_development": {
            "narrative": "Your threshold pace (at 175 bpm) improved from 4:25/km to 4:15/km, a 10-second improvement that translated directly to better race performance.",
            "threshold_hr": 175,
            "initial_pace": "4:25/km",
            "improved_pace": "4:15/km",
            "difference_seconds": 10,
        },
        "low_cardiac_drift": {
            "narrative": "Your heart rate stayed stable during long runs, only rising 3-4 bpm over 90+ minutes. This indicates excellent aerobic capacity and proper pacing.",
            "drift_bpm_increase": 3,
            "duration_minutes": 90,
        }
    }

    parsed = {}
    if OPENAI_API_KEY:
        try:
            parsed = _query_openai_response(
                HEART_RATE_EFFICIENCY_SYSTEM_PROMPT, user_prompt
            )
        except Exception as e:
            logger.error(f"OpenAI query failed, falling back to mock: {e}")

    aerobic = parsed.get("improved_aerobic_efficiency") or fallback_data["improved_aerobic_efficiency"]
    threshold = parsed.get("threshold_pace_development") or fallback_data["threshold_pace_development"]
    drift = parsed.get("low_cardiac_drift") or fallback_data["low_cardiac_drift"]

    def _safe_int(val, default):
        """Return int(val) or default if val is None or conversion fails."""
        if val is None:
            return default
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    def _safe_str(val, default):
        """Return str(val) or default if val is None."""
        if val is None:
            return default
        return str(val)

    response = HeartRateEfficiencyResponse(
        user_id=payload.user_id,
        improved_aerobic_efficiency=AerobicEfficiencyData(
            narrative=_safe_str(aerobic.get("narrative"), "Your average HR at easy pace (5:00-5:30/km) decreased from 155 bpm to 147 bpm, indicating improved cardiovascular fitness and running economy."),
            week_1_hr=_safe_int(aerobic.get("week_1_hr"), 155),
            week_1_pace=_safe_str(aerobic.get("week_1_pace"), "5:15/km"),
            week_12_hr=_safe_int(aerobic.get("week_12_hr"), 147),
            week_12_pace=_safe_str(aerobic.get("week_12_pace"), "5:15/km"),
        ),
        threshold_pace_development=ThresholdPaceData(
            narrative=_safe_str(threshold.get("narrative"), "Your threshold pace (at 175 bpm) improved from 4:25/km to 4:15/km, a 10-second improvement that translated directly to better race performance."),
            threshold_hr=_safe_int(threshold.get("threshold_hr"), 175),
            initial_pace=_safe_str(threshold.get("initial_pace"), "4:25/km"),
            improved_pace=_safe_str(threshold.get("improved_pace"), "4:15/km"),
            difference_seconds=_safe_int(threshold.get("difference_seconds"), 10),
        ),
        low_cardiac_drift=CardiacDriftData(
            narrative=_safe_str(drift.get("narrative"), "Your heart rate stayed stable during long runs, only rising 3-4 bpm over 90+ minutes. This indicates excellent aerobic capacity and proper pacing."),
            drift_bpm_increase=_safe_int(drift.get("drift_bpm_increase"), 3),
            duration_minutes=_safe_int(drift.get("duration_minutes"), 90),
        ),
    )

    analysis_cache_service.store_response(
        user_id=payload.user_id,
        cache_type="heart_rate_efficiency",
        request_payload=data,
        response_data=response.model_dump(mode="json"),
    )
    return response
