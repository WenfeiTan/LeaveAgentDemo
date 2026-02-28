#!/usr/bin/env bash
set -euo pipefail

PORT="${CHAINLIT_PORT:-8501}"
APP="/Users/wenfeitan/Desktop/vibecoding/LeaveAgentDemo/agent/chainlit_app.py"

exec chainlit run "$APP" -w --port "$PORT"
