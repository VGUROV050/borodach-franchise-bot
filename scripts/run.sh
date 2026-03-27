#!/bin/bash
# Скрипт запуска/перезапуска бота и мобильного API

cd /home/borodachdev/apps/borodach-franchise-bot

# --- Останавливаем старые процессы ---

if [ -f bot.pid ]; then
    OLD_PID=$(cat bot.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "Stopping old bot process (PID: $OLD_PID)..."
        kill $OLD_PID
        sleep 2
    fi
    rm -f bot.pid
fi

if [ -f mobile_api.pid ]; then
    OLD_PID=$(cat mobile_api.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "Stopping old mobile API process (PID: $OLD_PID)..."
        kill $OLD_PID
        sleep 2
    fi
    rm -f mobile_api.pid
fi

# --- Активируем виртуальное окружение ---
source venv/bin/activate

# --- Миграции ---
echo "Running database migrations..."
alembic upgrade head
if [ $? -ne 0 ]; then
    echo "ERROR: Migration failed!"
    exit 1
fi
echo "Migrations complete."

# --- Запускаем бота ---
echo "Starting bot..."
nohup python main.py > logs/bot.log 2>&1 &
echo $! > bot.pid
echo "Bot started with PID: $(cat bot.pid)"

# --- Запускаем мобильное API ---
echo "Starting mobile API..."
nohup python run_mobile_api.py > logs/mobile_api.log 2>&1 &
echo $! > mobile_api.pid
echo "Mobile API started with PID: $(cat mobile_api.pid)"




