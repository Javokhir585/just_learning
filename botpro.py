from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
import pyodbc
from datetime import datetime

# Database connection details
DB_SERVER = 'Navsuv'
DB_USER = '1c'
DB_PASSWORD = 'xxxx1111*'
DB_NAME = 'Suvtaminoti_venons'
DB_TABLE = 'БотДанныеЗупСувОкава'

# Define states
ENTERING_TAB_NOMER = 1
SELECTING_PERIOD = 2

def replace_special_characters(text):
    if not isinstance(text, str):
        return text
    
    replacements = {
        "@": "ғ",
        "#": "ҳ",
        "&": "Қ",
        "*": "Ғ",
        "?": "қ",
        "$": "Ҳ"
    }

    for old_char, new_char in replacements.items():
        text = text.replace(old_char, new_char)
    
    return text


# Create a database connection
def create_connection():
    conn_str = (
        'DRIVER={SQL Server};'  # Use the working driver
        f'SERVER={DB_SERVER};'
        f'DATABASE={DB_NAME};'
        f'UID={DB_USER};'
        f'PWD={DB_PASSWORD};'
    )
    return pyodbc.connect(conn_str)
# Function to check if chat_id is registered
def is_registered(chat_id):
    with create_connection() as conn:
        cursor = conn.cursor()
        query = f"SELECT COUNT(*) FROM {DB_TABLE} WHERE IDСотрудник = ?"
        cursor.execute(query, (str(chat_id),))  # Treat chat_id as a string
        return cursor.fetchone()[0] > 0

# Function to get the chat_id associated with the tab_nomer
def get_chat_id_for_tab_nomer(tab_nomer):
    with create_connection() as conn:
        cursor = conn.cursor()
        tab_nomer = str(tab_nomer).strip()  # Ensure tab_nomer is treated as a string
        print(f"Debug: Querying for tab_nomer: {tab_nomer}")  # Debugging line
        query = f"SELECT IDСотрудник FROM {DB_TABLE} WHERE ТабНом = ?"
        cursor.execute(query, (tab_nomer,))
        result = cursor.fetchone()
        print(f"Debug: Query result: {result}")  # Debugging line
        return result[0] if result else None


# Function to get unique periods in mm-YYYY format for the registered user
def get_unique_periods(tab_nomer, chat_id):
    with create_connection() as conn:
        cursor = conn.cursor()
        query = f"""
        SELECT DISTINCT Период
        FROM {DB_TABLE}
        WHERE ТабНом = ? AND IDСотрудник = ?
        """
        cursor.execute(query, (str(tab_nomer), str(chat_id)))  # Ensure both are treated as strings
        rows = cursor.fetchall()
        
        periods = [row[0].strftime('%m-%Y') for row in rows]
        return sorted(set(periods), reverse=True)

def get_data_for_period(tab_nomer, chat_id, period):
    with create_connection() as conn:
        cursor = conn.cursor()

        # Convert period to 'YYYY-MM' format and use it in the query
        period_formatted = period[-4:] + '-' + period[:2]  # Convert 'MM-YYYY' to 'YYYY-MM'

        query = f"""
        SELECT ВидРасчетаКод, ВидРасчета, Результат, Вид, Дни, Часы
        FROM {DB_TABLE}
        WHERE ТабНом = ? AND IDСотрудник = ? AND CONVERT(VARCHAR(7), Период, 126) = ?
        """
        cursor.execute(query, (str(tab_nomer), str(chat_id), period_formatted))  # Ensure tab_nomer and chat_id are strings
        rows = cursor.fetchall()

        data = {'Нач': [], 'Уд': [], 'Об': []}  # Added 'Об' to store total values
        for row in rows:
            вид = row[3]
            item = {
                'ВидРасчетаКод': row[0],
                'ВидРасчета': row[1],
                'Результат': row[2],
                'Дни': row[4],  # Added Дни
                'Часы': row[5],  # Added Часы
            }
            if вид == 'Нач':
                data['Нач'].append(item)
            elif вид == 'Уд':
                data['Уд'].append(item)
            elif вид == 'Об':  # Handle 'Об' (Общий итог)
                data['Об'].append(item)
        
        return data['Нач'], data['Уд'], data['Об']  # Return the total 'Об' list

