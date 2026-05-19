Fitness Analyst Chatbot
=======================

FastAPI-based chatbot API backed by LangChain + OpenAI, with per-user chat sessions persisted in MongoDB. Provides a health check, chat endpoint that auto-manages session IDs, and chat history retrieval.

Project Structure
-----------------
- `app/main.py` — FastAPI app wiring and router include.
- `app/api/v1/endpoints/chat.py` — API routes (`/health`, `/chat`, `/chat/history/{session_id}`).
- `app/services/chat_service.py` — Session management, chat invocation, history handling.
- `app/model/llm.py` — LangChain pipeline and Mongo-backed history store.
- `app/schemas/chat.py` — Pydantic request/response models.
- `app/config.py` — Core settings (OpenAI + Mongo).
- `sample_mongo_connection.py` — Quick connectivity check for Mongo.
- `Dockerfile`, `docker-compose.yml` — Containerization and optional local Mongo service.

Environment
-----------
Create a `.env` in the project root (kept out of git). Required keys:
```
OPENAI_API_KEY=sk-...
MONGO_URI=mongodb+srv://<user>:<pass>@<host>/<db>?authSource=admin
MONGODB_DB_NAME=chatbot
MONGODB_COLLECTION=chat_sessions
```
For local Docker Mongo (see below), you can use:
```
MONGO_URI=mongodb://root:rootpassword@mongodb:27017/chatbot?authSource=admin
```

Installation (local)
--------------------
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API Usage
---------
- Health: `GET /api/v1/health` → `{"status":"ok"}`
- Chat: `POST /api/v1/chat`
  - Body: `{"user_id": "user123", "message": "Hi"}` (optional `session_id` to reuse; if omitted/blank, a session is auto-created or reused for that user)
  - Response: `{"session_id": "...", "response": "..."}` (both user and assistant turns are persisted)
- History: `GET /api/v1/chat/history/{session_id}` → returns all turns for that session.

Sample Flow
-----------
Request:
```
POST /api/v1/chat
{
  "user_id": "runner42",
  "message": "I want to start 5K training. Any tips?"
}
```
Response:
```
{
  "session_id": "a1b2c3d4e5f6...",
  "response": "Great goal! Start with 3 runs/week, mix easy jogs and walk intervals. Aim for 20-30 minutes, and add one rest day between runs. Want a 4-week plan?"
}
```
History:
```
GET /api/v1/chat/history/a1b2c3d4e5f6...
{
  "session_id": "a1b2c3d4e5f6...",
  "history": [
    {"role": "user", "content": "I want to start 5K training. Any tips?"},
    {"role": "assistant", "content": "Great goal! Start with 3 runs/week, mix easy jogs and walk intervals. Aim for 20-30 minutes, and add one rest day between runs. Want a 4-week plan?"}
  ]
}
```

Docker
------
Build and run with Compose (includes MongoDB):
```
docker compose up --build
```
Then call the API at `http://localhost:8000/api/v1/...`.

Troubleshooting
---------------
- Mongo auth errors: verify `MONGO_URI` credentials and IP allowlist; URL-encode special characters in passwords.
- Connection cert issues: `app/model/llm.py` uses `certifi` to validate TLS for Atlas.

# Fitness AI Chatbot - System Architecture

## Overview
A professional fitness AI chatbot built with:
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation
- **LangChain** - LLM orchestration
- **MongoDB** - Conversation storage
- **OpenAI** - LLM provider

## Project Structure
```
lionscull_fitness_AI/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Settings and configuration
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py         # Chat endpoints (POST, GET)
│   │   │   └── health.py       # Health check
│   │   └── __init__.py
│   ├── schemas/
│   │   └── chat.py             # Pydantic models
│   ├── services/
│   │   └── chat_service.py     # LangChain chat logic
│   └── utils/
│       └── database.py         # MongoDB manager
├── config/
│   └── config.yaml             # Additional config
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
└── README.md

## Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Environment Variables
```bash
cp .env.example .env
```

Edit `.env` and add:
- `OPENAI_API_KEY`: Your OpenAI API key
- `MONGODB_URL`: MongoDB connection string (default: localhost:27017)

### 3. Ensure MongoDB is Running
```bash
# If using local MongoDB
mongod

# Or using Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

## Running the Application

### Development Mode
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### 1. Health Check
```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Fitness AI Chatbot"
}
```

### 2. Send Chat Message (POST)
```
POST /api/v1/chat/
```

**Request:**
```json
{
  "session_id": "user_123",
  "message": "How do I build muscle effectively?"
}
```

**Response:**
```json
{
  "session_id": "user_123",
  "user_message": "How do I build muscle effectively?",
  "assistant_response": "To build muscle effectively...",
  "timestamp": "2024-12-22T10:30:00"
}
```

### 3. Get Conversation History (GET)
```
GET /api/v1/chat/{session_id}
```

**Response:**
```json
{
  "session_id": "user_123",
  "messages": [
    {
      "role": "user",
      "content": "How do I build muscle effectively?",
      "timestamp": "2024-12-22T10:30:00"
    },
    {
      "role": "assistant",
      "content": "To build muscle effectively...",
      "timestamp": "2024-12-22T10:30:05"
    }
  ],
  "total_messages": 2
}
```

## Processing Flow

### POST /api/v1/chat/
1. ✅ Validate input (Pydantic checks session_id & message)
2. ✅ Fetch chat history from MongoDB
3. ✅ Construct prompt (System Prompt → History → User Message)
4. ✅ Send to OpenAI LLM
5. ✅ Save conversation to MongoDB
6. ✅ Return response

### GET /api/v1/chat/{session_id}
1. ✅ Validate session_id
2. ✅ Retrieve from MongoDB
3. ✅ Format and return conversation history

## System Prompt

The AI is configured with a professional fitness persona:
- Formal and polite tone
- Respectful and concise responses
- Professional language (no slang)
- Fitness and health expertise
- Well-structured answers

## MongoDB Schema

```javascript
{
  "_id": ObjectId,
  "session_id": "user_123",
  "messages": [
    {
      "user": "How do I build muscle?",
      "assistant": "To build muscle...",
      "timestamp": ISODate("2024-12-22T10:30:00Z")
    }
  ],
  "created_at": ISODate("2024-12-22T10:25:00Z"),
  "updated_at": ISODate("2024-12-22T10:30:00Z")
}
```

## Configuration

Edit `app/config.py` to customize:
- System prompt
- OpenAI model
- MongoDB details
- API settings

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (missing/invalid data)
- `500`: Server error

## Testing

Use curl or Postman:

```bash
# Health check
curl http://localhost:8000/health

# Send message
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"session_id":"user_123","message":"Hello"}'

# Get history
curl http://localhost:8000/api/v1/chat/user_123
```

## Development Notes

- All timestamps are UTC
- Messages are stored in MongoDB with both user and assistant content
- Chat history is ordered chronologically (old → new)
- System prompt is applied to every request
- Conversation context is maintained across requests within the same session_id

## Future Enhancements

- [ ] User authentication
- [ ] Rate limiting
- [ ] Message search/filtering
- [ ] Conversation export
- [ ] Analytics dashboard
- [ ] Multiple AI models
- [ ] Custom system prompts per user
