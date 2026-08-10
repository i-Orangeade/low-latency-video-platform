#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${PROJECT_ROOT}"

echo "Starting ZLMediaKit, backend, and frontend..."
docker compose --profile app up -d --build

echo "ZLM HTTP API: http://127.0.0.1:8080/index/api/getServerConfig"
echo "Backend API:  http://127.0.0.1:8000/api/health"
echo "Frontend:     http://127.0.0.1:5173"