# Command handler for /start
async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    if is_registered(chat_id):
        context.user_data['chat_id'] = chat_id
        context.user_data['state'] = ENTERING_TAB_NOMER
        
        await update.message.reply_text('🇷🇺 Вы уже зарегистрированы. Пожалуйста, введите ваш табельный номер:')
        await update.message.reply_text("🇺🇿 Siz allaqachon ro'yxatdan o'tgansiz. Iltimos, tabel raqamingizni kiriting:")
    else:
        await update.message.reply_text('🇷🇺 Вы не зарегистрированы. Нажмите /getid, чтобы увидеть свой идентификатор чата для регистрации.')
        await update.message.reply_text("🇺🇿 Siz ro'yxatdan o'tmagansiz. Roʻyxatdan oʻtish uchun  /getid tugmasini bosing.")

# Command handler for /getid (for unregistered users to get their chat_id)
async def getid(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"🇷🇺 Ваш идентификатор чата: {chat_id}. Свяжитесь с администратором для регистрации.")
    await update.message.reply_text(f"🇺🇿 Sizning chat identifikatoringiz: {chat_id}. Roʻyxatdan oʻtish uchun admin bilan bogʻlaning.")

# Handler for user input (tab_nomer)
async def handle_user_input(update: Update, context: CallbackContext):
    text = update.message.text
    state = context.user_data.get('state')

    if state == ENTERING_TAB_NOMER:
        await handle_tab_nomer(update, context, text)
    elif state == SELECTING_PERIOD:
        await handle_period_selection(update, context, text)
    else:
        await update.message.reply_text('🇷🇺 Неожиданный ввод. Пожалуйста, начните заново, используя /start.')
        await update.message.reply_text('🇺🇿 Kutilmagan kirish komandasi. Iltimos, /start yordamida qaytadan boshlang.')

# Function to handle tab_nomer input
async def handle_tab_nomer(update: Update, context: CallbackContext, text):
    chat_id = context.user_data.get('chat_id')

    if not chat_id:
        await update.message.reply_text('🇷🇺 Ошибка: Идентификатор чата не найден. Пожалуйста, начните снова, используя /start.')
        await update.message.reply_text('🇺🇿 Xatolik: Chat identifikatoringiz topilmadi. Iltimos, /start yordamida qaytadan boshlang.')
        return

    tab_nomer = str(text).strip()  # Ensure tab_nomer is a string

    print(f"Debug: Entered tab_nomer: {tab_nomer}")  # Debugging line

    expected_chat_id = get_chat_id_for_tab_nomer(tab_nomer)
    
    print(f"Debug: Retrieved expected_chat_id: {expected_chat_id}")  # Debugging line

    if expected_chat_id is None:
        await update.message.reply_text(f'🇷🇺 Табельный номер {tab_nomer} не найден в базе.')
        await update.message.reply_text(f"🇺🇿 Ma'lumotlar bazasida {tab_nomer} tabel raqami topilmadi.")
    elif str(expected_chat_id) == str(chat_id):
        unique_periods = get_unique_periods(tab_nomer, chat_id)
        
        if unique_periods:
            buttons = [[period] for period in unique_periods]
            reply_markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(" 📆 Выберите период, который хотите просмотреть👇", reply_markup=reply_markup)
            await update.message.reply_text(" 📆 Ko'rmoqchi bo'lgan davringizni tanlang👇 ", reply_markup=reply_markup)
            context.user_data['tab_nomer'] = tab_nomer
            context.user_data['state'] = SELECTING_PERIOD
        else:
            await update.message.reply_text("Данные не найдены")
            await update.message.reply_text("Ma'lumotlar topilmadi")
    else:
        await update.message.reply_text(f"🇷🇺 Вы зарегистрировались не по этому {tab_nomer} табельному номеру. Свяжитесь с администратором.")
        await update.message.reply_text(f"🇺🇿 Ushbu {tab_nomer} tabel raqami bilan registratsiyadan o'tmagansiz, administrator bilan bog'laning.")

