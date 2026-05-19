from fastapi import FastAPI
from app.api.routes import analysis
from app.api.routes import chat
from app.api.routes import chat, strava

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
