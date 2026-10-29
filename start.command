#!/bin/bash
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt
set -a
source .env
set +a
python3 -m uvicorn server:app --host 127.0.0.1 --port 8765
