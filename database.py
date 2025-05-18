import sqlite3
import pytz
from datetime import datetime, timedelta
from config import DB_NAME, TIMEZONE

def init_db():
    """Инициализация базы данных и создание необходимых таблиц"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Таблица общежитий
    c.execute('''CREATE TABLE IF NOT EXISTS dormitories
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT UNIQUE NOT NULL)''')

    # Таблица этажей
    c.execute('''CREATE TABLE IF NOT EXISTS floors
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 dorm_id INTEGER NOT NULL,
                 floor_number INTEGER NOT NULL,
                 FOREIGN KEY (dorm_id) REFERENCES dormitories(id),
                 UNIQUE(dorm_id, floor_number))''')

    # Таблица блоков
    c.execute('''CREATE TABLE IF NOT EXISTS blocks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 floor_id INTEGER NOT NULL,
                 block_number TEXT NOT NULL,
                 password TEXT,
                 FOREIGN KEY (floor_id) REFERENCES floors(id),
                 UNIQUE(floor_id, block_number))''')

    # Таблица комнат
    c.execute('''CREATE TABLE IF NOT EXISTS rooms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 block_id INTEGER NOT NULL,
                 room_number INTEGER NOT NULL,
                 FOREIGN KEY (block_id) REFERENCES blocks(id),
                 UNIQUE(block_id, room_number))''')

    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                 username TEXT,
                 room_id INTEGER,
                 role TEXT DEFAULT 'student',
                 FOREIGN KEY (room_id) REFERENCES rooms(id))''')

    # Таблица дежурств
    c.execute('''CREATE TABLE IF NOT EXISTS duties
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 date TEXT,
                 room_id INTEGER,
                 completed BOOLEAN DEFAULT FALSE,
                 FOREIGN KEY (room_id) REFERENCES rooms(id))''')

    # Таблица уведомлений
    c.execute('''CREATE TABLE IF NOT EXISTS notifications
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 type TEXT,
                 message TEXT,
                 sent_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY (user_id) REFERENCES users(user_id))''')

    # Таблица настроек
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (key TEXT PRIMARY KEY,
                 value TEXT)''')

    conn.commit()
    conn.close()

def get_setting(key: str) -> str or None:
    """Получение значения настройки по ключу"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def save_setting(key: str, value: str):
    """Сохранение значения настройки"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def get_notification_settings():
    """Получение всех ОБЩИХ настроек уведомлений из БД (используется как fallback)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT key, value FROM settings WHERE key IN (?, ?, ?, ?)',
              ('preview_time', 'duty_time', 'preview_text', 'duty_text'))
    settings_data = c.fetchall()
    conn.close()

    settings = {}
    for key, value in settings_data:
        settings[key] = value
    return settings

def get_block_notification_settings(block_id: int) -> dict:
    """Получение настроек уведомлений для конкретного блока"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    keys_to_fetch = [
        f'block_{block_id}_preview_time',
        f'block_{block_id}_duty_time',
        f'block_{block_id}_preview_text',
        f'block_{block_id}_duty_text'
    ]
    # Используем плейсхолдеры для безопасности
    placeholders = ','.join('?' for _ in keys_to_fetch)
    query = f'SELECT key, value FROM settings WHERE key IN ({placeholders})'
    c.execute(query, keys_to_fetch)
    settings_data = c.fetchall()
    conn.close()

    settings = {}
    # Убираем префикс block_id_ из ключей для удобства использования
    prefix = f'block_{block_id}_'
    for key, value in settings_data:
        if key.startswith(prefix):
            settings[key[len(prefix):]] = value
    return settings

def save_block_notification_setting(block_id: int, key: str, value: str):
    """Сохранение настройки уведомления для конкретного блока"""
    full_key = f'block_{block_id}_{key}'
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (full_key, value))
    conn.commit()
    conn.close()


def save_notification(user_id: int, notification_type: str, message: str):
    """Сохраняет отправленное уведомление в базу"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO notifications (user_id, type, message) VALUES (?, ?, ?)',
              (user_id, notification_type, message))
    conn.commit()
    conn.close()

