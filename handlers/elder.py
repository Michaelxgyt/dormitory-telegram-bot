from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import (
    get_block_password,
    update_user_role,
    get_user_role,
    get_user_room_id,
    get_room_details,
    get_rooms_by_block,
    get_block_schedule,
    create_duty_schedule,
    update_duty_room,
    update_duty_status,
    get_block_notification_settings, # Изменено
    save_block_notification_setting, # Изменено
    get_users_by_room,
    add_room,
    get_room_id, # Был get_room_id, предполагаю, что нужен
    delete_user,
    delete_rooms_in_block,
    get_duty_room # Добавлено для update_duty_assignment
)
from keyboards import (
    get_elder_panel,
    get_edit_duty_menu,
    get_select_room_for_duty_menu,
    get_schedule_menu,
    get_notification_settings_menu,
    get_back_button,
    get_residents_menu,
    get_resident_actions_menu,
    get_confirmation_menu
)
from config import DEFAULT_NOTIFICATION_SETTINGS # Импортируем дефолтные настройки

# Запрос пароля старосты
async def request_elder_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает пароль для входа в панель старосты"""
    query = update.callback_query

    # Устанавливаем флаг ожидания пароля
    context.user_data['awaiting_elder_password'] = True

    await query.edit_message_text(
        "🔐 Для входа в панель старосты введите пароль:",
        reply_markup=get_back_button()
    )

# Обработка введенного пароля старосты
async def handle_elder_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет введенный пароль старосты"""
    # Сбрасываем флаг ожидания пароля
    context.user_data['awaiting_elder_password'] = False

    user_id = update.effective_user.id
    entered_password = update.message.text

    # Удаляем сообщение с паролем для безопасности
    try:
        await update.message.delete()
    except Exception as e:
        # Ошибка может возникнуть, если сообщение слишком старое или нет прав на удаление
        print(f"Не удалось удалить сообщение с паролем: {str(e)}")
        pass  # Продолжаем работу, даже если не удалось удалить сообщение

    # Получаем список всех блоков и проверяем пароль для каждого
    from database import get_all_dormitories, get_floors_by_dorm, get_blocks_by_floor

    dormitories = get_all_dormitories()
    valid_block_id = None
    block_number_str = None # Переименовал для ясности

    # Проходим по всем общежитиям, этажам и блокам, чтобы найти совпадение пароля
    for dorm_id, _ in dormitories:
        floors = get_floors_by_dorm(dorm_id)
        for floor_id, _ in floors:
            blocks = get_blocks_by_floor(floor_id)
            for block_id_db, block_num_db in blocks: # Переименовал переменные цикла
                stored_password = get_block_password(block_id_db)
                if stored_password and entered_password == stored_password:
                    valid_block_id = block_id_db
                    block_number_str = block_num_db
                    context.user_data['elder_block_id'] = block_id_db
                    break
            if valid_block_id:
                break
        if valid_block_id:
            break

    if valid_block_id:
        # Пароль верный, устанавливаем роль 'elder'
        update_user_role(user_id, 'elder')
        context.user_data['role'] = 'elder'

        # Получаем данные о комнате, если она уже выбрана
        room_id_user = get_user_room_id(user_id) # Переименовал для ясности
        has_room = room_id_user is not None
        context.user_data['has_room'] = has_room

        # Формируем сообщение приветствия
        username = update.effective_user.username or update.effective_user.first_name

        # Получаем информацию о блоке старосты (общежитие, этаж)
        from sqlite3 import connect
        from config import DB_NAME
        conn = connect(DB_NAME)
        c = conn.cursor()

        c.execute('''
            SELECT f.floor_number, d.name
            FROM blocks b
            JOIN floors f ON b.floor_id = f.id
            JOIN dormitories d ON f.dorm_id = d.id
            WHERE b.id = ?
        ''', (valid_block_id,)) # Используем valid_block_id
        block_info = c.fetchone()
        conn.close()

        if block_info:
            floor_number, dorm_name = block_info
            message = f"✅ Вы успешно вошли как староста {dorm_name}, {floor_number} - этаж, {block_number_str} - блока \n\n"
        else:
            # Этот случай маловероятен, если блок найден, но на всякий случай
            message = f"✅ Вы успешно вошли как староста блока {block_number_str} \n\n"


        # Добавляем информацию о комнате, если она уже выбрана
        if has_room:
            room_details = get_room_details(room_id_user)
            if room_details:
                room_number_user, block_num_user, floor_number_user, dorm_name_user = room_details
                message += f"🏠 Ваша комната: {room_number_user} (Блок {block_num_user}, Этаж {floor_number_user}, {dorm_name_user})\n\n"

        message += "Выберите действие:"

        # Показываем главное меню с опциями студента и кнопкой панели старосты
        from keyboards import get_main_menu
        await update.message.reply_text(
            message,
            reply_markup=get_main_menu('elder', has_room)
        )
    else:
        # Пароль неверный
        await update.message.reply_text(
            "❌ Неверный пароль. Попробуйте снова или обратитесь к заведующему.",
            reply_markup=get_back_button()
        )

