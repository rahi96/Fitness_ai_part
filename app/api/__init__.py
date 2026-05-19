from fastapi import APIRouter
from app.api.routes import chat, strava

# Create main router
api_router = APIRouter()

# Include routes
api_router.include_router(chat.router)
api_router.include_router(strava.router)
