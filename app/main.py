from fastapi import FastAPI
from app.api.routes import analysis, chat, load_progression, performance, strava, overview, training_insights, heart_rate, dashboard

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
app.include_router(load_progression.router)
app.include_router(performance.router)
app.include_router(strava.router)
app.include_router(overview.router)
app.include_router(training_insights.router)
app.include_router(heart_rate.router)
app.include_router(dashboard.router)