# Обработчик кнопок старосты
async def handle_elder_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки для роли старосты"""
    query = update.callback_query
    callback_data = query.data

    # Проверяем, что пользователь действительно имеет роль старосты
    user_id = update.effective_user.id
    if get_user_role(user_id) != 'elder' and context.user_data.get('role') != 'elder':
        await query.edit_message_text(
            "У вас нет прав для доступа к панели старосты.",
            reply_markup=get_back_button()
        )
        return

    # Получаем блок старосты из контекста
    # elder_block_id должен быть установлен при входе по паролю
    current_elder_block_id = context.user_data.get('elder_block_id')
    if not current_elder_block_id:
        # Попытка восстановить, если пропал (маловероятно, но для надежности)
        room_id_user = get_user_room_id(user_id)
        if room_id_user:
            # Получаем block_id из комнаты пользователя
            from sqlite3 import connect
            from config import DB_NAME
            conn = connect(DB_NAME)
            c = conn.cursor()
            c.execute('SELECT block_id FROM rooms WHERE id = ?', (room_id_user,))
            block_id_res = c.fetchone()
            conn.close()
            if block_id_res:
                current_elder_block_id = block_id_res[0]
                context.user_data['elder_block_id'] = current_elder_block_id
            else:
                await query.edit_message_text(
                    "Ошибка: не удалось определить ваш блок. Пожалуйста, войдите снова.",
                    reply_markup=get_back_button()
                )
                return
        else: # Если нет комнаты, то и блока не определить так
            await query.edit_message_text(
                "Ошибка: не удалось определить ваш блок. Пожалуйста, войдите снова или выберите комнату.",
                reply_markup=get_back_button()
            )
            return


    # Основные действия старосты
    if callback_data == "elder_panel" or callback_data == "back_to_panel":
        await show_elder_panel(update, context)
    elif callback_data == "auto_schedule":
        await select_start_room(update, context)
    elif callback_data.startswith("start_room_"):
        room_id_start = int(callback_data.split("_")[2]) # Переименовал
        await confirm_schedule_creation(update, context, room_id_start)
    elif callback_data.startswith("confirm_create_"):
        room_id_start_confirm = int(callback_data.split("_")[2]) # Переименовал
        await create_schedule(update, context, room_id_start_confirm)
    elif callback_data == "view_schedule":
        await show_schedule(update, context)
    elif callback_data.startswith("schedule_"):
        action = callback_data.split("_")[1]
        if action == "prev":
            context.user_data['schedule_page'] = max(0, context.user_data.get('schedule_page', 0) - 1)
        elif action == "next":
            context.user_data['schedule_page'] = context.user_data.get('schedule_page', 0) + 1
        await show_schedule(update, context)
    elif callback_data == "edit_duty":
        await select_duty_to_edit(update, context)

    # Действия студента (выбор комнаты и просмотр дежурств)
    elif callback_data == "select_room":
        # Импортируем функцию выбора комнаты из модуля student
        from handlers.student import select_dormitory
        await select_dormitory(update, context)
    elif callback_data == "my_duties":
        # Импортируем функцию просмотра дежурств из модуля student
        from handlers.student import show_my_duties
        await show_my_duties(update, context)
    # Обработка других команд для выбора комнаты
    elif callback_data.startswith("dorm_") or callback_data.startswith("floor_") or callback_data.startswith("block_") or \
         callback_data == "back_to_floors" or callback_data == "back_to_blocks" or callback_data == "select_dorm" or \
         callback_data.startswith("room_") or callback_data.startswith("confirm_room_"):
        # Импортируем обработчик кнопок студента
        from handlers.student import handle_student_buttons
        await handle_student_buttons(update, context)
    elif callback_data.startswith("edit_duty_"):
        if callback_data == "edit_duty_prev":
            context.user_data['edit_duty_page'] = max(0, context.user_data.get('edit_duty_page', 0) - 1)
            await select_duty_to_edit(update, context)
        elif callback_data == "edit_duty_next":
            context.user_data['edit_duty_page'] = context.user_data.get('edit_duty_page', 0) + 1
            await select_duty_to_edit(update, context)
        else:
            duty_id_edit = int(callback_data.split("_")[2]) # Переименовал
            await select_new_room_for_duty(update, context, duty_id_edit)
    elif callback_data.startswith("assign_duty_"):
        parts = callback_data.split("_")
        duty_id_assign = int(parts[2]) # Переименовал
        room_id_assign = int(parts[3]) # Переименовал
        await update_duty_assignment(update, context, duty_id_assign, room_id_assign)
    elif callback_data == "notification_settings":
        await show_notification_settings(update, context)
    elif callback_data == "change_preview_time":
        await request_preview_time(update, context)
    elif callback_data == "change_duty_time":
        await request_duty_time(update, context)
    elif callback_data == "change_preview_text":
        await request_preview_text(update, context)
    elif callback_data == "change_duty_text":
        await request_duty_text(update, context)
    elif callback_data == "list_residents":
        await list_block_residents(update, context)
    elif callback_data == "create_rooms":
        await request_room_range(update, context)
    # Пагинация для списка комнат
    elif callback_data.startswith("rooms_"):
        action = callback_data.split("_")[1]
        if action == "prev":
            context.user_data['rooms_page'] = max(0, context.user_data.get('rooms_page', 0) - 1)
        elif action == "next":
            context.user_data['rooms_page'] = context.user_data.get('rooms_page', 0) + 1
        await list_block_residents(update, context)

    # Отображение жителей выбранной комнаты
    elif callback_data.startswith("show_room_residents_"):
        await show_room_residents(update, context)

    # Пагинация для списка жителей (старая функциональность, может быть не нужна если всегда через комнаты)
    elif callback_data.startswith("residents_"): # Оставим на случай если где-то используется
        action = callback_data.split("_")[1]
        if action == "prev":
            context.user_data['residents_page'] = max(0, context.user_data.get('residents_page', 0) - 1)
        elif action == "next":
            context.user_data['residents_page'] = context.user_data.get('residents_page', 0) + 1
        await list_block_residents(update, context) # Перенаправляем на более общую функцию

    # Действия с жителями
    elif callback_data.startswith("manage_resident_"):
        resident_user_id = int(callback_data.split("_")[2]) # Переименовал
        await show_resident_actions(update, context, resident_user_id)
    elif callback_data == "change_resident_room": # Эта callback_data может быть неоднозначной без user_id
        await change_resident_room(update, context) # Функция должна брать user_id из context
    elif callback_data.startswith("set_resident_room_"):
        await set_resident_room(update, context)
    elif callback_data == "confirm_delete_resident": # Аналогично, user_id из context
        await confirm_delete_resident(update, context)
    elif callback_data.startswith("delete_resident_"): # Эта callback_data содержит user_id
        await delete_resident(update, context)

    # Старые функции удаления (могут быть удалены, если не используются)
    elif callback_data.startswith("remove_resident_"): # Используется в get_resident_actions_menu
        user_id_remove = int(callback_data.split("_")[2])
        await confirm_remove_resident(update, context, user_id_remove)
    elif callback_data.startswith("confirm_remove_"): # Используется в get_confirmation_menu
        # Этот обработчик может конфликтовать с другими confirm_remove_* если не уточнить 'action'
        # В admin.py тоже есть "confirm_remove_", нужно быть осторожнее или сделать их более уникальными
        # Пока что, если мы здесь, то это удаление жителя
        user_id_confirm_remove = int(callback_data.split("_")[2])
        await remove_resident(update, context, user_id_confirm_remove)
    elif callback_data == "cancel_action": # Используется в get_confirmation_menu
        # Нужно определить, куда отменять. Если это было удаление жителя, то на список жителей.
        # Если мы не знаем точно, лучше на панель старосты или список комнат.
        # В admin.py "cancel_action" ведет на show_users.
        # Сделаем возврат к списку жителей, если это было связано с ними.
        if context.user_data.get('resident_user_id'): # Если мы управляли жителем
             await list_block_residents(update, context)
        else: # Иначе на панель старосты
            await show_elder_panel(update, context)

# Обработчик текстовых сообщений старосты
async def handle_elder_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений для роли старосты"""
    user_id = update.effective_user.id
    current_elder_block_id = context.user_data.get('elder_block_id') # Получаем ID блока старосты

    # Проверяем, что пользователь действительно имеет роль старосты
    if get_user_role(user_id) != 'elder' and context.user_data.get('role') != 'elder':
        await update.message.reply_text(
            "У вас нет прав для доступа к панели старосты.",
            reply_markup=get_back_button()
        )
        return

    if not current_elder_block_id: # Проверка на наличие ID блока
        await update.message.reply_text(
            "Ошибка: не удалось определить ваш блок. Пожалуйста, войдите снова.",
            reply_markup=get_back_button()
        )
        return

    # Обработка ввода параметров уведомлений
    if context.user_data.get('awaiting_preview_time'):
        context.user_data['awaiting_preview_time'] = False
        preview_time = update.message.text
        save_block_notification_setting(current_elder_block_id, 'preview_time', preview_time)
        await update.message.reply_text(
            f"✅ Время предварительного уведомления для вашего блока изменено на {preview_time}.",
            reply_markup=get_elder_panel()
        )
    elif context.user_data.get('awaiting_duty_time'):
        context.user_data['awaiting_duty_time'] = False
        duty_time = update.message.text
        save_block_notification_setting(current_elder_block_id, 'duty_time', duty_time)
        await update.message.reply_text(
            f"✅ Время дежурного уведомления для вашего блока изменено на {duty_time}.",
            reply_markup=get_elder_panel()
        )
    elif context.user_data.get('awaiting_preview_text'):
        context.user_data['awaiting_preview_text'] = False
        preview_text = update.message.text
        save_block_notification_setting(current_elder_block_id, 'preview_text', preview_text)
        await update.message.reply_text(
            f"✅ Текст предварительного уведомления для вашего блока изменен.",
            reply_markup=get_elder_panel()
        )
    elif context.user_data.get('awaiting_duty_text'):
        context.user_data['awaiting_duty_text'] = False
        duty_text = update.message.text
        save_block_notification_setting(current_elder_block_id, 'duty_text', duty_text)
        await update.message.reply_text(
            f"✅ Текст дежурного уведомления для вашего блока изменен.",
            reply_markup=get_elder_panel()
        )
    elif context.user_data.get('awaiting_room_range'):
        context.user_data['awaiting_room_range'] = False
        await process_room_range(update, context)
    else:
        await update.message.reply_text(
            "Пожалуйста, используйте меню для навигации.",
            reply_markup=get_elder_panel()
        )

