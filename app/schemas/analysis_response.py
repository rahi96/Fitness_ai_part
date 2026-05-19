from typing import List
from pydantic import BaseModel


class AnalysisMetric(BaseModel):
    label: str
    value: float
    unit: str = "%"


class AnalysisAchievement(BaseModel):
    title: str
    detail: str


class TrainingSummary(BaseModel):
    headline: str
    narrative: str
    metrics: List[AnalysisMetric]


class TrainingAnalysisResponse(BaseModel):
    plan_title: str
    timeframe: str
    summary: TrainingSummary
    achievements: List[AnalysisAchievement]
