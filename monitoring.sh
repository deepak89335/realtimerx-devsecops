#!/usr/bin/env bash

LOG_FILE="$(dirname "$0")/monitoring.log"
CONTAINER="realtimerx_app"
APP_PORT="5000"

PREV_RESTARTS=0

collect() {

    TS=$(date "+%Y-%m-%d %H:%M:%S")

    CPU=$(docker stats "$CONTAINER" --no-stream --format "{{.CPUPerc}}" 2>/dev/null || echo "N/A")

    HTTP_404S=$(curl -s -o /dev/null -w "%{http_code}" \
        "http://localhost:$APP_PORT/api/drugs/bad_id")

    if [ "$HTTP_404S" = "404" ]; then
        HTTP_404S=1
    else
        HTTP_404S=0
    fi

    JSON=$(curl -s "http://localhost:$APP_PORT/api/alerts/low-stock")

    if [ -n "$JSON" ]; then
        LOW_STOCK=$(echo "$JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(len(data) if isinstance(data, list) else data.get('count', 0))
" 2>/dev/null)
    else
        LOW_STOCK=0
    fi

    RESTARTS=$(docker inspect "$CONTAINER" \
        --format='{{.RestartCount}}' 2>/dev/null || echo 0)

    LINE="[$TS] CPU=$CPU HTTP_404s=$HTTP_404S LOW_STOCK_ALERTS=$LOW_STOCK RESTARTS=$RESTARTS"

    if [ "$RESTARTS" -gt "$PREV_RESTARTS" ] 2>/dev/null; then
        LINE="$LINE <-- RESTART DETECTED"
    fi

    echo "$LINE" | tee -a "$LOG_FILE"

    PREV_RESTARTS=$RESTARTS
}

echo "RealTimeRx monitoring started..."

while true
do
    collect
    sleep 60
done