# Функции для работы с общежитиями
def add_dormitory(name: str) -> int:
    """Добавляет новое общежитие и возвращает его id"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO dormitories (name) VALUES (?)', (name,))
    dorm_id = c.lastrowid if c.lastrowid else get_dormitory_id(name)
    conn.commit()
    conn.close()
    return dorm_id

def get_dormitory_id(name: str) -> int:
    """Получает id общежития по названию"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id FROM dormitories WHERE name = ?', (name,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_all_dormitories():
    """Получает список всех общежитий"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, name FROM dormitories')
    dormitories = c.fetchall()
    conn.close()
    return dormitories

# Функции для работы с этажами
def add_floor(dorm_id: int, floor_number: int) -> int:
    """Добавляет новый этаж и возвращает его id"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO floors (dorm_id, floor_number) VALUES (?, ?)',
              (dorm_id, floor_number))
    floor_id = c.lastrowid if c.lastrowid else get_floor_id(dorm_id, floor_number)
    conn.commit()
    conn.close()
    return floor_id

def get_floor_id(dorm_id: int, floor_number: int) -> int:
    """Получает id этажа по id общежития и номеру этажа"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id FROM floors WHERE dorm_id = ? AND floor_number = ?',
              (dorm_id, floor_number))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_floors_by_dorm(dorm_id: int):
    """Получает список всех этажей в общежитии"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, floor_number FROM floors WHERE dorm_id = ? ORDER BY floor_number',
              (dorm_id,))
    floors = c.fetchall()
    conn.close()
    return floors

# Функции для работы с блоками
def add_block(floor_id: int, block_number: str, password: str = None) -> int:
    """Добавляет новый блок и возвращает его id"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO blocks (floor_id, block_number, password) VALUES (?, ?, ?)',
              (floor_id, block_number, password))
    block_id = c.lastrowid if c.lastrowid else get_block_id(floor_id, block_number)
    conn.commit()
    conn.close()
    return block_id

def update_block_password(block_id: int, password: str):
    """Обновляет пароль для блока"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE blocks SET password = ? WHERE id = ?', (password, block_id))
    conn.commit()
    conn.close()

def get_block_id(floor_id: int, block_number: str) -> int:
    """Получает id блока по id этажа и номеру блока"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id FROM blocks WHERE floor_id = ? AND block_number = ?',
              (floor_id, block_number))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_blocks_by_floor(floor_id: int):
    """Получает список всех блоков на этаже"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, block_number FROM blocks WHERE floor_id = ?', (floor_id,))
    blocks = c.fetchall()
    conn.close()
    return blocks

def get_block_password(block_id: int) -> str:
    """Получает пароль блока по id"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT password FROM blocks WHERE id = ?', (block_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def is_password_used(password: str) -> bool:
    """Проверяет, используется ли уже такой пароль в других блоках"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM blocks WHERE password = ?', (password,))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

def get_duty_details(duty_id: int) -> tuple:
    """Получает информацию о дежурстве по его ID"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        'SELECT date FROM duties WHERE id = ?',
        (duty_id,)
    )
    result = c.fetchone()
    conn.close()
    return result

def get_duty_room(duty_id: int) -> int:
    """Получает ID комнаты, назначенной на дежурство"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT room_id FROM duties WHERE id = ?', (duty_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def validate_block_password(block_id: int, password: str) -> bool:
    """Проверяет пароль блока"""
    stored_password = get_block_password(block_id)
    return stored_password == password

