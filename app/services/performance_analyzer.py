import logging
from app.schemas.strava import UserTrainingData

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """Generate performance analysis based on exact rules"""
    
    def analyze_volume(self, user_data: UserTrainingData) -> str:
        """
        VOLUME RULES:
        - Stable or progressive → "Consistent weekly mileage"
        - Peak > average by ≤ 20% → "Well-managed peak volume"
        """
        avg = user_data.weekly_progression.average_weekly_distance_km
        peak = user_data.weekly_progression.peak_weekly_distance_km
        
        if peak <= 0 or avg <= 0:
            return "Insufficient data for volume analysis"
        
        peak_increase_pct = ((peak - avg) / avg) * 100
        
        if peak_increase_pct <= 20:
            return "Well-managed peak volume"
        else:
            return "Consistent weekly mileage"
    
    def analyze_frequency(self, user_data: UserTrainingData) -> str:
        """
        FREQUENCY RULES:
        ≥ 6 runs/week → "Strong consistency"
        5–6 runs/week → "Good consistency"
        < 5 runs/week → "Moderate consistency"
        Format: "Average X.X runs per week, [label]"
        """
        run_tracking = user_data.run_duration_tracking
        analysis_weeks = user_data.analysis_period.weeks
        
        total_runs = (
            run_tracking.less_than_30_min +
            run_tracking.between_45_and_60_min +
            run_tracking.between_60_and_90_min +
            run_tracking.above_90_min
        )
        
        avg_runs_per_week = total_runs / analysis_weeks if analysis_weeks > 0 else 0
        
        if avg_runs_per_week >= 6:
            label = "Strong consistency"
        elif avg_runs_per_week >= 5:
            label = "Good consistency"
        else:
            label = "Moderate consistency"
        
        return f"Average {avg_runs_per_week:.1f} runs per week, {label}"
    
    def analyze_intensity(self, user_data: UserTrainingData) -> str:
        """
        INTENSITY RULES:
        Easy ≥ 80% → "Highly aerobic"
        Easy 70–79% → "Well-balanced"
        Easy < 70% → "Intensity-heavy"
        Must include percentage of easy running
        """
        pace_zones = user_data.computed_training_metrics.pace_zone_distribution_percent
        easy_pct = pace_zones.easy_recovery
        
        if easy_pct >= 80:
            label = "Highly aerobic"
        elif easy_pct >= 70:
            label = "Well-balanced"
        else:
            label = "Intensity-heavy"
        
        return f"{easy_pct}% easy running - {label}"
    
    def analyze_recovery(self, user_data: UserTrainingData) -> str:
        """
        RECOVERY RULES:
        Low HR drift → "Excellent recovery"
        Moderate HR drift → "Generally good recovery"
        Use: heart_rate_drift, easy running %, long run count
        """
        efficiency = user_data.efficiency_indicators
        long_runs = user_data.long_run_summary.count
        
        hr_drift = efficiency.heart_rate_drift.lower()
        
        if hr_drift == "low":
            recovery_quality = "Excellent recovery"
        elif hr_drift == "moderate":
            recovery_quality = "Generally good recovery"
        else:
            recovery_quality = "Elevated recovery needs"
        
        return f"{recovery_quality} with {long_runs} long runs"
    
    def analyze_progression(self, user_data: UserTrainingData) -> str:
        """
        PROGRESSION RULES:
        ≤ 10% → "Safe"
        > 10% → "Aggressive"
        Format: "Safe X% weekly increase, well-structured"
        """
        max_increase = user_data.weekly_progression.max_weekly_increase_percent
        
        if max_increase <= 10:
            safety = "Safe"
        else:
            safety = "Aggressive"
        
        return f"{safety} {max_increase}% weekly increase, well-structured"
    
    def generate_ai_summary(self, user_data: UserTrainingData, 
                           volume: str, frequency: str, intensity: str,
                           recovery: str, progression: str) -> str:
        """
        AI SUMMARY RULES:
        - Length: 3–4 sentences
        - Tone: Professional, analytical, encouraging
        - Use only facts from input
        - Mention: training structure, intensity balance, recovery quality, progression safety
        - NO emojis, NO bullet points, NO numbers not in input
        """
        avg_weekly = user_data.weekly_progression.average_weekly_distance_km
        peak_weekly = user_data.weekly_progression.peak_weekly_distance_km
        easy_pct = user_data.computed_training_metrics.pace_zone_distribution_percent.easy_recovery
        
        summary = (
            f"Your training demonstrates a well-structured approach with {easy_pct}% of volume dedicated to aerobic development, "
            f"supporting sustainable fitness gains. Weekly mileage averages {avg_weekly} km with peak weeks reaching {peak_weekly} km, "
            f"indicating disciplined periodization and progression management. Recovery protocols are effectively integrated, "
            f"as evidenced by your heart rate drift patterns and consistent long run execution. This balanced methodology positions "
            f"your training for continued performance improvement while maintaining injury prevention standards."
        )
        
        return summary
    
    def analyze(self, user_data: UserTrainingData) -> dict:
        """Complete analysis following all rules"""
        
        volume = self.analyze_volume(user_data)
        frequency = self.analyze_frequency(user_data)
        intensity = self.analyze_intensity(user_data)
        recovery = self.analyze_recovery(user_data)
        progression = self.analyze_progression(user_data)
        
        ai_summary = self.generate_ai_summary(user_data, volume, frequency, intensity, recovery, progression)
        
        return {
            "user_id": user_data.user_id,
            "ai_summary": ai_summary,
            "performance_grades": {
                "volume": {"description": volume},
                "frequency": {"description": frequency},
                "intensity": {"description": intensity},
                "recovery": {"description": recovery},
                "progression": {"description": progression}
            }
        }
