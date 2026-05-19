from uuid import uuid4
from typing import Dict, List

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from pymongo import MongoClient
from pymongo.collection import Collection
import certifi

from app.config import (
    OPENAI_API_KEY,
    MODEL_NAME,
    TEMPERATURE,
    MONGODB_URI,
    MONGODB_DB_NAME,
    MONGODB_COLLECTION,
)
from app.utils.prompt import SYSTEM_PROMPT


memory_store: Dict[str, InMemoryChatMessageHistory] = {}
MAX_CONTEXT_MESSAGES = 5

mongo_client = MongoClient(MONGODB_URI, tlsCAFile=certifi.where())
mongo_db = mongo_client[MONGODB_DB_NAME]
chat_sessions: Collection = mongo_db[MONGODB_COLLECTION]


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("history"),
        ("human", "{input}"),
    ]
)


def _base_chain():
    llm = ChatOpenAI(
        api_key=OPENAI_API_KEY,
        model=MODEL_NAME,
        temperature=TEMPERATURE,
    )
    return prompt | llm


def _ensure_thread(thread_id: str) -> None:
    if thread_id in memory_store:
        return

    history = _load_history_from_db(thread_id)
    if not history:
        _create_session_if_missing(thread_id)
    memory = InMemoryChatMessageHistory()
    for message in history[-MAX_CONTEXT_MESSAGES:]:
        memory.add_message(to_message(message["role"], message["content"]))
    _trim_memory(memory)
    memory_store[thread_id] = memory


def create_thread_id(user_id: str | None = None) -> str:
    thread_id = uuid4().hex
    _create_session_if_missing(thread_id, user_id=user_id)
    _ensure_thread(thread_id)
    return thread_id


def get_chat_chain(thread_id: str) -> RunnableWithMessageHistory:
    _ensure_thread(thread_id)
    return RunnableWithMessageHistory(
        _base_chain(),
        lambda config: _get_memory(config, thread_id=thread_id),
        input_messages_key="input",
        history_messages_key="history",
    )


def append_history(thread_id: str, role: str, content: str) -> None:
    _ensure_thread(thread_id)
    _create_session_if_missing(thread_id)
    memory_store[thread_id].add_message(to_message(role, content))
    _trim_memory(memory_store[thread_id])
    chat_sessions.update_one(
        {"session_id": thread_id},
        {"$push": {"history": {"role": role, "content": content}}},
        upsert=False,
    )


def get_history(thread_id: str) -> List[dict[str, str]]:
    return _load_history_from_db(thread_id)


def to_message(role: str, content: str) -> BaseMessage:
    return HumanMessage(content=content) if role == "user" else AIMessage(content=content)


def _get_memory(_: dict, *, thread_id: str) -> InMemoryChatMessageHistory:
    _ensure_thread(thread_id)
    return memory_store[thread_id]


def _create_session_if_missing(thread_id: str, user_id: str | None = None) -> None:
    chat_sessions.update_one(
        {"session_id": thread_id},
        {
            "$setOnInsert": {
                "session_id": thread_id,
                "user_id": user_id,
                "history": [],
            }
        },
        upsert=True,
    )


def _load_history_from_db(thread_id: str) -> List[dict[str, str]]:
    record = chat_sessions.find_one(
        {"session_id": thread_id},
        projection={"_id": 0, "history": 1},
    )
    return record.get("history", []) if record else []


def get_session_id_for_user(user_id: str) -> str | None:
    record = chat_sessions.find_one(
        {"user_id": user_id},
        projection={"_id": 0, "session_id": 1},
    )
    if record:
        return record.get("session_id")
    return None


def _trim_memory(memory: InMemoryChatMessageHistory) -> None:
    while len(memory.messages) > MAX_CONTEXT_MESSAGES:
        memory.messages.pop(0)
 