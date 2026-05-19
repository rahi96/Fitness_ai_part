
from app.model.llm import (
    append_history,
    create_thread_id,
    get_chat_chain,
    get_history,
    get_session_id_for_user,
)


def ensure_thread_id(session_id: str | None, user_id: str) -> str:
    # Treat missing, empty, or placeholder "string" session_id as a new session request.
    if session_id and session_id.strip().lower() != "string":
        return session_id

    existing = get_session_id_for_user(user_id)
    if existing:
        return existing

    return create_thread_id(user_id)


def generate_chat_response(session_id: str, user_message: str) -> str:
    chain = get_chat_chain(session_id)
    append_history(session_id, "user", user_message)
    ai_message = chain.invoke(
        {"input": user_message},
        config={"configurable": {"session_id": session_id}},
    )
    response_text = getattr(ai_message, "content", str(ai_message))
    append_history(session_id, "assistant", response_text)
    return response_text


def fetch_history(session_id: str):
    return get_history(session_id)