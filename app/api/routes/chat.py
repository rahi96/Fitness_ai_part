from fastapi import APIRouter, HTTPException
from app.config import OPENAI_API_KEY
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
)
from app.services.chat_service import (
    ensure_thread_id,
    generate_chat_response,
    fetch_history,
)

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set.")

    session_id = ensure_thread_id(payload.session_id, payload.user_id)
    try:
        reply = generate_chat_response(
            session_id=session_id,
            user_message=payload.message
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI chat request failed: {exc}",
        ) from exc

    return {"session_id": session_id, "response": reply}


@router.get("/chat/history/{session_id}", response_model=ChatHistoryResponse)
async def chat_history(session_id: str):
    history = fetch_history(session_id)
    return {"session_id": session_id, "history": history}
