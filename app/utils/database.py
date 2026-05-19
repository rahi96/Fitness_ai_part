from pymongo import MongoClient
from pymongo.collection import Collection
from app.config import settings
from typing import Optional, List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MongoDBManager:
    """MongoDB connection and operations manager"""
    
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection: Optional[Collection] = None
    
    def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(settings.MONGODB_URL)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[settings.MONGODB_DB_NAME]
            self.collection = self.db[settings.MONGODB_COLLECTION_NAME]
            
            # Create compound index on user_id and session_id for faster lookups
            self.collection.create_index([("user_id", 1), ("session_id", 1)], unique=False)
            
            logger.info("Connected to MongoDB successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def save_conversation(self, user_id: str, session_id: str, user_message: str, assistant_response: str) -> bool:
        """Save conversation to MongoDB"""
        try:
            message_pair = {
                "user": user_message,
                "assistant": assistant_response,
                "timestamp": datetime.utcnow()
            }
            
            result = self.collection.update_one(
                {"user_id": user_id, "session_id": session_id},
                {
                    "$push": {"messages": message_pair},
                    "$set": {"updated_at": datetime.utcnow()}
                },
                upsert=True
            )
            
            logger.info(f"Saved conversation for user {user_id}, session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            return False
    
    def get_conversation_history(self, user_id: str, session_id: str) -> List[Dict]:
        """Get conversation history from MongoDB"""
        try:
            document = self.collection.find_one({"user_id": user_id, "session_id": session_id})
            
            if document:
                return document.get("messages", [])
            return []
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
    
    def delete_conversation(self, user_id: str, session_id: str) -> bool:
        """Delete a conversation"""
        try:
            result = self.collection.delete_one({"user_id": user_id, "session_id": session_id})
            logger.info(f"Deleted conversation for user {user_id}, session {session_id}")
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            return False

    # Strava-related methods
    def _ensure_strava_collections(self):
        """Ensure Strava collections exist with proper indexes"""
        athletes_collection = self.db["strava_athletes"]
        activities_collection = self.db["strava_activities"]
        
        # Create indexes
        athletes_collection.create_index([("user_id", 1)], unique=True)
        activities_collection.create_index([("user_id", 1), ("start_date", -1)])
        activities_collection.create_index([("strava_athlete_id", 1), ("start_date", -1)])
        activities_collection.create_index([("activity_id", 1)], unique=True)

    async def save_strava_athlete(self, user_id: str, athlete_data: dict) -> bool:
        """Save or update Strava athlete information"""
        try:
            self._ensure_strava_collections()
            athletes_collection = self.db["strava_athletes"]
            
            athlete_doc = {
                "user_id": user_id,
                "strava_athlete_id": athlete_data.get("id"),
                "firstname": athlete_data.get("firstname"),
                "lastname": athlete_data.get("lastname"),
                "city": athlete_data.get("city"),
                "state": athlete_data.get("state"),
                "country": athlete_data.get("country"),
                "sex": athlete_data.get("sex"),
                "profile_picture": athlete_data.get("profile_medium"),
                "access_token": athlete_data.get("access_token"),
                "refresh_token": athlete_data.get("refresh_token"),
                "token_expires_at": datetime.utcfromtimestamp(athlete_data.get("expires_at", 0)),
                "token_scopes": athlete_data.get("scopes", []),
                "last_sync_timestamp": datetime.utcnow(),
                "created_at": datetime.utcnow() if not await self.get_strava_athlete(user_id) else None,
                "updated_at": datetime.utcnow()
            }
            
            # Remove None values and created_at if updating
            if athlete_doc["created_at"] is None:
                del athlete_doc["created_at"]
            athlete_doc = {k: v for k, v in athlete_doc.items() if v is not None}
            
            athletes_collection.update_one(
                {"user_id": user_id},
                {"$set": athlete_doc},
                upsert=True
            )
            logger.info(f"Saved Strava athlete for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving Strava athlete: {e}")
            return False

    async def get_strava_athlete(self, user_id: str) -> Optional[Dict]:
        """Get Strava athlete information"""
        try:
            self._ensure_strava_collections()
            athletes_collection = self.db["strava_athletes"]
            return athletes_collection.find_one({"user_id": user_id})
        except Exception as e:
            logger.error(f"Error retrieving Strava athlete: {e}")
            return None

    async def update_strava_athlete(self, user_id: str, update_data: dict) -> bool:
        """Update Strava athlete information"""
        try:
            self._ensure_strava_collections()
            athletes_collection = self.db["strava_athletes"]
            
            result = athletes_collection.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )
            logger.info(f"Updated Strava athlete for user {user_id}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating Strava athlete: {e}")
            return False

    async def save_strava_activity(self, user_id: str, activity_data: dict) -> bool:
        """Save or update Strava activity. Returns True if new, False if updated"""
        try:
            self._ensure_strava_collections()
            activities_collection = self.db["strava_activities"]
            
            activity_doc = {
                "user_id": user_id,
                "strava_athlete_id": activity_data.get("athlete", {}).get("id"),
                "activity_id": activity_data.get("id"),
                "name": activity_data.get("name"),
                "type": activity_data.get("type"),
                "sport_type": activity_data.get("sport_type"),
                "distance": activity_data.get("distance"),
                "moving_time": activity_data.get("moving_time"),
                "elapsed_time": activity_data.get("elapsed_time"),
                "total_elevation_gain": activity_data.get("total_elevation_gain"),
                "elev_high": activity_data.get("elev_high"),
                "elev_low": activity_data.get("elev_low"),
                "average_speed": activity_data.get("average_speed"),
                "max_speed": activity_data.get("max_speed"),
                "average_heartrate": activity_data.get("average_heartrate"),
                "max_heartrate": activity_data.get("max_heartrate"),
                "average_watts": activity_data.get("average_watts"),
                "max_watts": activity_data.get("max_watts"),
                "weighted_average_watts": activity_data.get("weighted_average_watts"),
                "average_cadence": activity_data.get("average_cadence"),
                "achievement_count": activity_data.get("achievement_count"),
                "kudos_count": activity_data.get("kudos_count"),
                "start_date": activity_data.get("start_date"),
                "start_date_local": activity_data.get("start_date_local"),
                "timezone": activity_data.get("timezone"),
                "trainer": activity_data.get("trainer"),
                "commute": activity_data.get("commute"),
                "manual": activity_data.get("manual"),
                "private": activity_data.get("private"),
                "synced_at": datetime.utcnow(),
                "raw_data": activity_data
            }
            
            # Remove None values
            activity_doc = {k: v for k, v in activity_doc.items() if v is not None}
            
            result = activities_collection.update_one(
                {"activity_id": activity_data.get("id")},
                {
                    "$set": activity_doc,
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )
            
            is_new = result.upserted_id is not None
            logger.info(f"{'New' if is_new else 'Updated'} Strava activity {activity_data.get('id')} for user {user_id}")
            return is_new
        except Exception as e:
            logger.error(f"Error saving Strava activity: {e}")
            return False

    async def get_strava_activities(self, user_id: str, from_date: datetime = None, 
                                   activity_type: Optional[str] = None) -> List[Dict]:
        """Get Strava activities for a user"""
        try:
            self._ensure_strava_collections()
            activities_collection = self.db["strava_activities"]
            
            query = {"user_id": user_id}
            if from_date:
                query["start_date"] = {"$gte": from_date.isoformat()}
            if activity_type:
                query["type"] = activity_type
            
            activities = list(activities_collection.find(query).sort("start_date", -1))
            logger.info(f"Retrieved {len(activities)} activities for user {user_id}")
            return activities
        except Exception as e:
            logger.error(f"Error retrieving Strava activities: {e}")
            return []

    async def delete_strava_activities(self, user_id: str) -> bool:
        """Delete all Strava activities for a user"""
        try:
            self._ensure_strava_collections()
            activities_collection = self.db["strava_activities"]
            
            result = activities_collection.delete_many({"user_id": user_id})
            logger.info(f"Deleted {result.deleted_count} activities for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting Strava activities: {e}")
            return False

# Global database instance
db_manager = MongoDBManager()
