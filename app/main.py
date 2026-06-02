from fastapi import FastAPI
from app.api.routes import analysis, chat, strava, overview, training_insights

app = FastAPI(title="Fitness Analyst Chatbot")

app.include_router(
    chat.router,
    prefix="/api/v1",
    tags=["Chatbot"]
)

app.include_router(
    analysis.router,
    prefix="/api/v1",
    tags=["Training Analysis"]
)
app.include_router(strava.router)
app.include_router(overview.router)
app.include_router(training_insights.router)
