#!/bin/bash
# Скрипт запуска/перезапуска бота

cd /home/borodachdev/apps/borodach-franchise-bot

# Останавливаем старый процесс если есть
if [ -f bot.pid ]; then
    OLD_PID=$(cat bot.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "Stopping old bot process (PID: $OLD_PID)..."
        kill $OLD_PID
        sleep 2
    fi
    rm -f bot.pid
fi

# Активируем виртуальное окружение
source venv/bin/activate

# Запускаем бота в фоне
echo "Starting bot..."
nohup python main.py > logs/bot.log 2>&1 &

# Сохраняем PID
echo $! > bot.pid
echo "Bot started with PID: $(cat bot.pid)"

