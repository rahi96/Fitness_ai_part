import logging
from datetime import datetime
from app.schemas.strava import (
    UserTrainingData, VolumeMetrics, FrequencyMetrics, 
    IntensityMetrics, RecoveryMetrics, ProgressionMetrics
)

logger = logging.getLogger(__name__)


class AnalysisGenerator:
    """Generate performance analysis based on actual training data"""
    
    def generate_volume_metrics(self, user_data: UserTrainingData) -> VolumeMetrics:
        """Generate volume metrics from user training data"""
        run_tracking = user_data.run_duration_tracking
        weekly_prog = user_data.weekly_progression
        analysis_weeks = user_data.analysis_period.weeks
        
        # Calculate total activities
        total_activities = (
            run_tracking.less_than_30_min +
            run_tracking.between_45_and_60_min +
            run_tracking.between_60_and_90_min +
            run_tracking.above_90_min
        )
        
        # Estimate total distance (rough calculation from weekly average)
        total_distance_km = weekly_prog.average_weekly_distance_km * analysis_weeks
        avg_distance_per_activity = total_distance_km / total_activities if total_activities > 0 else 0
        
        # Estimate total time (assuming avg 10 km/h pace)
        total_time_hours = total_distance_km / 10
        
        description = (
            f"Over a {analysis_weeks}-week analysis period, the athlete has accumulated {total_distance_km:.1f} kilometers "
            f"across {total_activities} training sessions, averaging {avg_distance_per_activity:.1f} km per session. "
            f"The peak weekly distance reached {weekly_prog.peak_weekly_distance_km} km, demonstrating sustainable volume management. "
            f"With {total_time_hours:.1f} hours of total training time, this reflects a serious commitment to endurance development "
            f"with well-distributed weekly loads. The session diversity (short, medium, and long runs) indicates a structured approach "
            f"to building aerobic base and work capacity."
        )
        
        return VolumeMetrics(
            description=description,
            total_distance_km=round(total_distance_km, 1),
            total_time_hours=round(total_time_hours, 1),
            total_activities=total_activities,
            average_distance_per_activity=round(avg_distance_per_activity, 1)
        )
    
    def generate_frequency_metrics(self, user_data: UserTrainingData) -> FrequencyMetrics:
        """Generate frequency metrics from user training data"""
        run_tracking = user_data.run_duration_tracking
        analysis_weeks = user_data.analysis_period.weeks
        
        total_runs = (
            run_tracking.less_than_30_min +
            run_tracking.between_45_and_60_min +
            run_tracking.between_60_and_90_min +
            run_tracking.above_90_min
        )
        
        avg_runs_per_week = total_runs / analysis_weeks if analysis_weeks > 0 else 0
        
        # Determine consistency score based on runs per week
        if avg_runs_per_week >= 4:
            consistency_score = "Excellent consistency - Elite level training frequency"
        elif avg_runs_per_week >= 3.5:
            consistency_score = "Very good consistency - Strong training discipline"
        elif avg_runs_per_week >= 3:
            consistency_score = "Good consistency - Consistent training schedule"
        elif avg_runs_per_week >= 2:
            consistency_score = "Moderate consistency - Regular training pattern"
        else:
            consistency_score = "Basic consistency - Developing training habit"
        
        # Assess run balance
        short_pct = (run_tracking.less_than_30_min / total_runs * 100) if total_runs > 0 else 0
        long_pct = (run_tracking.above_90_min / total_runs * 100) if total_runs > 0 else 0
        
        if long_pct >= 15 and short_pct >= 20:
            run_value = "Excellently balanced - Mix of quality and volume work"
        elif long_pct >= 10:
            run_value = "Well-balanced - Good mix of session types"
        else:
            run_value = "Needs variety - Consider incorporating long runs"
        
        description = (
            f"The training frequency of {avg_runs_per_week:.1f} sessions per week demonstrates strong training discipline. "
            f"Session distribution shows {run_tracking.less_than_30_min} short runs ({short_pct:.0f}%), "
            f"{run_tracking.between_45_and_60_min} medium runs, {run_tracking.between_60_and_90_min} long runs, "
            f"and {run_tracking.above_90_min} extended sessions ({long_pct:.0f}%). {run_value} for optimal fitness development. "
            f"The consistency reflects a dedicated athlete with excellent training compliance and strategic periodization."
        )
        
        return FrequencyMetrics(
            description=description,
            average_runs_per_week=round(avg_runs_per_week, 1),
            consistency_score=consistency_score,
            average_run_value=run_value
        )
    
    def generate_intensity_metrics(self, user_data: UserTrainingData) -> IntensityMetrics:
        """Generate intensity metrics from user training data"""
        hr_zones = user_data.computed_training_metrics.heart_rate_zone_distribution_percent
        pace_zones = user_data.computed_training_metrics.pace_zone_distribution_percent
        
        # Calculate polarized training score (zone 2 + zone 5)
        polarized_score = hr_zones.zone_1 + hr_zones.zone_2 + hr_zones.zone_5
        easy_recovery_pct = pace_zones.easy_recovery
        
        # Assess polarization
        if easy_recovery_pct >= 80:
            polarization_quality = "Excellent polarized - Near-perfect implementation"
        elif easy_recovery_pct >= 75:
            polarization_quality = "Very good polarized - Strong training structure"
        elif easy_recovery_pct >= 70:
            polarization_quality = "Good polarized - Solid intensity distribution"
        else:
            polarization_quality = "Moderate polarized - Consider more recovery running"
        
        intensity_distribution = f"{pace_zones.hard}% hard, {pace_zones.tempo}% tempo, {easy_recovery_pct}% easy"
        
        description = (
            f"Heart rate zone distribution reveals {hr_zones.zone_1}% in Zone 1 (recovery), {hr_zones.zone_2}% in Zone 2 (base), "
            f"{hr_zones.zone_3}% in Zone 3 (threshold), {hr_zones.zone_4}% in Zone 4 (VO2max), and {hr_zones.zone_5}% in Zone 5 (anaerobic). "
            f"Pace-based analysis shows {intensity_distribution}. "
            f"{polarization_quality} with clear separation between recovery and quality work. "
            f"This structure optimally stimulates aerobic adaptation while minimizing central nervous system fatigue and injury risk."
        )
        
        return IntensityMetrics(
            description=description,
            polarized_training=polarization_quality,
            intensity_value=intensity_distribution
        )
    
    def generate_recovery_metrics(self, user_data: UserTrainingData) -> RecoveryMetrics:
        """Generate recovery metrics from user training data"""
        efficiency = user_data.efficiency_indicators
        short_runs = user_data.run_duration_tracking.less_than_30_min
        total_runs = (
            user_data.run_duration_tracking.less_than_30_min +
            user_data.run_duration_tracking.between_45_and_60_min +
            user_data.run_duration_tracking.between_60_and_90_min +
            user_data.run_duration_tracking.above_90_min
        )
        
        short_run_pct = (short_runs / total_runs * 100) if total_runs > 0 else 0
        
        # Assess heart rate drift (fatigue indicator)
        if efficiency.heart_rate_drift == "low":
            drift_quality = "Excellent - Minimal fatigue accumulation"
        elif efficiency.heart_rate_drift == "moderate":
            drift_quality = "Good - Well-managed fatigue"
        else:
            drift_quality = "High - Monitor recovery closely"
        
        # Assess pace efficiency
        if efficiency.pace_efficiency_change_percent <= 5:
            pace_quality = "Excellent - Consistent performance"
        elif efficiency.pace_efficiency_change_percent <= 8:
            pace_quality = "Good - Stable efficiency gains"
        else:
            pace_quality = "Strong - Positive efficiency improvement"
        
        description = (
            f"Recovery analysis shows {short_run_pct:.0f}% short runs, indicating strong emphasis on recovery sessions. "
            f"Heart rate drift classification: {drift_quality}, reflecting {efficiency.heart_rate_drift} fatigue buildup. "
            f"Pace efficiency improved by {efficiency.pace_efficiency_change_percent}% ({pace_quality}). "
            f"This recovery strategy supports optimal physiological adaptation, reduces overtraining risk, and enables "
            f"consistent training execution week after week. The balance between intensity and recovery is sustainable and professional-grade."
        )
        
        return RecoveryMetrics(
            description=description,
            rest_integration=f"{short_run_pct:.0f}% recovery-focused runs",
            recovery_quality=drift_quality
        )
    
    def generate_progression_metrics(self, user_data: UserTrainingData) -> ProgressionMetrics:
        """Generate progression metrics from user training data"""
        weekly_prog = user_data.weekly_progression
        
        weekly_avg = weekly_prog.average_weekly_distance_km
        weekly_peak = weekly_prog.peak_weekly_distance_km
        max_increase = weekly_prog.max_weekly_increase_percent
        
        # Assess progression strategy
        if max_increase <= 8:
            progression_pattern = "Conservative and sustainable - Low injury risk"
        elif max_increase <= 10:
            progression_pattern = "Moderate and structured - Balanced approach"
        else:
            progression_pattern = "Aggressive progression - Monitor for overtraining"
        
        # Calculate hard week to average ratio
        hard_to_avg_ratio = (weekly_peak / weekly_avg) if weekly_avg > 0 else 1
        
        description = (
            f"Weekly progression analysis shows an average of {weekly_avg} km per week with peak weeks reaching {weekly_peak} km. "
            f"The maximum weekly increase of {max_increase}% exemplifies a {progression_pattern.lower()} philosophy. "
            f"Peak-to-average ratio of {hard_to_avg_ratio:.2f}x demonstrates appropriate periodization with strategically planned "
            f"harder weeks balanced by recovery microcycles. The progression pattern reflects mature training planning with "
            f"consideration for adaptation windows and fatigue management. This approach supports continuous improvement while "
            f"minimizing injury risk and promoting long-term athletic development."
        )
        
        return ProgressionMetrics(
            description=description,
            weekly_increase=f"{max_increase}% max weekly increase",
            progression_pattern=progression_pattern
        )
    
    def generate_summary(self, user_id, user_data: UserTrainingData, 
                        volume: VolumeMetrics, frequency: FrequencyMetrics,
                        intensity: IntensityMetrics, recovery: RecoveryMetrics,
                        progression: ProgressionMetrics) -> str:
        """Generate a formal performance summary"""
        
        analysis_weeks = user_data.analysis_period.weeks
        
        summary = (
            f"ATHLETIC PERFORMANCE ANALYSIS\n"
            f"{'='*55}\n"
            f"Athlete ID: {user_id} | Period: {analysis_weeks} weeks\n"
            f"Date: {datetime.now().strftime('%Y-%m-%d')}\n\n"
            
            f"PERFORMANCE OVERVIEW\n"
            f"{'-'*55}\n"
            f"Volume: {volume.total_distance_km} km across {volume.total_activities} sessions\n"
            f"Frequency: {frequency.average_runs_per_week} sessions/week | {frequency.consistency_score}\n"
            f"Intensity: {intensity.polarized_training}\n"
            f"Recovery: {recovery.recovery_quality}\n"
            f"Progression: {progression.progression_pattern}\n\n"
            
            f"ASSESSMENT\n"
            f"{'-'*55}\n"
            f"The training program demonstrates professional methodology with strategic periodization. "
            f"Metrics indicate sustainable performance development and effective training management. "
            f"Recommend: Continue current approach while maintaining consistency and recovery protocols."
        )
        
        return summary
