# Lionscull Fitness AI

An AI-powered fitness analysis API for turning structured running and Strava-style training data into clear coaching insights, race analysis, improvement plans, and conversational feedback.

The project is built with FastAPI, Pydantic, LangChain, OpenAI, MongoDB, and Docker. It exposes a small set of API endpoints that can be used by a frontend, mobile app, internal tool, or automation workflow.

## What It Does

Lionscull Fitness AI helps analyze endurance training data from several angles:

- Generates rule-based training summaries from structured running data.
- Produces AI-assisted race analysis with prediction accuracy, pacing insight, taper effectiveness, and recommendations.
- Creates training strengths, achievements, and improvement plans.
- Provides a chatbot API with MongoDB-backed conversation history.
- Runs batch Strava-style performance analysis for multiple athletes.
- Ships with Docker support and GitHub Actions CI/CD.

## Tech Stack

| Area | Technology |
| --- | --- |
| API framework | FastAPI |
| Runtime | Python 3.12 |
| Validation | Pydantic |
| AI orchestration | LangChain, LangChain OpenAI |
| LLM provider | OpenAI |
| Database | MongoDB |
| Server | Uvicorn |
| Packaging | pip / uv-compatible metadata |
| Containers | Docker, Docker Compose |
| CI/CD | GitHub Actions |

## Project Structure

```text
.
|-- app/
|   |-- api/routes/          # FastAPI route modules
|   |-- model/               # LLM chain and chat persistence wiring
|   |-- schemas/             # Pydantic request/response models
|   |-- services/            # Analysis, chat, Strava, and data services
|   |-- utils/               # Prompts, templates, database utilities
|   |-- config.py            # Environment-driven app config
|   `-- main.py              # FastAPI application entrypoint
|-- .github/workflows/       # CI and image publishing workflows
|-- Dockerfile
|-- docker-compose.yml
|-- pyproject.toml
|-- requirements.txt
`-- uv.lock
```

## API Overview

The application is served from `app.main:app`.

### Health

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Basic health check used for local verification. |

### Chat

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/chat` | Sends a user message to the fitness chatbot and stores history by session. |
| `GET` | `/api/v1/chat/history/{session_id}` | Fetches stored chat history for a session. |

### Training Analysis

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/training/analysis` | Generates a lightweight structured training analysis without calling the LLM. |
| `POST` | `/api/v1/ai/race-analysis` | Uses OpenAI to produce race analysis, prediction insight, recommendations, and build-up summary. |
| `POST` | `/api/v1/ai/training-insights` | Uses OpenAI to identify strengths and achievements from training context. |
| `POST` | `/api/v1/ai/improvement-plan` | Uses OpenAI to generate improvement areas, next steps, and training distribution feedback. |

### Strava-Style Batch Analysis

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/strava/analyze` | Accepts an array of athlete training records and returns batch performance analysis. |

Interactive API documentation is available after startup:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Requirements

- Python 3.12+
- MongoDB, local or hosted
- OpenAI API key for AI-backed endpoints
- Docker Desktop, optional but recommended for container workflows

## Environment Variables

Create a `.env` file in the project root for local development:

```env
OPENAI_API_KEY=your_openai_api_key
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=chatbot
MONGODB_COLLECTION=chat_sessions
```

`MONGO_URI` is also supported as a MongoDB URI fallback.

For local smoke testing without real AI calls, you can use a placeholder `OPENAI_API_KEY`, but endpoints that call OpenAI need a valid key.

## Local Development

Create and activate a virtual environment:

```bash
python -m venv venv
```

On Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Check the server:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Expected response:

```json
{"status":"ok"}
```

## Docker

Build the image:

```bash
docker build -t lionscull-fitness-ai .
```

Run the API container:

```bash
docker run --env-file .env -p 8000:8000 lionscull-fitness-ai
```

Or start the app with MongoDB using Docker Compose:

```bash
docker compose up --build
```

The API will be available at:

```text
http://127.0.0.1:8000
```

## Deploying on Render

Use the Docker runtime or a Python web service with this start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set these environment variables in the Render dashboard:

```env
OPENAI_API_KEY=your_openai_api_key
MONGODB_URI=your_valid_mongodb_connection_string
MONGODB_DB_NAME=chatbot
MONGODB_COLLECTION=chat_sessions
```

If you use MongoDB Atlas, copy the connection string from the active cluster. A deleted, paused, renamed, or mistyped Atlas host will cause DNS errors like:

```text
The DNS query name does not exist: _mongodb._tcp.<cluster-host>
```

The API can now start even when MongoDB is temporarily unavailable, but chat history persistence requires a valid reachable MongoDB URI.

## Example Requests

### Health Check

```bash
curl http://127.0.0.1:8000/api/v1/health
```

### Chat

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "athlete-001",
    "session_id": null,
    "message": "How should I adjust my training after a hard race?"
  }'
```

### Batch Strava-Style Analysis

```bash
curl -X POST http://127.0.0.1:8000/api/v1/strava/analyze \
  -H "Content-Type: application/json" \
  --data-binary @data.json
```

## CI/CD

This repository includes two GitHub Actions workflows.

### CI

`.github/workflows/ci.yml` runs on pushes and pull requests to `main` or `master`.

It performs:

- Python 3.12 setup from `.python-version`
- Dependency installation from `requirements.txt`
- Merge conflict marker scan
- Python compilation check
- FastAPI smoke import
- Docker image build

### CD

`.github/workflows/cd.yml` publishes a Docker image to GitHub Container Registry.

It runs on:

- Version tags matching `v*.*.*`
- Manual `workflow_dispatch`

Published images use:

```text
ghcr.io/<owner>/<repository>
```

## Development Notes

- The chat service stores conversation history in MongoDB.
- Training analysis routes cache response payloads in MongoDB by `user_id`, route type, and request hash.
- Some analysis endpoints are deterministic and do not call OpenAI.
- AI endpoints require `OPENAI_API_KEY`.
- `dummy_data.json` and `data.json` provide sample training payloads for local experiments.
- The Docker image uses Python 3.12 to match the project metadata.

## Quality Checks

Useful local checks:

```bash
python -m compileall app main.py
python -c "from app.main import app; print(app.title)"
docker build -t lionscull-fitness-ai:local .
```

If your local `.env` points to a hosted MongoDB URI, make sure it resolves correctly before running import checks. For isolated local checks, override it:

```bash
MONGODB_URI=mongodb://localhost:27017 python -c "from app.main import app; print(app.title)"
```

On Windows PowerShell:

```powershell
$env:MONGODB_URI="mongodb://localhost:27017"
python -c "from app.main import app; print(app.title)"
```

## License

No license has been declared yet. Add one before distributing or publishing this project broadly.
