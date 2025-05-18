import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import TOKEN, ADMIN_PASSWORD, MANAGER_PASSWORD
from database import init_db
from keyboards import *
from notifications import setup_notification_scheduler
import handlers.student as student_handlers
import handlers.elder as elder_handlers
import handlers.manager as manager_handlers
import handlers.admin as admin_handlers

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start - начало работы с ботом"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Загружаем необходимые функции из базы данных
    from database import get_user_room_id, get_room_details, get_user_duties, add_user
    from datetime import datetime
    
    # Загружаем только данные о комнате из базы данных
    room_id = get_user_room_id(user_id)
    
    # Если пользователя нет в БД, добавляем его
    if not room_id and username:
        add_user(user_id, username)
    
    # Обновляем флаг наличия комнаты в контексте на основе данных из БД
    context.user_data['has_room'] = room_id is not None
    
    # Роль пользователя берем только из контекста
    user_role = context.user_data.get('role', 'student')
    has_room = context.user_data.get('has_room', False)
    
    # Начало сообщения
    message = f"👋 Добро пожаловать, {username}!\n\n"
    
    # Добавляем информацию о выбранной комнате и ближайших дежурствах
    if has_room and user_role in ['student', 'elder']:
        room_id = get_user_room_id(user_id)
        if room_id:
            room_details = get_room_details(room_id)
            if room_details:
                room_number, block_number, floor_number, dorm_name = room_details
                message += f"🏠 Ваша комната: {room_number} (Блок {block_number}, Этаж {floor_number}, {dorm_name})\n\n"
                
                # Получаем ближайшие дежурства
                duties = get_user_duties(user_id)
                if duties:
                    # Проверяем, есть ли дежурства на сегодня
                    today = datetime.now().strftime('%Y-%m-%d')
                    today_duty = next(((date, completed) for date, completed in duties if date == today), None)
                    
                    if today_duty:
                        date, completed = today_duty
                        status = "✅ Выполнено" if completed else "🔥 Сегодня ваше дежурство!"
                        message += f"🗓️ {status}\n\n"
                    else:
                        # Находим ближайшее дежурство
                        next_duty = duties[0] if len(duties) > 0 else None
                        if next_duty:
                            date, completed = next_duty
                            try:
                                date_obj = datetime.strptime(date, '%Y-%m-%d')
                                formatted_date = date_obj.strftime('%d.%m.%Y')
                            except:
                                formatted_date = date
                            message += f"🗓️ Ближайшее дежурство: {formatted_date}\n\n"
                else:
                    message += "🗓️ У вас пока нет запланированных дежурств.\n\n"
    
    # Добавляем общую информацию о боте
    message += "Этот бот поможет организовать дежурства в общежитии.\n\n"
    
    # Если пользователь староста - загружаем информацию о блоке
    if user_role == 'elder' and 'elder_block_id' not in context.user_data:
        from database import get_blocks_by_floor, get_floors_by_dorm, get_all_dormitories
        
        # Пытаемся найти блок старосты по комнате
        if room_id:
            room_details = get_room_details(room_id)
            if room_details:
                # В room_details возвращается room_number, block_number, floor_number, dorm_name
                # Нам нужно получить ID блока
                from sqlite3 import connect
                from config import DB_NAME
                conn = connect(DB_NAME)
                c = conn.cursor()
                
                c.execute('''
                    SELECT b.id
                    FROM rooms r
                    JOIN blocks b ON r.block_id = b.id
                    WHERE r.id = ?
                ''', (room_id,))
                
                block_result = c.fetchone()
                conn.close()
                
                if block_result:
                    context.user_data['elder_block_id'] = block_result[0]
    
    # Информация о текущей роли
    if user_role == 'student':
        message += "🔹 Вы можете выбрать свою комнату и получать уведомления о дежурствах\n"
    elif user_role == 'elder':
        message += "🔹 Вы вошли как староста и можете управлять дежурствами в вашем блоке\n"
    elif user_role == 'manager':
        message += "🔹 Вы вошли как заведующий и можете управлять общежитиями\n"
    elif user_role == 'admin':
        message += "🔹 Вы вошли как администратор и имеете полный доступ к системе\n"
    
    # Получаем подходящую клавиатуру в зависимости от роли пользователя
    reply_markup = get_main_menu(user_role, has_room)
    
    # Определяем, какой тип запроса - обычное сообщение или callback query
    if update.callback_query:
        # Если это нажатие на кнопку
        try:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
        except Exception as e:
            # Обрабатываем ошибку BadRequest, когда сообщение не изменяется
            if "Message is not modified" in str(e):
                # Ошибка проигнорирована: сообщение уже содержит нужную информацию
                pass
            else:
                # Другие ошибки пробрасываем дальше
                raise e
    elif update.message:
        # Если это обычное сообщение
        await update.message.reply_text(message, reply_markup=reply_markup)

# Обработчик нажатий на кнопки
async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех нажатий на кнопки"""
    query = update.callback_query
    await query.answer()  # Отвечаем на колбэк, чтобы убрать часы загрузки у кнопки
    
    callback_data = query.data
    user_role = context.user_data.get('role', 'student')
    
    # Общие действия для всех ролей
    if callback_data == "back_to_main":
        await start(update, context)
        return
    
    # Действия входа в различные роли
    if callback_data == "login_elder":
        await elder_handlers.request_elder_password(update, context)
        return
    elif callback_data == "login_manager":
        await manager_handlers.request_manager_password(update, context)
        return
    elif callback_data == "login_admin":
        await admin_handlers.request_admin_password(update, context)
        return
    elif callback_data == "logout_role":
        context.user_data['role'] = 'student'
        await start(update, context)
        return
    
    # Перенаправляем обработку действий в зависимости от роли пользователя
    if user_role == 'student':
        await student_handlers.handle_student_buttons(update, context)
    elif user_role == 'elder':
        await elder_handlers.handle_elder_buttons(update, context)
    elif user_role == 'manager':
        await manager_handlers.handle_manager_buttons(update, context)
    elif user_role == 'admin':
        await admin_handlers.handle_admin_buttons(update, context)

# Обработчик текстовых сообщений
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех текстовых сообщений"""
    user_role = context.user_data.get('role', 'student')
    
    # Обработка ввода пароля
    if context.user_data.get('awaiting_elder_password'):
        await elder_handlers.handle_elder_password(update, context)
        return
    elif context.user_data.get('awaiting_manager_password'):
        await manager_handlers.handle_manager_password(update, context)
        return
    elif context.user_data.get('awaiting_admin_password'):
        await admin_handlers.handle_admin_password(update, context)
        return
    
    # Обработка других текстовых сообщений в зависимости от роли
    if user_role == 'student':
        await student_handlers.handle_student_text(update, context)
    elif user_role == 'elder':
        await elder_handlers.handle_elder_text(update, context)
    elif user_role == 'manager':
        await manager_handlers.handle_manager_text(update, context)
    elif user_role == 'admin':
        await admin_handlers.handle_admin_text(update, context)

def main():
    """Запуск бота"""
    # Инициализация базы данных
    init_db()
    logger.info("База данных инициализирована")
    
    # Создание экземпляра приложения
    application = Application.builder().token(TOKEN).build()
    
    # Установка планировщика уведомлений
    setup_notification_scheduler(application)
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Запуск бота
    logger.info("Бот запущен")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
