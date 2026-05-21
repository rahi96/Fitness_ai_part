import hashlib
import json
import logging
from datetime import datetime
from typing import Any

import certifi
from pymongo import MongoClient
from pymongo.collection import Collection

from app.config import (
    ANALYSIS_CACHE_COLLECTION,
    ANALYSIS_CACHE_DB_NAME,
    ANALYSIS_CACHE_MONGODB_URI,
)


logger = logging.getLogger(__name__)


class AnalysisCacheService:
    """Mongo-backed cache for training analysis responses."""

    def __init__(self) -> None:
        self.client: MongoClient | None = None
        self.collection: Collection | None = None
        self.connection_failed = False

    def get_cached_response(
        self,
        *,
        user_id: str | int,
        cache_type: str,
        request_payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        collection = self._get_collection()
        if collection is None:
            return None

        request_hash = self._request_hash(request_payload)
        record = collection.find_one(
            {
                "user_id": str(user_id),
                "cache_type": cache_type,
                "request_hash": request_hash,
            },
            projection={"_id": 0, "response_data": 1},
        )
        if not record:
            return None
        response_data = record.get("response_data")
        return response_data if isinstance(response_data, dict) else None

    def store_response(
        self,
        *,
        user_id: str | int,
        cache_type: str,
        request_payload: dict[str, Any],
        response_data: dict[str, Any],
    ) -> None:
        collection = self._get_collection()
        if collection is None:
            return

        now = datetime.utcnow()
        request_hash = self._request_hash(request_payload)
        collection.update_one(
            {
                "user_id": str(user_id),
                "cache_type": cache_type,
                "request_hash": request_hash,
            },
            {
                "$set": {
                    "user_id": str(user_id),
                    "cache_type": cache_type,
                    "request_hash": request_hash,
                    "request_payload": request_payload,
                    "response_data": response_data,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    def _get_collection(self) -> Collection | None:
        if self.collection is not None:
            return self.collection
        if self.connection_failed:
            return None

        try:
            self.client = MongoClient(
                ANALYSIS_CACHE_MONGODB_URI,
                serverSelectionTimeoutMS=3000,
                **self._tls_kwargs(ANALYSIS_CACHE_MONGODB_URI),
            )
            db = self.client[ANALYSIS_CACHE_DB_NAME]
            self.collection = db[ANALYSIS_CACHE_COLLECTION]
            self.collection.create_index(
                [("user_id", 1), ("cache_type", 1), ("request_hash", 1)],
                unique=True,
            )
            return self.collection
        except Exception as exc:
            self.connection_failed = True
            logger.warning("Analysis cache unavailable; continuing without Mongo cache: %s", exc)
            return None

    @staticmethod
    def _request_hash(request_payload: dict[str, Any]) -> str:
        payload_without_user = {
            key: value for key, value in request_payload.items() if key != "user_id"
        }
        serialized = json.dumps(payload_without_user, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _tls_kwargs(uri: str) -> dict[str, str]:
        if uri.startswith("mongodb+srv://") or "tls=true" in uri.lower():
            return {"tlsCAFile": certifi.where()}
        return {}


analysis_cache_service = AnalysisCacheService()
