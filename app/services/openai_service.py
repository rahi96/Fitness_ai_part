from pathlib import Path
from typing import Dict, List


PROMPT_PATH = Path(__file__).resolve().parents[1] / "utils" / "training_analysis.txt"


def render_analysis_text(
    plan_title: str,
    timeframe: str,
    narrative: str,
    metrics: Dict[str, float],
    achievements: List[Dict[str, str]],
) -> str:
    """Render a lightweight text summary using a template (no external API call)."""
    template = PROMPT_PATH.read_text(encoding="utf-8")
    achievements_bullets = "\n".join(
        [f"- {item['title']}: {item['detail']}" for item in achievements]
    )
    return template.format(
        plan_title=plan_title,
        timeframe=timeframe,
        narrative=narrative,
        easy_running_pct=metrics["easy_running"],
        weekly_growth_pct=metrics["weekly_growth"],
        training_performance_score=metrics["training_performance"],
        achievements_bullets=achievements_bullets,
    )
