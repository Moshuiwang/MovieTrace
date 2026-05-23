#!/usr/bin/env bash
set -u

MAX_AGE=${1:-20}
HB_FILE="$(dirname "$0")/../data/pipeline_heartbeat.json"

if [[ ! -f "$HB_FILE" ]]; then
    echo "WARN: heartbeat file not found (pipeline never ran?)"
    exit 0
fi

STATUS=$(python3 -c "import json; print(json.load(open('$HB_FILE')).get('status',''))")
if [[ "$STATUS" == "done" ]]; then
    echo "OK: pipeline status=done"
    exit 0
fi

TS=$(python3 -c "import json; print(json.load(open('$HB_FILE')).get('ts',''))")
AGE_SEC=$(python3 -c "
from datetime import datetime,timezone,timedelta
ts=datetime.fromisoformat('$TS')
now=datetime.now(timezone(timedelta(hours=8)))
print(int((now-ts).total_seconds()))
")
STEP=$(python3 -c "import json; print(json.load(open('$HB_FILE')).get('step','?'))")

if [[ "$AGE_SEC" -gt $((MAX_AGE * 60)) ]]; then
    echo "ALERT: heartbeat stale ${AGE_SEC}s (>${MAX_AGE}min), last step: $STEP"
    exit 1
fi

DETAIL=$(python3 -c "import json; print(json.load(open('$HB_FILE')).get('detail',''))")
echo "OK: age=${AGE_SEC}s step=$STEP detail=$DETAIL"
exit 0
