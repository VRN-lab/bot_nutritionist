import os
import logging
import re

import sqlite3
from telegram.constants import ParseMode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    filters, ContextTypes,
    CommandHandler, MessageHandler, CallbackQueryHandler,
    CallbackContext, Application
)
from dotenv import load_dotenv

from texts import start_message, result_message

conn = sqlite3.connect('data.db')
c = conn.cursor()


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.ERROR
)

load_dotenv()
TOKEN = os.getenv('TOKEN')
START_MESSAGE = start_message
RESULT_MESSAGE = result_message


c.execute('''
    CREATE TABLE IF NOT EXISTS anthropometry (
        user_id INTEGER PRIMARY KEY,
        name TEXT DEFAUL None,
        height INTEGER DEFAULT 0,
        weight INTEGER DEFAULT 0,
        age INTEGER DEFAULT 0,
        sex INTEGER DEFAULT 0
    )
''')
conn.commit()


async def sex():
    keyboard = [
        [
            InlineKeyboardButton('Мужской', callback_data='Male'),
            InlineKeyboardButton('Женский', callback_data='Female'),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def confirm_or_refresh():
    keyboard = [
        [
            InlineKeyboardButton('Подтвердить', callback_data='Confirm'),
            InlineKeyboardButton('Ввести заново', callback_data='Refresh'),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def incoming():
    keyboard = [
        [InlineKeyboardButton(
            'Хочу похудеть',
            url='https://t.me/lena_kamchatka'
        )],
    ]
    return InlineKeyboardMarkup(keyboard)


async def add_user_id(update: Update, context: CallbackContext) -> None:
    """
    Добавляем id пользователя в таблицу
    """
    user_id = update.effective_user.id
    c.execute(
        "INSERT OR IGNORE INTO anthropometry (user_id) VALUES (?)", (user_id,)
    )
    conn.commit()


async def column_name():
    """
    Получаем название стобца
    """
    c.execute('SELECT * FROM anthropometry')

    column_names = [description[0] for description in c.description]

    return column_names


async def receiving_data(
    update: Update, context: CallbackContext, value
) -> None:
    """
    Получаем значение счетчика
    """
    user_id = update.effective_user.id

    try:
        c.execute(
            f"SELECT {value} FROM anthropometry WHERE user_id = ?",
            (user_id,)
        )
        result = c.fetchone()[0]

        return result
    except TypeError:
        return


async def add_user_in_db(
        update: Update, context: CallbackContext, column, value
) -> None:
    """
    Добавляем id пользователя в таблицу
    """
    user_id = update.effective_user.id

    c.execute(
        "INSERT OR IGNORE INTO anthropometry (user_id) VALUES (?)", (user_id,)
    )
    c.execute(
        f"UPDATE anthropometry SET {column} = ? WHERE user_id = ?",
        (value, user_id),
    )

    conn.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запускает бота и проверяет, есть ли уже расчет,
    если есть, то показывет предыдущее значение
    """
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name
    user_name_full = update.effective_user.full_name
    sum_result = await result(update, context)
    column_names = await column_name()
    await add_user_id(update, context)
    await add_user_in_db(update, context, column_names[1], user_name_full)
    check_age = await receiving_data(update, context, column_names[4])
    if check_age == 0:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f'Привет {user_name} 👋\n\n{START_MESSAGE}',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=await sex()
        )
    elif check_age != 0:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f'*Ваш предыдущий результат = {sum_result}*\n\n'
            f'Нажмите в _меню_ *повторить*, что бы расчитать заново\n\n'
            f'{RESULT_MESSAGE}',
            parse_mode=ParseMode.MARKDOWN,
        )


async def callback_handler(update: Update, context: CallbackContext):
    """
    Обрабатывает нажатие на inline кнопки
    """
    query = update.callback_query
    data = query.data
    chat_id = update.effective_chat.id
    column_names = await column_name()
    sum_result = await result(update, context)
    await query.answer()
    if data == 'Male':
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([])
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text='Введита Ваш рост в см.',
        )
        await add_user_in_db(update, context, column_names[5], 5)
    elif data == 'Female':
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([])
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text='Введита Ваш рост в см.',
        )
        await add_user_in_db(update, context, column_names[5], 161)
    elif data == 'Confirm':
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([])
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=f'Ваш результат {sum_result}\n\n{RESULT_MESSAGE}',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=await incoming()
        )
    elif data == 'Refresh':
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([])
        )
        await refresh(update, context)
        await context.bot.send_message(
            chat_id=chat_id,
            text='Повторите ввод. Ваш пол:',
            reply_markup=await sex()
        )


async def message_handler(update: Update, context: CallbackContext):
    """
    Обрабатывает входящие сообщение от пользователя
    """
    message = update.message.text
    chat_id = update.effective_chat.id
    column_names = await column_name()
    check_height = await receiving_data(update, context, column_names[2])
    check_weight = await receiving_data(update, context, column_names[3])
    check_age = await receiving_data(update, context, column_names[4])
    pattern = r'^\d*\.?\d+$'
    pattern_2 = r'^\d+'
    if check_height == 0:
        if re.match(pattern_2, message):
            await add_user_in_db(update, context, column_names[2], message)
            await context.bot.send_message(
                chat_id=chat_id,
                text='Введите ваш вес в кг например 50 или 50.2',
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id, text='Введите только цифры',
            )
    if check_height != 0:
        if check_weight == 0:
            if re.match(pattern, message):
                await add_user_in_db(update, context, column_names[3], message)
                await context.bot.send_message(
                    chat_id=chat_id, text='Введите ваш возраст',
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id, text='Неверно введите только цифры например 61 или 61.7, ввод граммов через точку',  # noqa
                )
    if check_weight != 0:
        if check_age == 0:
            if re.match(pattern_2, message):
                await add_user_in_db(update, context, column_names[4], message)
                await check(update, context)
            else:
                await context.bot.send_message(
                    chat_id=chat_id, text='Введите только цифры',
                )


async def check(update, context):
    """
    Вызывает все введенные данные для провекри пользователем
    """
    column_names = await column_name()
    chat_id = update.effective_chat.id
    height = await receiving_data(update, context, column_names[2])
    weight = await receiving_data(update, context, column_names[3])
    age = await receiving_data(update, context, column_names[4])
    text = f"""
    *Проверьте правильность введенных данных*\n
    Рост - {height}  см
    Вес - {weight}   кг
    Возраст - {age}  лет/год(а)\n
    Если все правильно нажмите *<Подтердить>*,
    если надо что то изменить нажмите *<Ввести заново>*
    """
    await context.bot.send_message(
        chat_id=chat_id, text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=await confirm_or_refresh()
    )


async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Выводит результат с расчетом по формуле
    """
    column_names = await column_name()
    height = await receiving_data(update, context, column_names[2])
    weight = await receiving_data(update, context, column_names[3])
    age = await receiving_data(update, context, column_names[4])
    sex = await receiving_data(update, context, column_names[5])
    try:
        if int(sex) == 5:
            summ = (
                (9.99 * float(weight)) + (6.25 * float(height)) -
                (4.92 * int(age)) + int(sex)
            )

            return "{:.2f}".format(summ)
        elif int(sex) == 161:
            summ = (
                (9.99 * int(weight)) + (6.25 * float(height)) -
                (4.92 * int(age)) - int(sex)
            )
            return "{:.2f}".format(summ)

    except TypeError:

        return


async def refresh(update: Update, context: CallbackContext) -> None:
    """
    Восстанавливаем значения по умолчанию при выполнении команды refresh
    и запсукаем бота заново
    """
    user_id = update.effective_user.id
    c.execute(
        "UPDATE anthropometry SET height = 0 WHERE user_id = ?", (user_id,)
    )
    c.execute(
        "UPDATE anthropometry SET weight = 0 WHERE user_id = ?", (user_id,)
    )
    c.execute(
        "UPDATE anthropometry SET age = 0 WHERE user_id = ?", (user_id,)
    )
    c.execute(
        "UPDATE anthropometry SET sex = 0 WHERE user_id = ?", (user_id,)
    )

    conn.commit()
    await start(update, context)


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("refresh", refresh))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    application.run_polling()
    conn.close()


if __name__ == "__main__":
    main()
