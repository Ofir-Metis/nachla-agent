# Deployment Guide

## Prerequisites
- Docker & Docker Compose
- PostgreSQL credentials
- Anthropic API key

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
ANTHROPIC_API_KEY=sk-ant-...
POSTGRES_DB=nachla
POSTGRES_USER=nachla
POSTGRES_PASSWORD=<strong-password>
DATABASE_URL=postgresql://nachla:<password>@postgres:5432/nachla

# Optional
MONDAY_API_TOKEN=<monday-api-token>
MONDAY_BOARD_ID=<board-id>
GOOGLE_CREDENTIALS_PATH=/app/credentials/google.json
ONEDRIVE_CLIENT_ID=<client-id>
```

## Docker Deployment

```bash
# Build and start all services
docker compose up -d --build

# Check health
curl http://localhost:8000/health
curl http://localhost:3000/healthz

# View logs
docker compose logs -f app
docker compose logs -f frontend
```

## Services

| Service    | Port | Description              |
|------------|------|--------------------------|
| app        | 8000 | FastAPI backend           |
| frontend   | 3000 | React UI (nginx)          |
| postgres   | 5432 | PostgreSQL database       |
| redis      | 6379 | Redis cache (future use)  |

## Database

Tables are auto-created on startup. For production migrations, use Alembic:

```bash
alembic init alembic
alembic stamp head  # Mark existing schema
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Monitoring

- Health check: `GET /health`
- Detailed health: `GET /health/detailed`
- Frontend health: `GET /healthz` (nginx)
