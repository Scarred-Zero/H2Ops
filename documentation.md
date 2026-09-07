# H2Ops — Architecture

## 1. Monorepo Directory Tree

H2Ops/
├── docker-compose.yml                       # container orchestration for app stack
├── documentation.md                         # architecture and project notes
├── README.md                                # project setup and usage
├── stuff.txt                                # local scratch/notes
├── client/                                  # Next.js frontend application
│   ├── AGENTS.md
│   ├── CLAUDE.md
│   ├── components.json
│   ├── Dockerfile
│   ├── eslint.config.mjs
│   ├── next-env.d.ts
│   ├── next.config.ts
│   ├── package.json
│   ├── postcss.config.mjs
│   ├── proxy.ts                             # API/proxy configuration
│   ├── README.md
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── app/
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   └── ui/
│   │       └── button.tsx
│   ├── lib/
│   │   ├── apiClient.ts
│   │   └── utils.ts
│   ├── public/
│   └── types/
│
├── server/                                  # FastAPI backend application
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── main.py
│   ├── pyproject.toml
│   ├── README.md
│   ├── alembic/
│   │   ├── README
│   │   ├── env.py
│   │   └── versions/
│   └── src/
│       ├── __init__.py
│       ├── api/
│       │   └── v1/
│       │       └── routes/
│       │           ├── __init__.py
│       │           ├── auth.py
│       │           ├── device.py
│       │           └── ws.py
│       ├── aws/
│       │   ├── client.py
│       │   ├── config.py
│       │   ├── constants.py
│       │   ├── exceptions.py
│       │   ├── schemas.py
│       │   └── utils.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── database.py
│       │   ├── exceptions.py
│       │   ├── metrics.py
│       │   └── security.py
│       ├── dependencies/
│       │   ├── __init__.py
│       │   └── auth.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── alert.py
│       │   ├── device.py
│       │   ├── facility.py
│       │   ├── role.py
│       │   ├── telemetry_log.py
│       │   └── user.py
│       ├── repositories/
│       │   ├── __init__.py
│       │   └── telemetry_repo.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   ├── device.py
│       │   ├── facility.py
│       │   ├── telemetry_log.py
│       │   └── user.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── telemetry_service.py
│       │   └── websocket_manager.py
│       ├── test/
│       │   ├── test_device_router.py
│       │   └── test_telemetry_repo.py
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── jwt_handler.py
│       │   ├── path_utils.py
│       │   └── redis_client.py
│       └── workers/
│           ├── __init__.py
│           └── simulator.py
│
├── infra/                                   # shared infrastructure bootstrap
│   ├── minio/
│   │   └── init-bucket.sh
│   └── postgres/
│       └── init.sql/
│
├── prometheus.yml                           # monitoring configuration
└── .env.example                             # environment variable template (if present in local setup)

> The application is organized into a client/server monorepo: the client contains the Next.js UI and the server contains the FastAPI API, worker logic, and data access layers.

## 2. Real-Time Data Flow

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

## 3. Database Schema

### `users`
| column       | type        | notes                              |
|--------------|-------------|-------------------------------------|
| id           | UUID PK     |                                     |
| email        | text UNIQUE |                                     |
| hashed_password | text     |                                     |
| role         | enum        | plant_operator, facility_admin, compliance_auditor |
| facility_id  | UUID FK → facilities.id (nullable) | scoping for operators/auditors |
| created_at   | timestamptz |                                     |

### `facilities`
| column       | type        | notes                              |
|--------------|-------------|-------------------------------------|
| id           | UUID PK     |                                     |
| name         | text        |                                     |
| location     | text        |                                     |
| timezone     | text        |                                     |
| created_at   | timestamptz |                                     |

### `devices`
| column       | type        | notes                              |
|--------------|-------------|-------------------------------------|
| id           | UUID PK     |                                     |
| facility_id  | UUID FK → facilities.id |                        |
| name         | text        |                                     |
| device_type  | enum        | ph_sensor, turbidity_sensor, dosing_pump, flow_meter |
| ph_setpoint  | float       | current PID target, cached in Redis too |
| is_online    | boolean     |                                     |
| created_at   | timestamptz |                                     |

### `telemetry_logs` (TimescaleDB hypertable)
| column       | type        | notes                              |
|--------------|-------------|-------------------------------------|
| timestamp    | timestamptz | **hypertable partition column**    |
| device_id    | UUID FK → devices.id |                            |
| metric_type  | enum        | ph, turbidity_ntu, chlorine_dose_ml, flow_rate |
| metric_value | double precision |                                |

Composite index on `(device_id, timestamp DESC)`; hypertable chunk interval of 1 day is a
reasonable default for high-frequency telemetry (see `database.py`).