async def handle_period_selection(update: Update, context: CallbackContext, period):
    tab_nomer = context.user_data.get('tab_nomer')
    chat_id = context.user_data.get('chat_id')

    if not tab_nomer or not chat_id:
        await update.message.reply_text('Ошибка! Пожалуйста, начните снова, используя /start.')
        return

    # Fetch the required data for the period
    data_nach, data_ud, data_ob = get_data_for_period(tab_nomer, chat_id, period)
    
    # Fetch employee details (Сотрудник, Дни, Часы)
    with create_connection() as conn:
        cursor = conn.cursor()
        query = f"SELECT Сотрудник, Дни, Часы FROM {DB_TABLE} WHERE IDСотрудник = ?"
        cursor.execute(query, str(chat_id))
        result = cursor.fetchone()

        # Apply special character replacement to the employee's name (Сотрудник)
        employee_name = replace_special_characters(result[0])
        dni = result[1]  # Дни
        chasi = result[2]  # Часы
    
    # Construct the message for Начисления and Удержания
    message_nach = f"📅 Период: {period}\n\n"
    message_nach += f"👤 Сотрудник: {employee_name}\n\n"
    message_nach += "⚡️ Начисления:\n"

    # Process Начисления
    for item in data_nach:
        vid_rascheta = replace_special_characters(item['ВидРасчета'])
        days = item['Дни']
        hours = item['Часы']
        result = item['Результат']
        formatted_result = f"{result:,.2f}".replace(",", " ")  # Format for Russian number display
        
        line = f"🔹 {vid_rascheta} — {formatted_result} сум"
        if days != 0 and days != 0.0:
            line += f" \n Дни:{days}"
        if hours != 0 and hours != 0.0:
            line += f"  Часы:{hours}"
        message_nach += f"{line}\n"

    message_ud = "\n⚡️ Удержания:\n"

    # Process Удержания
    for item in data_ud:
        vid_rascheta = replace_special_characters(item['ВидРасчета'])
        days = item['Дни']
        hours = item['Часы']
        result = item['Результат']
        formatted_result = f"{result:,.2f}".replace(",", " ")
        
        line = f"🔸 {vid_rascheta} — {formatted_result} сум"
        if days != 0 and days != 0.0:
            line += f" \n Дни:{days}"
        if hours != 0 and hours != 0.0:
            line += f"  Часы:{hours}"
        message_ud += f"{line}\n"

    message_ob = "\n🧮 Общий итог:\n"

    # Process Общий итог (Об)
    for item in data_ob:
        vid_rascheta = replace_special_characters(item['ВидРасчета'])
        days = item['Дни']
        hours = item['Часы']
        result = item['Результат']
        formatted_result = f"{result:,.2f}".replace(",", " ")
        
        line = f"🔹 {vid_rascheta} — {formatted_result} сум"
        if days != 0 and days != 0.0:
            line += f" \n Дни:{days}"
        if hours != 0 and hours != 0.0:
            line += f"  Часы:{hours}"
        message_ob += f"{line}\n"

    # Send the final message with Начисления, Удержания, and Общий итог
    await update.message.reply_text(message_nach + message_ud + message_ob, parse_mode='HTML')



    


# Main function to run the bot
def main():
    application = Application.builder().token("6147266336:AAEVYYZCy270VDW9gZwA9d40dyRfunavmVk").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("getid", getid))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    application.run_polling()

if __name__ == '__main__':
    main()
