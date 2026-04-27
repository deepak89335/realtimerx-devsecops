#!/usr/bin/env bash
LOG_FILE="$(dirname "$0")/monitoring.log"
CONTAINER="realtimerx_app"
APP_PORT="5000"

collect() {
    TS=$(date "+%Y-%m-%d %H:%M:%S")
    CPU=$(docker stats "$CONTAINER" --no-stream --format "{{.CPUPerc}}" 2>/dev/null || echo "N/A")
    HTTP_404s=$(docker logs "$CONTAINER" --since=60s 2>&1 | grep -c " 404 " || echo 0)
    JSON=$(curl -sf "http://localhost:$APP_PORT/api/alerts/low-stock" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$JSON" ]; then
        LOW_STOCK=$(echo "$JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('count',len(d)))" 2>/dev/null || echo 0)
    else
        LOW_STOCK=0
    fi
    RESTARTS=$(docker inspect "$CONTAINER" --format="{{.RestartCount}}" 2>/dev/null || echo 0)
    LINE="[$TS] CPU=$CPU HTTP_404s=$HTTP_404s LOW_STOCK_ALERTS=$LOW_STOCK RESTARTS=$RESTARTS"
    if [ "$RESTARTS" -gt 0 ] 2>/dev/null; then
        LINE="$LINE  <- RESTART DETECTED"
    fi
    echo "$LINE" | tee -a "$LOG_FILE"
}

echo "RealTimeRx monitor started. Logging to: $LOG_FILE"
while true; do
    collect
    sleep 60
done
