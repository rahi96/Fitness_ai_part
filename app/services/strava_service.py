import json
import aiohttp
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from app.utils.database import MongoDBManager

logger = logging.getLogger(__name__)


DEFAULT_DATA_PATH = Path(__file__).resolve().parents[2] / "dummy_data.json"


def load_training_data(path: Path | None = None) -> Dict[str, Any]:
    """Load Strava-like training data from disk."""
    data_path = path or DEFAULT_DATA_PATH
    if not data_path.exists():
        raise FileNotFoundError(f"Training data file not found: {data_path}")
    with data_path.open("r", encoding="utf-8") as f:
        return json.load(f)


class StravaService:
    """Service to handle Strava API integration"""

    STRAVA_API_BASE = "https://www.strava.com/api/v3"
    STRAVA_AUTH_BASE = "https://www.strava.com/oauth/authorize"
    STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"

    def __init__(self, client_id: str, client_secret: str, db_manager: MongoDBManager):
        self.client_id = client_id
        self.client_secret = client_secret
        self.db = db_manager

    async def get_auth_url(self, redirect_uri: str, state: str) -> str:
        """Generate Strava OAuth authorization URL"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "activity:read_all,profile:read_all",
            "state": state,
            "approval_prompt": "force"
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.STRAVA_AUTH_BASE}?{query_string}"

    async def exchange_token(self, code: str) -> dict:
        """Exchange authorization code for access token"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code"
            }
            async with session.post(self.STRAVA_TOKEN_URL, data=payload) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to exchange token: {resp.status}")
                return await resp.json()

    async def refresh_access_token(self, user_id: str) -> str:
        """Refresh expired access token using refresh token"""
        athlete = await self.db.get_strava_athlete(user_id)
        if not athlete:
            raise Exception(f"No Strava athlete found for user {user_id}")

        refresh_token = athlete.get("refresh_token")
        if not refresh_token:
            raise Exception(f"No refresh token available for user {user_id}")

        async with aiohttp.ClientSession() as session:
            payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
            async with session.post(self.STRAVA_TOKEN_URL, data=payload) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to refresh token: {resp.status}")
                token_data = await resp.json()

                # Update in database
                await self.db.update_strava_athlete(
                    user_id,
                    {
                        "access_token": token_data.get("access_token"),
                        "refresh_token": token_data.get("refresh_token"),
                        "token_expires_at": datetime.utcfromtimestamp(token_data.get("expires_at", 0)),
                        "updated_at": datetime.utcnow()
                    }
                )
                return token_data.get("access_token")

    async def get_athlete_info(self, access_token: str) -> dict:
        """Get authenticated athlete profile information"""
        headers = {"Authorization": f"Bearer {access_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.STRAVA_API_BASE}/athlete", headers=headers) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to fetch athlete info: {resp.status}")
                return await resp.json()

    async def fetch_activities(self, access_token: str, after: Optional[int] = None, 
                              per_page: int = 30, max_pages: int = 10) -> List[dict]:
        """Fetch activities from Strava API"""
        activities = []
        page = 1
        headers = {"Authorization": f"Bearer {access_token}"}

        async with aiohttp.ClientSession() as session:
            while page <= max_pages:
                params = {
                    "page": page,
                    "per_page": per_page
                }
                if after:
                    params["after"] = after

                async with session.get(
                    f"{self.STRAVA_API_BASE}/athlete/activities",
                    headers=headers,
                    params=params
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to fetch activities: {resp.status}")
                        break

                    page_activities = await resp.json()
                    if not page_activities:
                        break

                    activities.extend(page_activities)
                    page += 1

        return activities

    async def sync_activities(self, user_id: str, access_token: str) -> Tuple[int, int]:
        """
        Sync activities from Strava to MongoDB.
        Returns (total_synced, new_activities)
        """
        try:
            # Get last sync timestamp
            athlete = await self.db.get_strava_athlete(user_id)
            last_sync = athlete.get("last_sync_timestamp") if athlete else None
            after_timestamp = int(last_sync.timestamp()) if last_sync else None

            # Fetch activities
            activities = await self.fetch_activities(access_token, after=after_timestamp)
            logger.info(f"Fetched {len(activities)} activities for user {user_id}")

            # Save to database
            new_count = 0
            for activity in activities:
                is_new = await self.db.save_strava_activity(user_id, activity)
                if is_new:
                    new_count += 1

            # Update last sync time
            if athlete:
                await self.db.update_strava_athlete(
                    user_id,
                    {
                        "last_sync_timestamp": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                )

            logger.info(f"Synced {len(activities)} activities, {new_count} new for user {user_id}")
            return len(activities), new_count

        except Exception as e:
            logger.error(f"Error syncing activities: {str(e)}")
            raise

    async def get_user_activities(self, user_id: str, days_back: int = 30, 
                                 activity_type: Optional[str] = None) -> List[dict]:
        """Get activities for a user from MongoDB"""
        from_date = datetime.utcnow() - timedelta(days=days_back)
        return await self.db.get_strava_activities(user_id, from_date, activity_type)
