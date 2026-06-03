from pydantic import BaseModel, Field

class AerobicEfficiencyData(BaseModel):
    """Aerobic efficiency data showing pace and heart rate comparison"""
    narrative: str = Field(..., description="Coaching analysis narrative for aerobic efficiency")
    week_1_hr: int = Field(..., description="Average HR in week 1")
    week_1_pace: str = Field(..., description="Average pace in week 1")
    week_12_hr: int = Field(..., description="Average HR in week 12")
    week_12_pace: str = Field(..., description="Average pace in week 12")

class ThresholdPaceData(BaseModel):
    """Threshold pace development metrics"""
    narrative: str = Field(..., description="Coaching analysis narrative for threshold pace")
    threshold_hr: int = Field(..., description="Heart rate at threshold")
    initial_pace: str = Field(..., description="Pace at threshold initially")
    improved_pace: str = Field(..., description="Pace at threshold after improvements")
    difference_seconds: int = Field(..., description="Improvement in seconds per km")

class CardiacDriftData(BaseModel):
    """Cardiac drift analysis for long runs"""
    narrative: str = Field(..., description="Coaching analysis narrative for cardiac drift")
    drift_bpm_increase: int = Field(..., description="Heart rate rise in bpm during long runs")
    duration_minutes: int = Field(..., description="Duration of long run in minutes")

class HeartRateEfficiencyResponse(BaseModel):
    """Complete heart rate efficiency analysis response"""
    user_id: str
    improved_aerobic_efficiency: AerobicEfficiencyData
    threshold_pace_development: ThresholdPaceData
    low_cardiac_drift: CardiacDriftData
