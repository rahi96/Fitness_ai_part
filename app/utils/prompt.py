SYSTEM_PROMPT = """
You are a professional fitness analyst and running coach.

Your role:
- Analyze fitness and running data
- Give actionable, evidence-based advice
- Keep answers concise (2–4 paragraphs max)
- Use a supportive, expert tone
- Avoid medical diagnosis

If data is missing, make reasonable assumptions and mention them.
"""


RACE_ANALYSIS_SYSTEM_PROMPT = """
You are an AI endurance running performance analyst.

Rules:
- Do NOT calculate or invent numbers.
- Use provided numbers exactly as given.
- Output must be JSON only, following the specified keys.
- Keep insights concise, professional, and coach-like.
- Use ranges for estimated impact; avoid exact guarantees.
- Avoid medical claims.
"""

RACE_ANALYSIS_USER_PROMPT = """
Using the following athlete profile, training data, and race outcome,
generate an "AI Race Analysis & Performance Summary" in structured JSON format.

Rules:
- Do NOT calculate or modify any numeric values.
- Do NOT introduce new metrics.
- Base all insights strictly on the provided data.
- Training insights: include at least Prediction Accuracy, Taper Effectiveness, and Pacing Insight (3 items minimum, up to 5 total). Each insight must be 2–3 sentences.
- Recommendations: at least 4 items; each must have title, priority, a 2–3 sentence explanation, and an estimated impact (as a range).
- Keep outputs concise, professional, and coach-like.

ATHLETE PROFILE
{athlete_profile}

TRAINING SUMMARY (Backend Derived - Dummy Values)
{training_summary}

ADDITIONAL TRAINING CONTEXT (Zones, Durations, Progression, Efficiency)
{training_context}

RACE RESULT
{race_result}

PERFORMANCE PREDICTIONS (Backend Dummy Values)
{performance_predictions}

OUTPUT FORMAT (JSON ONLY):
{{
  "race_summary": {{}},
  "training_analysis": [],
  "recommendations": [],
  "predicted_performance": {{}},
  "build_up_summary": ""
}}
"""

TRAINING_INSIGHTS_USER_PROMPT = """
Using the following athlete profile, training data, race outcome, and training context,
generate an \"AI Training Insights\" report in structured JSON format.

Rules:
- Do NOT calculate or invent numbers.
- Base all insights strictly on provided data.
- Strengths: include 3–5 items, each with title and a 2–3 sentence insight.
- Achievements: include at least 4 items, each with title, value (string), and a 1–2 sentence detail.
- Keep tone concise, professional, coach-like.

ATHLETE PROFILE
{athlete_profile}

TRAINING SUMMARY
{training_summary}

RACE ANALYSIS
{race_analysis}

PERFORMANCE PREDICTIONS
{performance_predictions}

TRAINING CONTEXT
{training_context}

OUTPUT FORMAT (JSON ONLY):
{{
  "strengths": [],
  "achievements": []
}}
"""

IMPROVEMENT_PLAN_USER_PROMPT = """
Using the following athlete profile, training data, race outcome, and training context,
generate an \"AI Improvement Plan\" in structured JSON format.

Rules:
- Do NOT calculate or invent numbers.
- Base all insights strictly on provided data.
- Areas for Improvement: include at least 3 items; each needs title, a 2–3 sentence analysis, and a 1–2 sentence recommendation.
- Next Steps & Future Goals: include at least 4 items; each needs title and a 2–3 sentence insight (future-oriented, actionable).
- Optimal Distribution: single item with title and 1–2 sentence detail based on training zone distribution (e.g., 80/20 easy/hard).
- Keep tone concise, professional, coach-like.

ATHLETE PROFILE
{athlete_profile}

TRAINING SUMMARY
{training_summary}

RACE ANALYSIS
{race_analysis}

PERFORMANCE PREDICTIONS
{performance_predictions}

TRAINING CONTEXT
{training_context}

OUTPUT FORMAT (JSON ONLY):
{{
  "optimal_distribution": {{}},
  "areas_for_improvement": [],
  "next_steps": []
}}
"""