# Отображение панели старосты
async def show_elder_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает главную панель старосты"""
    query = update.callback_query
    await query.edit_message_text(
        "⚙️ Панель управления старосты\n\n"
        "Здесь вы можете управлять дежурствами в вашем блоке.",
        reply_markup=get_elder_panel()
    )

# Функции для автоматического создания расписания
async def select_start_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор комнаты, с которой начнется дежурство"""
    query = update.callback_query
    current_elder_block_id = context.user_data.get('elder_block_id')

    if not current_elder_block_id:
        await query.edit_message_text(
            "Не удалось определить ваш блок. Обратитесь к администратору.",
            reply_markup=get_back_button("elder_panel")
        )
        return

    # Получаем список комнат в блоке
    rooms = get_rooms_by_block(current_elder_block_id)

    if not rooms:
        await query.edit_message_text(
            "В вашем блоке пока нет комнат. Создайте их через меню 'Создать комнаты в блоке' или обратитесь к заведующему.",
            reply_markup=get_back_button("elder_panel")
        )
        return

    # Создаем клавиатуру с комнатами
    keyboard = []
    row = []

    for i, (room_id_db, room_number_db) in enumerate(rooms): # Переименовал переменные цикла
        row.append(InlineKeyboardButton(
            f"🛏️ {room_number_db}",
            callback_data=f"start_room_{room_id_db}"
        ))

        if len(row) == 2 or i == len(rooms) - 1:
            keyboard.append(row)
            row = []

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="elder_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "Выберите комнату, с которой начнется цикл дежурства:",
        reply_markup=reply_markup
    )