# Функции для работы с комнатами
def add_room(block_id: int, room_number: int) -> int:
    """Добавляет новую комнату и возвращает её id"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO rooms (block_id, room_number) VALUES (?, ?)',
              (block_id, room_number))
    room_id = c.lastrowid if c.lastrowid else get_room_id(block_id, room_number)
    conn.commit()
    conn.close()
    return room_id

def get_room_id(block_id: int, room_number: int) -> int:
    """Получает id комнаты по id блока и номеру комнаты"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id FROM rooms WHERE block_id = ? AND room_number = ?',
              (block_id, room_number))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_rooms_by_block(block_id: int):
    """Получает список всех комнат в блоке"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, room_number FROM rooms WHERE block_id = ? ORDER BY room_number',
              (block_id,))
    rooms = c.fetchall()
    conn.close()
    return rooms

def delete_rooms_in_block(block_id: int):
    """Удаляет все комнаты в блоке"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Сначала получаем ID всех комнат в блоке
    c.execute('SELECT id FROM rooms WHERE block_id = ?', (block_id,))
    room_ids = [row[0] for row in c.fetchall()]

    # Удаляем ссылки на эти комнаты в таблице пользователей
    for room_id in room_ids:
        c.execute('UPDATE users SET room_id = NULL WHERE room_id = ?', (room_id,))

    # Удаляем дежурства, связанные с этими комнатами
    for room_id in room_ids:
        c.execute('DELETE FROM duties WHERE room_id = ?', (room_id,))

    # Удаляем сами комнаты
    c.execute('DELETE FROM rooms WHERE block_id = ?', (block_id,))

    conn.commit()
    conn.close()

def delete_block(block_id: int):
    """Удаляет блок и все его комнаты"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Сначала удаляем все комнаты в блоке
    delete_rooms_in_block(block_id)

    # Затем удаляем сам блок
    c.execute('DELETE FROM blocks WHERE id = ?', (block_id,))

    conn.commit()
    conn.close()
    return True

def delete_floor(floor_id: int):
    """Удаляет этаж и все его блоки и комнаты"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Сначала получаем все блоки на этаже
    c.execute('SELECT id FROM blocks WHERE floor_id = ?', (floor_id,))
    block_ids = [row[0] for row in c.fetchall()]

    # Удаляем каждый блок
    for block_id in block_ids:
        delete_block(block_id)

    # Затем удаляем сам этаж
    c.execute('DELETE FROM floors WHERE id = ?', (floor_id,))

    conn.commit()
    conn.close()
    return True

def delete_dormitory(dorm_id: int):
    """Удаляет общежитие и все его этажи, блоки и комнаты"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Сначала получаем все этажи в общежитии
    c.execute('SELECT id FROM floors WHERE dorm_id = ?', (dorm_id,))
    floor_ids = [row[0] for row in c.fetchall()]

    # Удаляем каждый этаж
    for floor_id in floor_ids:
        delete_floor(floor_id)

    # Затем удаляем само общежитие
    c.execute('DELETE FROM dormitories WHERE id = ?', (dorm_id,))

    conn.commit()
    conn.close()
    return True

def get_room_details(room_id: int):
    """Получает полную информацию о комнате (номер, блок, этаж, общежитие)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT r.room_number, b.block_number, f.floor_number, d.name
        FROM rooms r
        JOIN blocks b ON r.block_id = b.id
        JOIN floors f ON b.floor_id = f.id
        JOIN dormitories d ON f.dorm_id = d.id
        WHERE r.id = ?
    ''', (room_id,))
    result = c.fetchone()
    conn.close()
    return result

# Функции для работы с пользователями
def add_user(user_id: int, username: str, room_id: int = None, role: str = 'student'):
    """Добавляет или обновляет пользователя"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if room_id:
        c.execute('INSERT OR REPLACE INTO users (user_id, username, room_id, role) VALUES (?, ?, ?, ?)',
                  (user_id, username, room_id, role))
    else:
        c.execute('INSERT OR REPLACE INTO users (user_id, username, role) VALUES (?, ?, ?)',
                  (user_id, username, role))
    conn.commit()
    conn.close()

def update_user_role(user_id: int, role: str):
    """Обновляет роль пользователя"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE users SET role = ? WHERE user_id = ?', (role, user_id))
    conn.commit()
    conn.close()

def update_user_room(user_id: int, room_id: int):
    """Обновляет комнату пользователя"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE users SET room_id = ? WHERE user_id = ?', (room_id, user_id))
    conn.commit()
    conn.close()
    return True # Добавим возвращаемое значение для проверки успеха

def get_user(user_id: int):
    """Получает информацию о пользователе"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT user_id, username, room_id, role FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result

def get_user_role(user_id: int) -> str:
    """Получает роль пользователя"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT role FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 'student'

def get_user_room_id(user_id: int) -> int:
    """Получает id комнаты пользователя"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT room_id FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_users_by_room(room_id: int):
    """Получает список пользователей в комнате"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT user_id, username FROM users WHERE room_id = ?', (room_id,))
    users = c.fetchall()
    conn.close()
    return users

def get_all_users():
    """Получает список всех пользователей"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT u.user_id, u.username, r.room_number, b.block_number, f.floor_number, d.name, u.role
        FROM users u
        LEFT JOIN rooms r ON u.room_id = r.id
        LEFT JOIN blocks b ON r.block_id = b.id
        LEFT JOIN floors f ON b.floor_id = f.id
        LEFT JOIN dormitories d ON f.dorm_id = d.id
        ORDER BY d.name, f.floor_number, b.block_number, r.room_number
    ''')
    users = c.fetchall()
    conn.close()
    return users

