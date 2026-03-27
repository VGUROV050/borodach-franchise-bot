#!/bin/bash
# Скрипт остановки бота и мобильного API

cd /home/borodachdev/apps/borodach-franchise-bot

for SERVICE in bot mobile_api; do
    PIDFILE="${SERVICE}.pid"
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Stopping $SERVICE (PID: $PID)..."
            kill $PID
            echo "$SERVICE stopped."
        else
            echo "$SERVICE process not running."
        fi
        rm -f "$PIDFILE"
    else
        echo "No PID file for $SERVICE."
    fi
done




