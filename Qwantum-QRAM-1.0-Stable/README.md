# Qwantum QRAM 1.0 Stable

**Stable release 1.0.0** of the Qwantum QRAM software simulator. It includes SQLite-backed addressable memory, versioned database migrations, experiment persistence and audit events, an optional Qiskit Aer circuit-simulation bridge, configurable API-key protection, process-local rate limiting, and a browser UI.

> Important: QRAM in this repository is a software architecture/simulator. It is not physical quantum RAM and does not provide 777 physical qubits. QWP-777 and Nebiru are unconnected integration contracts until actual device protocols/services are implemented and configured.

## Release status
- Application version: `1.0.0` (stable).
- SQLite schema version: `3`.
- Automated regression tests: `32 passed` in the release environment.
- Deployment model: local-first. Public internet deployment requires additional operational security and deployment testing.

## Features
- Addressable memory read/write with per-cell revisions and history.
- SQLite storage for data and experiment records.
- Transactional, versioned migrations (`schema_migrations`).
- Persistent experiment status, metadata, JSON results, and event history.
- Optional Qiskit Aer circuit simulation; it runs on classical hardware.
- API key via `QRAM_API_KEY` and request header `X-API-Key`.
- Process-local per-client rate limiting via `QRAM_RATE_LIMIT`.
- FastAPI docs and responsive browser UI.

## Requirements
Python 3.11+ recommended. Docker Compose is optional.

## Install and run locally
```bash
python -m venv .venv
```

Windows PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:
```bash
source .venv/bin/activate
```

Install and start:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open the UI at `http://127.0.0.1:8000/` and API docs at `http://127.0.0.1:8000/docs`.

## Enable API-key protection
Set a strong, unique random secret before starting the application.

Linux/macOS:
```bash
export QRAM_API_KEY='replace-with-a-long-random-secret'
export QRAM_RATE_LIMIT=120
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Windows PowerShell:
```powershell
$env:QRAM_API_KEY = "replace-with-a-long-random-secret"
$env:QRAM_RATE_LIMIT = "120"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In the browser UI, enter the same secret in **Klucz API** and select **Zastosuj klucz**. The UI stores it in `sessionStorage` for the current browser session and sends it as `X-API-Key`. `/api/health` and `/api/version` remain public; other `/api/*` routes require the key when it is configured.

**Local-development compatibility:** if `QRAM_API_KEY` is unset, API-key enforcement is disabled. Keep the service bound to localhost in this mode. Do not expose the open mode to a network.

## Docker Compose
Copy `.env.example` to `.env`, set `QRAM_API_KEY` to a strong unique random secret, then run:
```bash
docker compose up --build -d
```

Compose publishes the port on `127.0.0.1:8000` and persists the SQLite database in `./data/qram.db`. Keep `.env` private and do not commit it. Stop the service with `docker compose down`.

## Rate limits
`QRAM_RATE_LIMIT` defaults to 120 API requests per client IP in a 60-second window. Public health/version routes are excluded. The limiter is in-process, not shared between multiple workers/replicas, and is not a DDoS defense. A reverse proxy should apply its own limits and trusted client-IP configuration for remote deployments.

## Optional Qiskit Aer simulator
```bash
pip install -r requirements-quantum.txt
```

Check `GET /api/quantum/backend`. The adapter performs classical circuit simulation. Measurement returns sampled bitstrings; it does not reveal all quantum states from one measurement. State-vector costs grow exponentially, so the demo has a small qubit cap.

## API highlights
- `GET /api/health`, `GET /api/version`
- `GET /api/integrations/capabilities`
- `POST /api/experiments`, `GET /api/experiments`
- `GET /api/experiments/{experiment_id}`
- `GET /api/experiments/{experiment_id}/history`
- `POST /api/experiments/{experiment_id}/run`
- `GET /api/memory`, `POST /api/memory/write`
- `GET /api/memory/read/{address}`, `GET /api/memory/history/{address}`
- `DELETE /api/memory`
- `GET /api/quantum/backend`, `POST /api/quantum/circuit-demo`, `POST /api/quantum/demo`

Full interactive API schemas are available at `/docs`.

## Tests
```bash
pytest -q
```

## Persistence, migrations, and backups
Default database path: `data/qram.db`, configurable with `QRAM_DATABASE_PATH`. Database migrations run on application startup. The service supports the schemas used by the earlier QRAM SQLite versions in this project and fails fast rather than opening a database with a newer unsupported schema version. Before upgrading an existing database, create a backup. Stop the application cleanly before copying the SQLite file; retain backups securely if data is sensitive.

## Security limitations
- API key is one shared secret, not per-user authentication or role-based access control.
- Rate limiting is process-local.
- The built-in server is intended for local use. Remote deployment requires HTTPS, a configured reverse proxy, secret management, monitoring, backup/restore validation, and additional security testing.
- Do not treat this release as a safety-certified or quantum-hardware control system.

## Release notes
See `RELEASE_NOTES.md` and `CHANGELOG.md`.
