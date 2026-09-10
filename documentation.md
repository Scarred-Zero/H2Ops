# H2Ops — Architecture

---

## 1. Monorepo Directory Tree

```
H2Ops/
├── .env.example                             # shared environment variable template
├── .gitignore                                # repository ignore rules
├── docker-compose.yml                         # container orchestration for app stack
├── documentation.md                           # architecture and project notes
├── LICENSE                                    # project license
├── prometheus.yml                             # monitoring configuration
├── README.md                                  # project setup and usage
├── stuff.txt                                  # local scratch/notes
├── client/                                    # Next.js frontend application
│   ├── .dockerignore                          # Docker build exclusions
│   ├── .gitignore                             # client-specific ignore rules
│   ├── AGENTS.md                              # client agent guidance
│   ├── CLAUDE.md                              # client development guidance
│   ├── components.json                        # UI component configuration
│   ├── Dockerfile                             # client container image
│   ├── eslint.config.mjs                      # ESLint configuration
│   ├── next-env.d.ts                          # Next.js generated type declarations
│   ├── next.config.ts                         # Next.js configuration
│   ├── package.json                            # client dependencies and scripts
│   ├── package-lock.json                       # locked npm dependency versions
│   ├── postcss.config.mjs                     # PostCSS configuration
│   ├── proxy.ts                               # client proxy configuration
│   ├── README.md                              # client-specific documentation
│   ├── tailwind.config.ts                     # Tailwind CSS configuration
│   ├── tsconfig.json                           # TypeScript configuration
│   ├── app/                                    # App Router pages and styles
│   │   ├── favicon.ico                         # browser tab icon
│   │   ├── globals.css                         # global styles
│   │   ├── layout.tsx                          # root layout
│   │   └── page.tsx                            # home page
│   ├── components/                             # reusable UI components
│   │   └── ui/
│   │       └── button.tsx                      # shared button component
│   ├── lib/                                    # client utilities and API access
│   │   ├── apiClient.ts                        # server API client
│   │   └── utils.ts                            # shared client utilities
│   ├── public/                                 # static assets
│   └── types/                                  # shared client TypeScript types
│
├── server/                                     # FastAPI backend application
│   ├── .dockerignore                           # Docker build exclusions
│   ├── .python-version                         # project Python version
│   ├── alembic.ini                             # Alembic configuration
│   ├── Dockerfile                              # server container image
│   ├── main.py                                 # FastAPI application entry point
│   ├── pyproject.toml                          # Python project and dependency metadata
│   ├── README.md                               # server-specific documentation
│   ├── uv.lock                                 # locked Python dependency versions
│   ├── alembic/                                # database migration configuration
│   │   ├── README
│   │   ├── env.py
│   │   ├── script.py.mako                      # migration template
│   │   └── versions/                           # generated migration revisions
│   └── src/
│       ├── __init__.py                         # source package marker
│       ├── api/                                # API dependency and route modules
│       │   └── v1/
│       │       └── routes/
│       │           ├── __init__.py
│       │           ├── auth.py                  # authentication routes
│       │           ├── device.py                # device routes
│       │           └── ws.py                    # WebSocket routes
│       ├── aws/                                # AWS integration helpers
│       │   ├── client.py
│       │   ├── config.py
│       │   ├── constants.py
│       │   ├── exceptions.py
│       │   ├── schemas.py
│       │   └── utils.py
│       ├── core/                               # application infrastructure
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── database.py
│       │   ├── exceptions.py
│       │   ├── metrics.py
│       │   └── security.py
│       ├── dependencies/                       # FastAPI dependency providers
│       │   ├── __init__.py
│       │   └── auth.py
│       ├── models/                             # SQLAlchemy domain models
│       │   ├── __init__.py
│       │   ├── alert.py
│       │   ├── device.py
│       │   ├── facility.py
│       │   ├── role.py
│       │   ├── telemetry_log.py
│       │   └── user.py
│       ├── repositories/                        # database access layer
│       │   ├── __init__.py
│       │   ├── telemetry_repo.py
│       │   └── user_repo.py
│       ├── schemas/                             # Pydantic request/response schemas
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   ├── device.py
│       │   ├── facility.py
│       │   ├── telemetry_log.py
│       │   └── user.py
│       ├── services/                            # application services
│       │   ├── __init__.py
│       │   ├── auth_service.py
│       │   ├── mail_service.py
│       │   ├── telemetry_service.py
│       │   └── websocket_manager.py
│       ├── test/                                # server tests
│       │   ├── test_device_router.py
│       │   └── test_telemetry_repo.py
│       ├── utils/                               # shared server utilities
│       │   ├── __init__.py
│       │   ├── path_utils.py
│       │   ├── rate_limiter.py
│       │   └── redis_client.py
│       └── workers/                             # background jobs and simulation
│           ├── __init__.py
│           ├── celery_app.py
│           ├── simulator.py
│           └── tasks.py
│
└── infra/                                     # shared infrastructure bootstrap
    ├── minio/
    │   └── init-bucket.sh                      # MinIO bucket initialization
    ├── mosquitto/
    │   └── mosquitto.conf                      # MinIO bucket initialization
    └── postgres/
        └── init.sql                          # PostgreSQL initialization scripts
```

