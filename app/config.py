
import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

MODEL_NAME = "gpt-4o-mini"  
TEMPERATURE = 0.4
MAX_TOKENS = 500

MONGODB_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "chatbot")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "chat_sessions")

ANALYSIS_CACHE_MONGODB_URI = os.getenv("ANALYSIS_CACHE_MONGODB_URI", "mongodb://localhost:27017")
ANALYSIS_CACHE_DB_NAME = os.getenv("ANALYSIS_CACHE_DB_NAME", MONGODB_DB_NAME)
ANALYSIS_CACHE_COLLECTION = os.getenv("ANALYSIS_CACHE_COLLECTION", "training_analysis_cache")
