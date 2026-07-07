# KFC Instalaciones App Backend

FastAPI service for the MKP One KFC app installs dashboard. It proxies Windsor.ai from the server, stores normalized daily rows, builds Monday-Sunday weekly aggregates, and exposes authenticated and public-token dashboard views.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

By default the code can run with SQLite if `DATABASE_URL` is omitted. The included Docker setup runs the API with MariaDB.

## Run with Docker

```bash
docker compose up --build
```

The API will be available at:

```text
http://localhost:8030
```

The generated `.env` is configured for local/dev mode with `AUTH_DISABLED=true` and no Azure variables.

## Endpoints

- `GET /health`
- `GET /api/kfc-app-installs/dashboard?from=2025-12-29&to=2026-07-07`
- `POST /api/kfc-app-installs/refresh`
- `POST /api/kfc-app-installs/share`
- `DELETE /api/kfc-app-installs/share`
- `GET /api/public/kfc-app-installs/{shareToken}?from=2025-12-29&to=2026-07-07`

Private endpoints require `Authorization: Bearer <MSAL idToken>` and a role of `Planners` or `admin`.

## Windsor fields

The service uses these install fields:

- Meta Ads: `actions_mobile_app_install`
- TikTok Ads: `app_install`
- Google Ads: `biddable_app_install_conversions`

Google Ads intentionally never reads `conversions`.

The Windsor client also exposes `fetch_fields()` and `fetch_options()` helpers so field names can be checked with the configured API key.

## Tests

```bash
pytest
```