async def confirm_schedule_creation(update: Update, context: ContextTypes.DEFAULT_TYPE, start_room_id: int):
    """Подтверждение создания расписания дежурств"""
    query = update.callback_query

    # Получаем информацию о комнате
    room_details = get_room_details(start_room_id)

    if not room_details:
        await query.edit_message_text(
            "Не удалось получить информацию о комнате.",
            reply_markup=get_back_button("elder_panel")
        )
        return

    room_number, _, _, _ = room_details # block_number, floor_number, dorm_name не нужны здесь

    # Создаем клавиатуру для подтверждения
    keyboard = [
        [InlineKeyboardButton("✅ Создать расписание", callback_data=f"confirm_create_{start_room_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data="elder_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"Вы собираетесь создать расписание дежурств для вашего блока, начиная с комнаты {room_number}.\n\n"
        f"Дежурства будут назначены по порядку номеров комнат в вашем блоке, начиная с выбранной.\n\n"
        f"Внимание! Это действие перезапишет существующее расписание дежурств для вашего блока, если оно есть.\n\n"
        f"Продолжить?",
        reply_markup=reply_markup
    )

async def create_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE, start_room_id: int):
    """Создание расписания дежурств"""
    query = update.callback_query

    # Создаем расписание
    success = create_duty_schedule(start_room_id) # block_id не передаем, он определяется внутри

    if success:
        await query.edit_message_text(
            "✅ Расписание дежурств для вашего блока успешно создано!\n\n"
            "Теперь вы можете просмотреть его или внести изменения.",
            reply_markup=get_elder_panel()
        )
    else:
        await query.edit_message_text(
            "❌ Не удалось создать расписание. Убедитесь, что в вашем блоке есть комнаты, или попробуйте снова. Если проблема сохраняется, обратитесь к администратору.",
            reply_markup=get_elder_panel()
        )

# Функции для просмотра расписания
async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расписание дежурств блока"""
    query = update.callback_query
    current_elder_block_id = context.user_data.get('elder_block_id')

    if not current_elder_block_id:
        await query.edit_message_text(
            "Не удалось определить ваш блок. Обратитесь к администратору.",
            reply_markup=get_back_button("elder_panel")
        )
        return

    # Получаем информацию о блоке (для заголовка)
    # Это можно оптимизировать, сохранив имя блока в context.user_data при входе
    block_info_str = ""
    from sqlite3 import connect
    from config import DB_NAME
    conn = connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT b.block_number, f.floor_number, d.name
        FROM blocks b
        JOIN floors f ON b.floor_id = f.id
        JOIN dormitories d ON f.dorm_id = d.id
        WHERE b.id = ?
    ''', (current_elder_block_id,))
    res_block_info = c.fetchone()
    conn.close()
    if res_block_info:
        block_num, floor_num, dorm_name = res_block_info
        block_info_str = f" ({dorm_name}, этаж {floor_num}, блок {block_num})"


    # Получаем расписание дежурств для блока
    schedule = get_block_schedule(current_elder_block_id)

    if not schedule:
        await query.edit_message_text(
            f"🗓️ Управление дежурствами{block_info_str}\n\n"
            "Расписание дежурств пока не создано.\n\n"
            "Чтобы создать расписание, вернитесь в панель старосты и нажмите 'Автоматическое назначение дежурств'.",
            reply_markup=get_back_button("elder_panel")
        )
        return

    # Определяем статистику по расписанию
    total_duties = len(schedule)
    completed_duties = sum(1 for _, _, _, completed in schedule if completed)
    completion_rate = round(completed_duties / total_duties * 100) if total_duties > 0 else 0

    # Находим сегодняшнее дежурство
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    today_duty_info = next(((duty_id, date_str, room_num, completed_status) for duty_id, date_str, room_num, completed_status in schedule if date_str == today), None) # Переименовал

    # Определяем страницу
    page = context.user_data.get('schedule_page', 0)
    items_per_page = 7
    total_pages = (len(schedule) + items_per_page - 1) // items_per_page

    # Проверяем, что страница в допустимом диапазоне
    if page >= total_pages and total_pages > 0 : # Добавил проверку total_pages > 0
        page = total_pages -1
        context.user_data['schedule_page'] = page
    elif page < 0:
        page = 0
        context.user_data['schedule_page'] = page


    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(schedule))

    # Формируем заголовок с информацией о дежурствах
    message = f"🗓️ Управление дежурствами{block_info_str}\n\n"

    # Добавляем статистику
    message += f"📊 Статистика:\n"
    message += f"\u2022 Всего дежурств: {total_duties}\n"
    message += f"\u2022 Выполнено: {completed_duties} ({completion_rate}%)\n"

    # Добавляем инфо о сегодняшнем дежурстве
    if today_duty_info:
        _, _, room_number_today, completed_today = today_duty_info # duty_id, date не нужны здесь
        status_today = "✅ Выполнено" if completed_today else "🔥 Сегодня"
        message += f"\nСегодня дежурит: Комната {room_number_today} ({status_today})\n"

    message += "\nРасписание дежурств:\n"

    # Добавляем дежурства с форматированными датами
    for _, date_duty, room_number_duty, completed_duty in schedule[start_idx:end_idx]: # duty_id не нужен здесь
        try:
            # Преобразуем дату в более читабельный формат
            date_obj = datetime.strptime(date_duty, '%Y-%m-%d')
            weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            weekday = weekdays[date_obj.weekday()]
            formatted_date = f"{date_obj.strftime('%d.%m.%Y')} ({weekday})"
        except:
            formatted_date = date_duty

        # Добавляем иконки статуса
        if completed_duty:
            status_duty = "✅"
        else:
            # Проверяем, сегодняшнее ли это дежурство
            if date_duty == today:
                status_duty = "🔥"
            else:
                status_duty = "⏳"

        message += f"\u2022 {formatted_date}: Комната {room_number_duty} {status_duty}\n"

    if total_pages > 0 : # Показывать пагинацию только если есть страницы
        message += f"\nСтраница {page + 1} из {total_pages}\n\n"
    message += "ℹ️ Вы можете изменить расписание, вернувшись в панель старосты и нажав 'Изменить дежурство'."

    await query.edit_message_text(
        message,
        reply_markup=get_schedule_menu(page, total_pages)
    )

# Функции для редактирования дежурств
async def select_duty_to_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор дежурства для редактирования"""
    query = update.callback_query
    current_elder_block_id = context.user_data.get('elder_block_id')

    if not current_elder_block_id:
        await query.edit_message_text(
            "Не удалось определить ваш блок. Обратитесь к администратору.",
            reply_markup=get_back_button("elder_panel")
        )
        return

    # Получаем расписание дежурств для блока
    schedule = get_block_schedule(current_elder_block_id)

    if not schedule:
        await query.edit_message_text(
            "Расписание дежурств пока не создано.",
            reply_markup=get_back_button("elder_panel")
        )
        return

    # Сохраняем расписание в контексте (если оно нужно где-то еще, но вроде бы get_edit_duty_menu его просто отображает)
    # context.user_data['duty_schedule'] = schedule # Можно убрать, если не используется

    # Определяем страницу
    page = context.user_data.get('edit_duty_page', 0)
    items_per_page = 5 # Можно вынести в константы

    await query.edit_message_text(
        "Выберите дежурство для редактирования:",
        reply_markup=get_edit_duty_menu(schedule, page, items_per_page)
    )

async def select_new_room_for_duty(update: Update, context: ContextTypes.DEFAULT_TYPE, duty_id: int):
    """Выбор новой комнаты для дежурства"""
    query = update.callback_query
    current_elder_block_id = context.user_data.get('elder_block_id')

    if not current_elder_block_id:
        await query.edit_message_text(
            "Не удалось определить ваш блок. Обратитесь к администратору.",
            reply_markup=get_back_button("elder_panel")
        )
        return

    # Получаем список комнат в блоке
    rooms = get_rooms_by_block(current_elder_block_id)

    if not rooms:
        await query.edit_message_text(
            "В вашем блоке пока нет комнат. Обратитесь к администратору.",
            reply_markup=get_back_button("elder_panel")
        )
        return

    await query.edit_message_text(
        "Выберите новую комнату для дежурства:",
        reply_markup=get_select_room_for_duty_menu(rooms, duty_id)
    )

async def update_duty_assignment(update: Update, context: ContextTypes.DEFAULT_TYPE, duty_id: int, new_room_id: int): # room_id переименован в new_room_id
    """Обновляет назначение дежурства на новую комнату"""
    query = update.callback_query

    # Получаем текущую комнату для дежурства до обновления
    old_room_id = get_duty_room(duty_id)

    # Обновляем комнату для дежурства
    update_duty_room(duty_id, new_room_id)

    # Получаем информацию о новой комнате
    room_details_new = get_room_details(new_room_id) # Переименовал

    if not room_details_new:
        await query.edit_message_text(
            "Дежурство переназначено, но не удалось получить информацию о новой комнате.",
            reply_markup=get_back_button("elder_panel") # Или get_elder_panel()
        )
        return

    room_number_new, _, _, _ = room_details_new # block_number, floor_number, dorm_name не нужны здесь

    # Отправляем уведомления о смене дежурства
    from notifications import send_duty_change_notification
    await send_duty_change_notification(context.bot, duty_id, old_room_id, new_room_id)

    await query.edit_message_text(
        f"✅ Дежурство успешно переназначено на комнату {room_number_new}.\n\n"
        f"Жители комнат (старой, если была, и новой) должны получить уведомления об изменении.",
        reply_markup=get_elder_panel()
    )

# Функции для настроек уведомлений
async def show_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает настройки уведомлений для блока старосты"""
    query = update.callback_query
    current_elder_block_id = context.user_data.get('elder_block_id')

    if not current_elder_block_id:
        await query.edit_message_text(
            "Ошибка: не удалось определить ваш блок. Пожалуйста, войдите снова.",
            reply_markup=get_back_button()
        )
        return

    # Получаем настройки для конкретного блока
    block_settings = get_block_notification_settings(current_elder_block_id)

    # Если какие-то настройки для блока отсутствуют, берем их из DEFAULT_NOTIFICATION_SETTINGS
    preview_time = block_settings.get('preview_time', DEFAULT_NOTIFICATION_SETTINGS['preview_time'])
    duty_time = block_settings.get('duty_time', DEFAULT_NOTIFICATION_SETTINGS['duty_time'])
    preview_text_example = block_settings.get('preview_text', DEFAULT_NOTIFICATION_SETTINGS['preview_text'])
    duty_text_example = block_settings.get('duty_text', DEFAULT_NOTIFICATION_SETTINGS['duty_text'])


    await query.edit_message_text(
        "⚙️ Настройки уведомлений о дежурствах для вашего блока\n\n"
        f"Текущие настройки:\n"
        f"• Предварительное уведомление: {preview_time}\n"
        f"• Дежурное уведомление: {duty_time}\n"
        f"• Текст предварительного (пример): \"{preview_text_example[:50]}...\"\n" # Показываем часть текста
        f"• Текст дежурного (пример): \"{duty_text_example[:50]}...\"\n\n"         # Показываем часть текста
        f"Выберите параметр для изменения:",
        reply_markup=get_notification_settings_menu(preview_time, duty_time)
    )

async def request_preview_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает новое время для предварительного уведомления"""
    query = update.callback_query
    context.user_data['awaiting_preview_time'] = True

    await query.edit_message_text(
        "Введите новое время для предварительного уведомления в формате ЧЧ:ММ (например, 12:00):",
        reply_markup=get_back_button("notification_settings")
    )

async def request_duty_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает новое время для дежурного уведомления"""
    query = update.callback_query
    context.user_data['awaiting_duty_time'] = True

    await query.edit_message_text(
        "Введите новое время для дежурного уведомления в формате ЧЧ:ММ (например, 22:00):",
        reply_markup=get_back_button("notification_settings")
    )

async def request_preview_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает новый текст для предварительного уведомления"""
    query = update.callback_query
    context.user_data['awaiting_preview_text'] = True
    current_elder_block_id = context.user_data.get('elder_block_id')

    current_text = DEFAULT_NOTIFICATION_SETTINGS['preview_text'] # По умолчанию
    if current_elder_block_id:
        block_settings = get_block_notification_settings(current_elder_block_id)
        current_text = block_settings.get('preview_text', current_text)

    await query.edit_message_text(
        f"Текущий текст для вашего блока: \"{current_text}\"\n\n"
        "Введите новый текст для предварительного уведомления:",
        reply_markup=get_back_button("notification_settings")
    )

async def request_duty_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает новый текст для дежурного уведомления"""
    query = update.callback_query
    context.user_data['awaiting_duty_text'] = True
    current_elder_block_id = context.user_data.get('elder_block_id')

    current_text = DEFAULT_NOTIFICATION_SETTINGS['duty_text'] # По умолчанию
    if current_elder_block_id:
        block_settings = get_block_notification_settings(current_elder_block_id)
        current_text = block_settings.get('duty_text', current_text)

    await query.edit_message_text(
        f"Текущий текст для вашего блока: \"{current_text}\"\n\n"
        "Введите новый текст для дежурного уведомления:",
        reply_markup=get_back_button("notification_settings")
    )

# Функции для управления жителями блока
async def list_block_residents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список комнат в блоке с количеством жителей"""
    query = update.callback_query
    current_elder_block_id = context.user_data.get('elder_block_id')

    if not current_elder_block_id:
        await query.edit_message_text(
            "Не удалось определить ваш блок. Обратитесь к администратору.",
            reply_markup=get_back_button("elder_panel")
        )
        return

    # Получаем список комнат в блоке
    rooms = get_rooms_by_block(current_elder_block_id)

    if not rooms:
        await query.edit_message_text(
            "В вашем блоке пока нет комнат. Создайте их или обратитесь к заведующему.",
            reply_markup=get_back_button("elder_panel")
        )
        return

    # Добавляем информацию о количестве жителей в каждой комнате
    rooms_info = []
    total_residents = 0

    for room_id_db, room_number_db in rooms: # Переименовал переменные цикла
        users_in_room = get_users_by_room(room_id_db) # Переименовал
        resident_count = len(users_in_room)
        rooms_info.append((room_id_db, room_number_db, resident_count))
        total_residents += resident_count

    # Разбиваем на страницы
    page = context.user_data.get('rooms_page', 0) # Используем 'rooms_page' для пагинации комнат
    items_per_page = 8
    total_pages = (len(rooms_info) + items_per_page - 1) // items_per_page

    if page >= total_pages and total_pages > 0:
        page = total_pages - 1
        context.user_data['rooms_page'] = page
    elif page < 0 :
        page = 0
        context.user_data['rooms_page'] = page


    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(rooms_info))

    # Создаем клавиатуру
    keyboard = []

    for room_id_page, room_number_page, resident_count_page in rooms_info[start_idx:end_idx]: # Переименовал
        # Иконка показывает есть ли жители в комнате
        room_icon = "🔵" if resident_count_page > 0 else "⚪"
        keyboard.append([InlineKeyboardButton(
            f"{room_icon} Комната {room_number_page} ({resident_count_page} чел.)",
            callback_data=f"show_room_residents_{room_id_page}"
        )])

    # Добавляем навигационные кнопки
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data="rooms_prev"))
    if end_idx < len(rooms_info): # end_idx < len(rooms_info) а не total_pages, т.к. page с 0
        nav_row.append(InlineKeyboardButton("➡️", callback_data="rooms_next"))

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_panel")]) # или elder_panel

    # Формируем сообщение
    message = f"🏠 Список комнат в блоке:\n\n"
    message += f"Всего комнат: {len(rooms_info)}\n"
    message += f"Всего жителей: {total_residents}\n\n"
    if total_pages > 0:
         message += f"Страница {page + 1} из {total_pages}\n"
    message += "Выберите комнату, чтобы просмотреть список её жителей:"

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_room_residents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список жителей конкретной комнаты"""
    query = update.callback_query
    callback_data = query.data

    # Извлекаем ID комнаты из callback_data
    room_id_show = int(callback_data.split('_')[-1]) # Переименовал

    # Сохраняем ID комнаты в контексте для дальнейшего использования (например, для кнопки "Назад")
    context.user_data['current_room_id_for_residents_view'] = room_id_show

    # Получаем номер комнаты
    # current_elder_block_id должен быть в контексте
    current_elder_block_id = context.user_data.get('elder_block_id')
    if not current_elder_block_id: # Добавил проверку
        await query.edit_message_text("Ошибка: блок старосты не определен.", reply_markup=get_back_button("elder_panel"))
        return

    rooms_in_block = get_rooms_by_block(current_elder_block_id) # Получаем комнаты только текущего блока
    room_number_show = None
    for r_id, r_num in rooms_in_block:
        if r_id == room_id_show:
            room_number_show = r_num
            break

    # Получаем список жителей комнаты
    users_in_room_show = get_users_by_room(room_id_show) # Переименовал

    # Формируем сообщение
    if room_number_show:
        message = f"🛏️ Комната {room_number_show}\n\n"
    else:
        message = "🛏️ Выбранная комната (номер не найден)\n\n"

    if users_in_room_show:
        message += f"Список жителей ({len(users_in_room_show)} чел.):\n"
        for i, (user_id_list, username_list) in enumerate(users_in_room_show, 1): # Переименовал
            message += f"{i}. 👤 {username_list}\n"
        message += "\nВыберите жителя для управления:" # Изменил текст

        # Создаем клавиатуру с жителями
        keyboard = []
        for user_id_btn, username_btn in users_in_room_show: # Переименовал
            keyboard.append([InlineKeyboardButton(
                f"👤 {username_btn}",
                callback_data=f"manage_resident_{user_id_btn}"
            )])

        # Кнопка назад
        keyboard.append([InlineKeyboardButton("🔙 Назад к списку комнат", callback_data="list_residents")])

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        message += "В этой комнате пока нет зарегистрированных жителей."

        # Только кнопка назад
        keyboard = [[InlineKeyboardButton("🔙 Назад к списку комнат", callback_data="list_residents")]]

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def show_resident_actions(update: Update, context: ContextTypes.DEFAULT_TYPE, resident_user_id: int): # user_id переименован
    """Показывает действия, доступные для управления жителем"""
    query = update.callback_query

    # Получаем информацию о пользователе
    room_id_resident = get_user_room_id(resident_user_id) # Переименовал
    room_number_resident = "Неизвестно"
    username_resident = f"Пользователь {resident_user_id}" # Дефолтное имя

    if room_id_resident:
        room_details_resident = get_room_details(room_id_resident) # Переименовал
        if room_details_resident:
            room_number_resident = room_details_resident[0]

        # Получаем имя пользователя (если есть в комнате, но должно быть)
        users_in_room_resident = get_users_by_room(room_id_resident) # Переименовал
        for u_id, u_name in users_in_room_resident:
            if u_id == resident_user_id:
                username_resident = u_name
                break

    message = f"👤 Житель: {username_resident}\n🛏️ Комната: {room_number_resident}\n\nВыберите действие:"

    # Сохраняем ID пользователя в контексте для следующих шагов
    context.user_data['resident_user_id_manage'] = resident_user_id # Изменил ключ

    # Кнопка назад должна вести к просмотру жителей той комнаты, откуда пришли
    # room_id_resident - это комната управляемого жителя.
    back_callback = f"show_room_residents_{room_id_resident}" if room_id_resident else "list_residents"


    # Создаем клавиатуру
    keyboard = [
        # [InlineKeyboardButton("🔄 Изменить комнату", callback_data="change_resident_room")], # Эта кнопка неоднозначна
        # Вместо этого сделаем так:
        [InlineKeyboardButton("🔄 Изменить комнату", callback_data=f"change_resident_room_{resident_user_id}")],
        # [InlineKeyboardButton("❌ Удалить жителя", callback_data="confirm_delete_resident")], # Эта кнопка неоднозначна
        # Вместо этого:
        [InlineKeyboardButton("❌ Удалить жителя", callback_data=f"confirm_delete_resident_{resident_user_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data=back_callback)]
    ]

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def change_resident_room(update: Update, context: ContextTypes.DEFAULT_TYPE): # Эта функция теперь вызывается с user_id в callback_data
    """Показывает список комнат для перемещения жителя"""
    query = update.callback_query
    # Извлекаем user_id из callback_data, если он там есть
    resident_user_id_change = None
    if query.data.startswith("change_resident_room_"):
        try:
            resident_user_id_change = int(query.data.split("_")[-1])
            context.user_data['resident_user_id_manage'] = resident_user_id_change # Сохраняем или обновляем
        except ValueError:
            pass # Не удалось извлечь ID

    if not resident_user_id_change: # Если ID не был в callback_data, берем из контекста
        resident_user_id_change = context.user_data.get('resident_user_id_manage')


    current_elder_block_id = context.user_data.get('elder_block_id')

    if not resident_user_id_change or not current_elder_block_id:
        await query.edit_message_text(
            "Не удалось получить информацию о жителе или блоке.",
            reply_markup=get_back_button("list_residents")
        )
        return

    # Получаем информацию о текущей комнате жителя
    current_room_id_resident = get_user_room_id(resident_user_id_change)
    current_room_number_resident = "Нет"
    if current_room_id_resident:
        room_details_current = get_room_details(current_room_id_resident)
        if room_details_current:
            current_room_number_resident = room_details_current[0]

    # Получаем имя пользователя
    # Можно получить из get_user, но раз уж мы в контексте комнаты...
    username_change = f"Пользователь {resident_user_id_change}"
    if current_room_id_resident:
        users_in_current_room = get_users_by_room(current_room_id_resident)
        for u_id, u_name in users_in_current_room:
            if u_id == resident_user_id_change:
                username_change = u_name
                break
    else: # Если у пользователя нет комнаты, пытаемся получить его username из таблицы users
        user_data_db = context.bot_data.get('db_get_user_function', lambda x: (None, f"User {x}", None, None))(resident_user_id_change) # Заглушка, нужна реальная функция
        if user_data_db and user_data_db[1]:
            username_change = user_data_db[1]


    # Получаем список всех комнат в блоке старосты
    rooms_in_block_change = get_rooms_by_block(current_elder_block_id)

    if not rooms_in_block_change:
        await query.edit_message_text(
            "В вашем блоке нет комнат для перемещения жителя.",
            reply_markup=get_back_button(f"manage_resident_{resident_user_id_change}") # Назад к действиям с этим жителем
        )
        return

    # Создаем клавиатуру с комнатами
    keyboard = []

    for room_id_btn_change, room_number_btn_change in rooms_in_block_change:
        # Отмечаем текущую комнату
        if room_id_btn_change == current_room_id_resident:
            room_label = f"🔵 Комната {room_number_btn_change} (Текущая)"
        else:
            room_label = f"⚪ Комната {room_number_btn_change}"

        keyboard.append([InlineKeyboardButton(
            room_label,
            callback_data=f"set_resident_room_{resident_user_id_change}_{room_id_btn_change}" # Передаем оба ID
        )])

    # Кнопка назад
    keyboard.append([InlineKeyboardButton(
        "🔙 Назад",
        callback_data=f"manage_resident_{resident_user_id_change}" # Назад к действиям с этим жителем
    )])

    # Формируем сообщение
    message = f"🔄 Изменение комнаты\n\n"
    message += f"Житель: 👤 {username_change}\n"
    message += f"Текущая комната: 🛏️ {current_room_number_resident}\n\n"
    message += "Выберите новую комнату для жителя:"

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def set_resident_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменяет комнату жителя и отправляет ему уведомление"""
    query = update.callback_query
    callback_data = query.data

    # Извлекаем ID пользователя и комнаты из callback_data
    parts = callback_data.split('_')
    user_id_set = int(parts[-2])
    new_room_id_set = int(parts[-1])

    # Получаем информацию о текущей комнате
    old_room_id_set = get_user_room_id(user_id_set)
    old_room_number_set = "Нет"
    if old_room_id_set:
        room_details_old = get_room_details(old_room_id_set)
        if room_details_old:
            old_room_number_set = room_details_old[0]

    # Получаем информацию о новой комнате
    new_room_number_set = "Неизвестно"
    room_details_new = get_room_details(new_room_id_set)
    if room_details_new:
        new_room_number_set = room_details_new[0]

    # Получаем имя пользователя (можно использовать telegram username, если доступен)
    username_set = f"Пользователь {user_id_set}"
    # Попробуем получить из Telegram, если есть query.from_user (для callback) или update.effective_user
    effective_user_to_get_name = query.from_user if query else update.effective_user
    if effective_user_to_get_name and effective_user_to_get_name.id == user_id_set: # Если это сам пользователь
         username_set = effective_user_to_get_name.username or effective_user_to_get_name.first_name
    else: # Если это другой пользователь, надо доставать из БД
        # Заглушка для получения имени пользователя, нужна реальная функция get_user(user_id_set)
        # user_db_info = get_user(user_id_set)
        # if user_db_info: username_set = user_db_info[1]
        pass # Пока оставим как есть, если не сам пользователь


    # Обновляем комнату пользователя
    success = update_user_room(user_id_set, new_room_id_set)

    if success:
        # Отправляем уведомление пользователю
        try:
            # Подготавливаем текст уведомления
            notification_text = f"📣 Уведомление от старосты\n\n"
            notification_text += "Ваша комната была изменена.\n\n"
            notification_text += f"Старая комната: {old_room_number_set}\n"
            notification_text += f"Новая комната: {new_room_number_set}"

            await context.bot.send_message(chat_id=user_id_set, text=notification_text)
            notification_sent_msg = "Уведомление отправлено жителю."
        except Exception as e:
            print(f"Ошибка при отправке уведомления пользователю {user_id_set}: {str(e)}")
            notification_sent_msg = "Не удалось отправить уведомление жителю."


        # Отображаем успешное сообщение старосте
        success_message = "✅ Комната успешно изменена.\n\n"
        success_message += f"Житель: {username_set}\n"
        success_message += f"Старая комната: {old_room_number_set}\n"
        success_message += f"Новая комната: {new_room_number_set}\n\n"
        success_message += notification_sent_msg

        # Возвращаемся к списку комнат
        await query.edit_message_text(
            success_message,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                "🔙 Назад к списку комнат",
                callback_data="list_residents"
            )]])
        )

    else:
        # Если не удалось обновить комнату
        await query.edit_message_text(
            "❌ Не удалось изменить комнату. Попробуйте еще раз или обратитесь к администратору.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                "🔙 Назад",
                callback_data=f"manage_resident_{user_id_set}"
            )]])
        )

