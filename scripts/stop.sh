#!/bin/bash
# Скрипт остановки бота

cd /home/borodachdev/apps/borodach-franchise-bot

if [ -f bot.pid ]; then
    PID=$(cat bot.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "Stopping bot (PID: $PID)..."
        kill $PID
        rm -f bot.pid
        echo "Bot stopped."
    else
        echo "Bot process not running."
        rm -f bot.pid
    fi
else
    echo "No PID file found."
fi




