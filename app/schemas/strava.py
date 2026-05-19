from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


# ==================== Dataset Models ====================

class HeartRateZoneDistribution(BaseModel):
    """Heart rate zone distribution percentages"""
    zone_1: int
    zone_2: int
    zone_3: int
    zone_4: int
    zone_5: int


class PowerZoneDistribution(BaseModel):
    """Power zone distribution percentages"""
    zone_1: int
    zone_2: int
    zone_3: int
    zone_4: int
    zone_5: int


class PaceZoneDistribution(BaseModel):
    """Pace zone distribution percentages"""
    easy_recovery: int
    tempo: int
    hard: int


class ComputedTrainingMetrics(BaseModel):
    """Computed training metrics"""
    heart_rate_zone_distribution_percent: HeartRateZoneDistribution
    power_zone_distribution_percent: PowerZoneDistribution
    pace_zone_distribution_percent: PaceZoneDistribution


class RunDurationTracking(BaseModel):
    """Run duration tracking"""
    less_than_30_min: int
    between_45_and_60_min: int
    between_60_and_90_min: int
    above_90_min: int


class WeeklyProgression(BaseModel):
    """Weekly progression metrics"""
    average_weekly_distance_km: float
    peak_weekly_distance_km: float
    max_weekly_increase_percent: float


class LongRunSummary(BaseModel):
    """Long run summary"""
    count: int
    max_duration_minutes: int


class EfficiencyIndicators(BaseModel):
    """Efficiency indicators"""
    pace_efficiency_change_percent: float
    heart_rate_drift: str


class AnalysisPeriod(BaseModel):
    """Analysis period"""
    weeks: int


class UserTrainingData(BaseModel):
    """Complete user training data from dataset"""
    user_id: int
    analysis_period: AnalysisPeriod
    computed_training_metrics: ComputedTrainingMetrics
    run_duration_tracking: RunDurationTracking
    weekly_progression: WeeklyProgression
    long_run_summary: LongRunSummary
    efficiency_indicators: EfficiencyIndicators


# ==================== Performance Analysis Models ====================
class VolumeMetrics(BaseModel):
    """Volume metrics for user"""
    description: str = Field(..., description="Detailed description of training volume")
    total_distance_km: float
    total_time_hours: float
    total_activities: int
    average_distance_per_activity: float


class FrequencyMetrics(BaseModel):
    """Frequency metrics for user"""
    description: str = Field(..., description="Detailed description of training frequency")
    average_runs_per_week: float
    consistency_score: str = Field(..., description="Consistency level")
    average_run_value: str = Field(..., description="Run balance assessment")


class IntensityMetrics(BaseModel):
    """Intensity metrics for user"""
    description: str = Field(..., description="Detailed description of training intensity")
    polarized_training: str = Field(..., description="Polarization quality")
    intensity_value: str = Field(..., description="Intensity distribution")


class RecoveryMetrics(BaseModel):
    """Recovery metrics for user"""
    description: str = Field(..., description="Detailed description of recovery status")
    rest_integration: str = Field(..., description="Recovery run percentage")
    recovery_quality: str = Field(..., description="Heart rate drift assessment")


class ProgressionMetrics(BaseModel):
    """Progression metrics for user"""
    description: str = Field(..., description="Detailed description of progression pattern")
    weekly_increase: str = Field(..., description="Weekly increase percentage")
    progression_pattern: str = Field(..., description="Progression sustainability")


class PerformanceGrade(BaseModel):
    """Performance grade for a single metric"""
    description: str


class PerformanceGrades(BaseModel):
    """All performance grades"""
    volume: PerformanceGrade
    frequency: PerformanceGrade
    intensity: PerformanceGrade
    recovery: PerformanceGrade
    progression: PerformanceGrade


class AnalysisResponse(BaseModel):
    """Response with performance analysis"""
    user_id: int
    ai_summary: str
    performance_grades: PerformanceGrades


class AnalysisRequest(BaseModel):
    """Request to analyze user data - accepts full training data"""
    user_id: int
    analysis_period: AnalysisPeriod
    computed_training_metrics: ComputedTrainingMetrics
    run_duration_tracking: RunDurationTracking
    weekly_progression: WeeklyProgression
    long_run_summary: LongRunSummary
    efficiency_indicators: EfficiencyIndicators


class BatchAnalysisRequest(BaseModel):
    """Request to analyze multiple users at once"""
    users: List[AnalysisRequest] = Field(..., description="List of user training data to analyze")


class BatchAnalysisResponse(BaseModel):
    """Response with analyses for multiple users"""
    total_users: int = Field(..., description="Total number of users analyzed")
    successful: int = Field(..., description="Number of successful analyses")
    failed: int = Field(..., description="Number of failed analyses")
    results: List[AnalysisResponse] = Field(..., description="Analysis results for each user")
    errors: Optional[Dict[int, str]] = Field(None, description="Errors by user_id if any failed")