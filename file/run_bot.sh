#!/bin/bash

# Директория с проектом
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $PROJECT_DIR

# Проверка, запущен ли уже бот
PID_FILE="$PROJECT_DIR/bot.pid"
LOG_FILE="$PROJECT_DIR/bot.log"

# Функция для запуска бота
start_bot() {
    echo "$(date): Запуск бота..." >> $LOG_FILE
    # Проверяем доступные пути к Python
    PYTHON_PATH=""
    for path in "/usr/bin/python3" "/usr/bin/python" "/opt/alt/python311/bin/python3" "/usr/local/bin/python3"; do
        if [ -f "$path" ]; then
            PYTHON_PATH="$path"
            break
        fi
    done
    
    if [ -z "$PYTHON_PATH" ]; then
        echo "$(date): Не найден интерпретатор Python!" >> $LOG_FILE
        exit 1
    fi
    
    echo "$(date): Используем Python: $PYTHON_PATH" >> $LOG_FILE
    $PYTHON_PATH "$PROJECT_DIR/main.py" >> $LOG_FILE 2>&1 &
    echo $! > $PID_FILE
    echo "$(date): Бот запущен с PID $(cat $PID_FILE)" >> $LOG_FILE
}

# Проверяем, есть ли файл с PID
if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    
    # Проверяем, работает ли процесс
    if ps -p $PID > /dev/null; then
        echo "$(date): Бот уже запущен с PID $PID" >> $LOG_FILE
        exit 0
    else
        echo "$(date): Процесс с PID $PID не найден, перезапуск..." >> $LOG_FILE
        rm $PID_FILE
        start_bot
    fi
else
    # Если PID файла нет, запускаем бота
    start_bot
fi