def delete_user(user_id: int):
    """Удаляет пользователя из системы"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# Функции для работы с дежурствами
def create_duty_schedule(start_room_id: int, days: int = 30):
    """Создает расписание дежурств на указанное количество дней для КОНКРЕТНОГО блока"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Получаем block_id из start_room_id
    c.execute('SELECT block_id FROM rooms WHERE id = ?', (start_room_id,))
    block_id_result = c.fetchone()
    if not block_id_result:
        conn.close()
        print(f"Error: Could not find block_id for start_room_id {start_room_id}")
        return False
    current_block_id = block_id_result[0]

    # Получаем все комнаты в КОНКРЕТНОМ блоке
    c.execute('''
        SELECT r.id, r.room_number
        FROM rooms r
        WHERE r.block_id = ?
        ORDER BY r.room_number
    ''', (current_block_id,))
    rooms_in_block = c.fetchall()

    if not rooms_in_block:
        conn.close()
        return False

    # Создаем циклический список комнат
    room_cycle = []
    start_index = 0

    for i, (room_id, room_number) in enumerate(rooms_in_block):
        if room_id == start_room_id:
            start_index = i
            break

    room_cycle = rooms_in_block[start_index:] + rooms_in_block[:start_index]

    # Создаем расписание
    current_date = datetime.now(pytz.timezone(TIMEZONE))
    schedule = []

    for i in range(days):
        room_index = i % len(room_cycle)
        room_id_for_duty = room_cycle[room_index][0] # Переименовал для ясности
        date_str = current_date.strftime('%Y-%m-%d')
        schedule.append((date_str, room_id_for_duty))
        current_date += timedelta(days=1)

    # Удаляем старые дежурства ТОЛЬКО для текущего блока
    c.execute('''
        DELETE FROM duties
        WHERE room_id IN (SELECT id FROM rooms WHERE block_id = ?)
    ''', (current_block_id,))

    # Сохраняем новое расписание
    c.executemany('INSERT INTO duties (date, room_id) VALUES (?, ?)', schedule)
    conn.commit()
    conn.close()
    return True


