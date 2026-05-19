
from typing import Optional, List
from pydantic import BaseModel


class ChatRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatSessionHistory(BaseModel):
    session_id: str
    history: List[ChatMessage]


class ChatHistoryResponse(BaseModel):
    session_id: str
    history: List[ChatMessage]
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum
import uuid

class MessageRole(str, Enum):
    """Message role enumeration"""
    USER = "user"
    ASSISTANT = "assistant"

class Message(BaseModel):
    """Single message in conversation"""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatHistory(BaseModel):
    """Chat history for GET endpoint"""
    user_id: str
    session_id: str
    messages: List[Message]
    total_messages: int

class ConversationDocument(BaseModel):
    """MongoDB document for conversation"""
    user_id: str
    session_id: str
    messages: List[dict]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        arbitrary_types_allowed = True
