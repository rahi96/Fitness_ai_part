from typing import Any, Dict, List


def compute_metrics(data: Dict[str, Any]) -> Dict[str, float]:
    """Compute high-level metrics used in the summary card."""
    pace_dist = data.get("computed_training_metrics", {}).get(
        "pace_zone_distribution_percent", {}
    )
    easy_running = float(pace_dist.get("easy_recovery", 0))

    weekly_growth = float(
        data.get("weekly_progression", {}).get("max_weekly_increase_percent", 0)
    )

    efficiency_change = float(
        data.get("efficiency_indicators", {}).get("pace_efficiency_change_percent", 0)
    )
    long_run_count = float(data.get("long_run_summary", {}).get("count", 0))

    # Heuristic performance score capped at 100
    training_performance = (
        0.6 * easy_running
        + 3.0 * efficiency_change
        + (4.0 if weekly_growth <= 10 else -2.0)
        + 2.0 * long_run_count
    )
    training_performance = max(0.0, min(100.0, round(training_performance)))

    return {
        "easy_running": round(easy_running, 1),
        "weekly_growth": round(weekly_growth, 1),
        "training_performance": training_performance,
    }


def build_achievements(data: Dict[str, Any], metrics: Dict[str, float]) -> List[Dict[str, str]]:
    achievements: List[Dict[str, str]] = []

    achievements.append(
        {
            "title": "Consistent volume increase",
            "detail": f"Never exceeded {metrics['weekly_growth']}% weekly",
        }
    )

    efficiency_change = float(
        data.get("efficiency_indicators", {}).get("pace_efficiency_change_percent", 0)
    )
    achievements.append(
        {
            "title": "Improved efficiency",
            "detail": f"{efficiency_change}% better pace at same HR",
        }
    )

    pace_dist = data.get("computed_training_metrics", {}).get(
        "pace_zone_distribution_percent", {}
    )
    easy_pct = pace_dist.get("easy_recovery", 0)
    tempo_pct = pace_dist.get("tempo", 0)
    hard_pct = pace_dist.get("hard", 0)
    achievements.append(
        {
            "title": "Perfect polarization",
            "detail": f"{easy_pct}/{tempo_pct}/{hard_pct} easy/moderate/hard",
        }
    )

    achievements.append(
        {
            "title": "Strong taper execution",
            "detail": "Optimal recovery before race",
        }
    )

    return achievements