def get_block_schedule(block_id: int):
    """Получает расписание дежурств для блока"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT d.id, d.date, r.room_number, d.completed
        FROM duties d
        JOIN rooms r ON d.room_id = r.id
        WHERE r.block_id = ?
        ORDER BY d.date
    ''', (block_id,))
    schedule = c.fetchall()
    conn.close()
    return schedule

def get_user_duties(user_id: int):
    """Получает список предстоящих дежурств пользователя"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT d.date, d.completed
        FROM duties d
        JOIN users u ON d.room_id = u.room_id
        WHERE u.user_id = ? AND d.date >= ?
        ORDER BY d.date
    ''', (user_id, datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y-%m-%d')))
    duties = c.fetchall()
    conn.close()
    return duties

def update_duty_room(duty_id: int, new_room_id: int):
    """Изменяет комнату для конкретного дежурства"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE duties SET room_id = ? WHERE id = ?', (new_room_id, duty_id))
    conn.commit()
    conn.close()

def update_duty_status(duty_id: int, completed: bool = True):
    """Обновляет статус выполнения дежурства"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE duties SET completed = ? WHERE id = ?', (completed, duty_id))
    conn.commit()
    conn.close()

def get_duty_by_date_and_block(date: str, block_id: int):
    """Получает информацию о дежурстве по дате и блоку"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT d.id, d.room_id, r.room_number, d.completed
        FROM duties d
        JOIN rooms r ON d.room_id = r.id
        WHERE d.date = ? AND r.block_id = ?
    ''', (date, block_id))
    result = c.fetchone()
    conn.close()
    return result

def get_todays_duties():
    """Получает все дежурства на сегодня, включая block_id"""
    today = datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT d.id, d.room_id, r.room_number, b.block_number, f.floor_number, dr.name, d.completed, b.id as block_id
        FROM duties d
        JOIN rooms r ON d.room_id = r.id
        JOIN blocks b ON r.block_id = b.id
        JOIN floors f ON b.floor_id = f.id
        JOIN dormitories dr ON f.dorm_id = dr.id
        WHERE d.date = ?
    ''', (today,))
    duties = c.fetchall()
    conn.close()
    return duties

def get_tomorrows_duties():
    """Получает все дежурства на завтра, включая block_id"""
    tomorrow = (datetime.now(pytz.timezone(TIMEZONE)) + timedelta(days=1)).strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT d.id, d.room_id, r.room_number, b.block_number, f.floor_number, dr.name, d.completed, b.id as block_id
        FROM duties d
        JOIN rooms r ON d.room_id = r.id
        JOIN blocks b ON r.block_id = b.id
        JOIN floors f ON b.floor_id = f.id
        JOIN dormitories dr ON f.dorm_id = dr.id
        WHERE d.date = ?
    ''', (tomorrow,))
    duties = c.fetchall()
    conn.close()
    return duties


def get_block_elders(block_id: int):
    """Получает информацию о старостах блока"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Получаем информацию о старостах блока по их роли и активности
    c.execute('''
        SELECT u.user_id, u.username, MAX(n.sent_time) as last_login
        FROM users u
        LEFT JOIN notifications n ON u.user_id = n.user_id AND n.type = 'elder_login'
        WHERE u.role = 'elder'
        GROUP BY u.user_id, u.username
        ORDER BY last_login DESC
    ''')

    users = c.fetchall()
    conn.close()

    # Форматируем данные для удобного использования
    elder_info = []
    for user_id, username, last_login in users:
        # Форматируем время последнего входа
        if last_login:
            try:
                login_dt = datetime.strptime(last_login, '%Y-%m-%d %H:%M:%S.%f') # Учтем микросекунды, если они есть
                formatted_time = login_dt.strftime('%d.%m.%Y %H:%M')
            except ValueError: # Если формат другой (без микросекунд)
                try:
                    login_dt = datetime.strptime(last_login, '%Y-%m-%d %H:%M:%S')
                    formatted_time = login_dt.strftime('%d.%m.%Y %H:%M')
                except:
                    formatted_time = 'неизвестно'
        else:
            formatted_time = 'никогда'

        elder_info.append({
            'user_id': user_id,
            'username': username or f'Пользователь {user_id}',
            'last_login': formatted_time
        })

    return elder_info