#!/usr/bin/env bash
set -euo pipefail

PORT="${BACKEND_PORT:-8000}"
exec fastapi dev /Users/wenfeitan/Desktop/vibecoding/LeaveAgentDemo/be/main.py --port "$PORT"
