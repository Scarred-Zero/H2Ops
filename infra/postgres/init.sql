-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create a dedicated schema for our telemetry if needed (optional, but good practice)
CREATE SCHEMA IF NOT EXISTS h2ops;