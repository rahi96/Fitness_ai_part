from pydantic import BaseModel, Field
from typing import List, Dict, Optional


# ==================== 1. Executive Summary ====================

class ExecutiveSummaryItem(BaseModel):
    """Single executive summary card (e.g., Consistency, Progression, Recovery)."""
    title: str = Field(..., description="Card title, e.g. 'Training Consistency'")
    status: str = Field(..., description="Status label, e.g. 'Strong', 'Optimal', 'Attention Needed'")
    detail: str = Field(..., description="1-2 sentence coaching narrative")
    icon: str = Field(default="", description="Icon identifier or emoji")


class ExecutiveSummaryResponse(BaseModel):
    user_id: str
    summary_narrative: str = Field(..., description="Overall executive summary narrative")
    items: List[ExecutiveSummaryItem]


# ==================== 2. Training Load Analysis ====================

class WeeklyDistancePoint(BaseModel):
    week: int
    distance_km: float


class TrainingPhase(BaseModel):
    name: str = Field(..., description="Phase name, e.g. 'Base Phase'")
    weeks: str = Field(..., description="Week range, e.g. 'Weeks 1-4'")
    description: str


class TrainingLoadAnalysisResponse(BaseModel):
    user_id: str
    weekly_distance_progression: List[WeeklyDistancePoint]
    training_load_narrative: str
    phases: List[TrainingPhase]
    analysis: str


# ==================== 3. Performance Metrics ====================

class PerformanceMetricsResponse(BaseModel):
    user_id: str
    average_pace: str = Field(..., description="Current average pace, e.g. '5:15/km'")
    resting_hr: int = Field(..., description="Resting heart rate in bpm")
    easy_run_hr: int = Field(..., description="Average easy run HR in bpm")
    tempo_hr: int = Field(..., description="Average tempo HR in bpm")
    pace_progression_narrative: str
    hr_analysis_narrative: str


# ==================== 4. Weekly Training Breakdown ====================

class WeeklyBreakdownEntry(BaseModel):
    week: int
    distance_km: float
    runs: int
    avg_pace: str
    long_run_km: float


class WeeklyTrainingBreakdownResponse(BaseModel):
    user_id: str
    weeks: List[WeeklyBreakdownEntry]
    summary: str


# ==================== 5. Recommendations & Insights ====================

class RecommendationItem(BaseModel):
    title: str
    detail: str


class RecommendationsInsightsResponse(BaseModel):
    user_id: str
    strengths: List[RecommendationItem]
    areas_for_improvement: List[RecommendationItem]
    next_steps: List[RecommendationItem]


# ==================== 6. Training Zone Distribution ====================

class ZoneData(BaseModel):
    zone: str = Field(..., description="Zone name, e.g. 'Zone 1 (Recovery)'")
    percentage: float
    description: str


class TrainingZoneDistributionResponse(BaseModel):
    user_id: str
    zones: List[ZoneData]
    optimal_distribution_narrative: str
    current_assessment: str


# ==================== 7. Key Achievements ====================

class AchievementItem(BaseModel):
    title: str
    value: str
    detail: str


class KeyAchievementsResponse(BaseModel):
    user_id: str
    achievements: List[AchievementItem]
    summary: str