> Generated or machine-local directories such as `client/.next/`, `client/node_modules/`, `server/.venv/`, and `server/__pycache__/` are present in some workspaces but are intentionally omitted from this source tree.

## 2. Real-Time Data Flow

```
Field Device (sensor / PLC)
    │  publishes MQTT payload → topic: telemetry/{facility_id}/{device_id}/{metric}
    ▼
Eclipse Mosquitto (MQTT Broker)
    │  fan-out to subscribers
    ▼
FastAPI MQTT Subscriber (server/src/workers/simulator.py)
    │  1. validates payload against Pydantic schema
    │  2. writes row to database storage via repository layer
    │  3. distributes live updates to connected clients
    ▼
TimescaleDB Hypertable (telemetry_logs)          WebSocketManager (server/src/services/websocket_manager.py)
    │  durable, compressed, queryable history          │  broadcasts to all sockets subscribed to facility_id room
    ▼                                                   ▼
REST endpoints (historical / aggregated queries)   WebSocket `/ws/{facility_id}`
    │                                                   │
    └──────────────────┬────────────────────────────────┘
                        ▼
              Next.js Dashboard (client)
              - Server Components fetch initial history via REST (SSR)
              - Client Components subscribe to WebSocket for live deltas
              - UI actions push updates back through the API layer

Control-loop direction (operator tunes a setpoint):
Next.js client → FastAPI API → server-side service logic → worker or device simulation updates.
```


## 3. Database Schema

### `users`
```
| column       | type        | notes                              |
|--------------|-------------|-------------------------------------|
| id           | UUID PK     |                                     |
| email        | text UNIQUE |                                     |
| hashed_password | text     |                                     |
| role         | enum        | plant_operator, facility_admin, compliance_auditor |
| facility_id  | UUID FK → facilities.id (nullable) | scoping for operators/auditors |
| created_at   | timestamptz |                                     |
```
### `facilities`
```
| column       | type        | notes                              |
|--------------|-------------|-------------------------------------|
| id           | UUID PK     |                                     |
| name         | text        |                                     |
| location     | text        |                                     |
| timezone     | text        |                                     |
| created_at   | timestamptz |                                     |
```
### `devices`
```
| column       | type        | notes                              |
|--------------|-------------|-------------------------------------|
| id           | UUID PK     |                                     |
| facility_id  | UUID FK → facilities.id |                        |
| name         | text        |                                     |
| device_type  | enum        | ph_sensor, turbidity_sensor, dosing_pump, flow_meter |
| ph_setpoint  | float       | current PID target, cached in Redis too |
| is_online    | boolean     |                                     |
| created_at   | timestamptz |                                     |
```
### `telemetry_logs` (TimescaleDB hypertable)
```
| column       | type        | notes                              |
|--------------|-------------|-------------------------------------|
| timestamp    | timestamptz | **hypertable partition column**    |
| device_id    | UUID FK → devices.id |                            |
| metric_type  | enum        | ph, turbidity_ntu, chlorine_dose_ml, flow_rate |
| metric_value | double precision |                                |
```
Composite index on `(device_id, timestamp DESC)`; hypertable chunk interval of 1 day is a
reasonable default for high-frequency telemetry (see `database.py`).