# H2Ops

Operations dashboard for monitoring and managing water treatment systems, telemetry,
alerts, and operational workflows across sites.

## Prerequisites
- Docker & Docker Compose v2
- Node.js 20+ (only needed if running the client outside Docker)
- Python 3.11+ (only needed if running the server outside Docker)

## 1. Clone & configure

git clone <repo-url> H2Ops
cd H2Ops
cp .env.example .env

Fill in `.env`:

POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
DATABASE_URL=

REDIS_URL=

MQTT_HOST=
MQTT_PORT=

MINIO_ROOT_USER=
MINIO_ROOT_PASSWORD=
MINIO_BUCKET=

JWT_SECRET=replace-with-a-long-random-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=20

## 2. Boot the stack

docker compose up --build

This starts, in order: `db` (Postgres+TimescaleDB) → `redis` → `mqtt_broker` → `minio`
(+ `minio-init` bucket bootstrap) → `server` → `client`.

- Client: http://localhost:3000
- Server API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001
- MQTT broker: mqtt://localhost:1883

## 3. Database migrations

The server container runs database bootstrap automatically on first startup. For schema
changes going forward, use Alembic:

docker compose exec server alembic revision --autogenerate -m "describe change"
docker compose exec server alembic upgrade head

## 4. Seed / simulate telemetry

The simulator worker starts automatically as part of the `server` service and begins
publishing synthetic telemetry over MQTT within a few seconds of boot, so the dashboard
has live data immediately — no manual seeding required.

To run it standalone against a local broker instead:

docker compose exec server python -m workers.simulator

## 5. Running services individually (without Docker)

**Server**
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

**Client**
cd client
npm install
npm run dev

## 6. Roles for local testing

Seed users are created with these roles — log in and the dashboard adapts automatically:
- `operator@h2ops.local` — Plant Operator
- `admin@h2ops.local` — Facility Admin
- `auditor@h2ops.local` — Compliance Auditor