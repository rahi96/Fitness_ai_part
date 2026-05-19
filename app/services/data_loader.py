import json
import logging
from pathlib import Path
from typing import List, Optional
from app.schemas.strava import UserTrainingData

logger = logging.getLogger(__name__)


class DataLoader:
    """Load and manage training data from JSON file"""
    
    def __init__(self, data_file_path: str = "data.json"):
        """Initialize data loader with path to data file"""
        self.data_file_path = Path(data_file_path)
        self._data_cache: Optional[List[UserTrainingData]] = None
    
    def load_all_data(self) -> List[UserTrainingData]:
        """Load all user training data from JSON file"""
        if self._data_cache is not None:
            return self._data_cache
        
        try:
            with open(self.data_file_path, 'r') as f:
                raw_data = json.load(f)
            
            # Validate and convert to Pydantic models
            self._data_cache = [UserTrainingData(**user_data) for user_data in raw_data]
            logger.info(f"Loaded {len(self._data_cache)} user records from {self.data_file_path}")
            return self._data_cache
        
        except FileNotFoundError:
            logger.error(f"Data file not found: {self.data_file_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in data file: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid data structure: {e}")
            raise
    
    def get_user_data(self, user_id: int) -> Optional[UserTrainingData]:
        """Get training data for a specific user"""
        all_data = self.load_all_data()
        for user_data in all_data:
            if user_data.user_id == user_id:
                logger.info(f"Found data for user {user_id}")
                return user_data
        
        logger.warning(f"No data found for user {user_id}")
        return None
    
    def get_all_user_ids(self) -> List[int]:
        """Get list of all available user IDs"""
        all_data = self.load_all_data()
        return [user_data.user_id for user_data in all_data]
    
    def reload_data(self) -> List[UserTrainingData]:
        """Reload data from file (clear cache)"""
        self._data_cache = None
        logger.info("Data cache cleared, reloading from file")
        return self.load_all_data()