async def confirm_delete_resident(update: Update, context: ContextTypes.DEFAULT_TYPE): # Вызывается с user_id в callback_data
    """Запрашивает подтверждение удаления жителя"""
    query = update.callback_query
    resident_user_id_confirm = None
    if query.data.startswith("confirm_delete_resident_"):
        try:
            resident_user_id_confirm = int(query.data.split("_")[-1])
            context.user_data['resident_user_id_manage'] = resident_user_id_confirm
        except ValueError:
            pass

    if not resident_user_id_confirm:
        resident_user_id_confirm = context.user_data.get('resident_user_id_manage')


    if not resident_user_id_confirm:
        await query.edit_message_text(
            "Не удалось получить информацию о жителе для удаления.",
            reply_markup=get_back_button("list_residents")
        )
        return

    # Получаем информацию о пользователе
    room_id_confirm = get_user_room_id(resident_user_id_confirm)
    room_number_confirm = "Нет"
    username_confirm = f"Пользователь {resident_user_id_confirm}"

    if room_id_confirm:
        room_details_confirm = get_room_details(room_id_confirm)
        if room_details_confirm:
            room_number_confirm = room_details_confirm[0]

        users_in_room_confirm = get_users_by_room(room_id_confirm)
        for u_id, u_name in users_in_room_confirm:
            if u_id == resident_user_id_confirm:
                username_confirm = u_name
                break
    else: # Если нет комнаты, пытаемся получить username
        # user_data_db_confirm = get_user(resident_user_id_confirm)
        # if user_data_db_confirm: username_confirm = user_data_db_confirm[1]
        pass


    # Формируем сообщение
    message = "⚠️ Подтверждение удаления\n\n"
    message += f"Житель: 👤 {username_confirm}\n"
    message += f"Комната: 🛏️ {room_number_confirm}\n\n"
    message += "Вы действительно хотите удалить этого жителя из системы?\n"
    message += "Пользователь получит уведомление об удалении. Это действие необратимо."

    # Создаем клавиатуру
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data=f"delete_resident_{resident_user_id_confirm}")], # Передаем ID
        [InlineKeyboardButton("❌ Отмена", callback_data=f"manage_resident_{resident_user_id_confirm}")] # Назад к управлению этим жителем
    ]

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def delete_resident(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет жителя и отправляет ему уведомление"""
    query = update.callback_query
    callback_data = query.data

    # Извлекаем ID пользователя из callback_data
    user_id_delete = int(callback_data.split('_')[-1])

    # Получаем информацию о пользователе перед удалением
    room_id_delete = get_user_room_id(user_id_delete)
    room_number_delete = "Нет"
    username_delete = f"Пользователь {user_id_delete}"

    if room_id_delete:
        room_details_delete = get_room_details(room_id_delete)
        if room_details_delete:
            room_number_delete = room_details_delete[0]

        users_in_room_delete = get_users_by_room(room_id_delete)
        for u_id, u_name in users_in_room_delete:
            if u_id == user_id_delete:
                username_delete = u_name
                break
    else: # Если нет комнаты
        # user_data_db_delete = get_user(user_id_delete)
        # if user_data_db_delete: username_delete = user_data_db_delete[1]
        pass


    try:
        # Отправляем уведомление пользователю перед удалением
        notification_text = f"📣 Уведомление от старосты\n\n"
        notification_text += "Вы были удалены из системы управления дежурствами для вашего блока.\n\n"
        if room_number_delete != "Нет":
            notification_text += f"Комната: {room_number_delete}\n\n"
        notification_text += "Если вы считаете, что это ошибка, пожалуйста, обратитесь к старосте вашего блока."

        await context.bot.send_message(chat_id=user_id_delete, text=notification_text)
        notification_sent_msg_del = "Уведомление об удалении отправлено пользователю."
    except Exception as e:
        print(f"Ошибка при отправке уведомления об удалении пользователю {user_id_delete}: {str(e)}")
        notification_sent_msg_del = "Не удалось отправить уведомление пользователю."

    # Удаляем пользователя (полностью из системы или только из комнаты/блока?)
    # Текущая delete_user удаляет полностью. Это может быть слишком радикально для старосты.
    # Возможно, староста должен иметь возможность только "открепить" от комнаты.
    # Пока оставляем delete_user.
    delete_user(user_id_delete) # Это удаляет пользователя из таблицы users

    # Формируем сообщение о результате
    result_message = "✅ Житель успешно удален из системы.\n\n"
    result_message += f"Житель: {username_delete}\n"
    if room_number_delete != "Нет":
        result_message += f"Комната: {room_number_delete}\n\n"
    result_message += notification_sent_msg_del

    await query.edit_message_text(
        result_message,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            "🔙 Назад к списку комнат",
            callback_data="list_residents"
        )]])
    )

async def confirm_remove_resident(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_confirm_remove: int): # user_id переименован
    """Запрашивает подтверждение удаления жителя (старый вариант, используется в get_resident_actions_menu)"""
    query = update.callback_query

    await query.edit_message_text(
        "Вы уверены, что хотите удалить этого жителя из системы?\n\n"
        "Это действие нельзя отменить.",
        reply_markup=get_confirmation_menu("remove_resident_final", user_id_confirm_remove) # Изменил action для уникальности
    )

async def remove_resident(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_remove_final: int): # user_id переименован
    """Удаляет жителя из системы (старый вариант, вызывается из confirm_remove_resident)"""
    # Этот обработчик вызывается, если callback_data = "confirm_remove_resident_final_USERID"
    query = update.callback_query

    # Удаляем пользователя
    delete_user(user_id_remove_final)

    await query.edit_message_text(
        "✅ Житель успешно удален из системы.",
        reply_markup=get_back_button("list_residents") # Возврат к списку комнат/жителей
    )

# Функции для создания комнат
async def request_room_range(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает диапазон номеров комнат для создания"""
    query = update.callback_query
    current_elder_block_id = context.user_data.get('elder_block_id')

    if not current_elder_block_id:
        await query.edit_message_text(
            "Не удалось определить ваш блок. Обратитесь к администратору.",
            reply_markup=get_back_button("elder_panel")
        )
        return

    context.user_data['awaiting_room_range'] = True

    await query.edit_message_text(
        "Введите диапазон номеров комнат, которые нужно создать (например, 101-110 или просто 101 для одной комнаты):",
        reply_markup=get_back_button("elder_panel")
    )

async def process_room_range(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод диапазона комнат и создает комнаты"""
    # user_id = update.effective_user.id # Не используется здесь
    room_range_text = update.message.text
    current_elder_block_id = context.user_data.get('elder_block_id')

    if not current_elder_block_id:
        await update.message.reply_text(
            "Не удалось определить ваш блок. Обратитесь к администратору.",
            reply_markup=get_elder_panel()
        )
        return

    # Проверяем формат ввода: ожидаем "N-M", где N и M - числа, или "N"
    try:
        if '-' in room_range_text:
            # Формат "N-M"
            start_num_str, end_num_str = room_range_text.split('-', 1)
            start_num = int(start_num_str.strip())
            end_num = int(end_num_str.strip())
        else:
            # Формат одного числа
            start_num = end_num = int(room_range_text.strip())

        if start_num <= 0 or end_num <= 0:
             await update.message.reply_text(
                "❌ Номера комнат должны быть положительными числами.",
                reply_markup=get_elder_panel()
            )
             return

        if start_num > end_num: # Если ввели в обратном порядке, меняем местами
            start_num, end_num = end_num, start_num

        # Ограничиваем количество создаваемых комнат для защиты от злоупотребления
        if end_num - start_num + 1 > 50: # +1 т.к. диапазон включительный
            await update.message.reply_text(
                "❌ Вы пытаетесь создать слишком много комнат. Максимальное количество за раз - 50 комнат.",
                reply_markup=get_elder_panel()
            )
            return

        # Удаляем все существующие комнаты в блоке ПЕРЕД добавлением новых
        # Это поведение было в вашем коде. Если нужно добавлять, а не заменять, эту строку надо убрать.
        delete_rooms_in_block(current_elder_block_id)

        # Создаем новые комнаты в заданном диапазоне
        created_rooms_numbers = [] # Будем хранить номера созданных комнат

        for room_number_create in range(start_num, end_num + 1):
            # Создаем новую комнату
            new_room_id_create = add_room(current_elder_block_id, room_number_create)
            if new_room_id_create:
                created_rooms_numbers.append(str(room_number_create)) # Сохраняем как строку для join

        # Формируем отчет о результатах
        if created_rooms_numbers:
            message = f"✅ Список комнат в блоке обновлен. Добавлены комнаты: {', '.join(created_rooms_numbers)}"
        else:
            # Это может случиться, если delete_rooms_in_block сработал, а add_room нет,
            # или если диапазон был некорректен и не прошел проверки (хотя проверки выше)
            message = "❌ Комнаты не были созданы. Убедитесь, что диапазон корректен. Если все существующие комнаты были удалены, а новые не добавлены, возможно, произошла ошибка."

        await update.message.reply_text(
            message,
            reply_markup=get_elder_panel()
        )

    except ValueError:
        await update.message.reply_text(
            "❌ Неправильный формат ввода. Пожалуйста, введите диапазон в формате '101-110' или одно число для создания одной комнаты.",
            reply_markup=get_elder_panel()
        )