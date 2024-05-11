import json
from itertools import islice

from aiogram import types
from aiogram.types.reply_keyboard import ReplyKeyboardMarkup
from texts import Texts


class Markups:

    @staticmethod
    def chunk(it, size):
        it = iter(it)
        return iter(lambda: tuple(islice(it, size)), ())

    @staticmethod
    def get_titles_from_kb(kb: types.ReplyKeyboardMarkup):
        json_kb = json.loads(kb.as_json())['keyboard']
        titles = []
        for row in json_kb:
            for btn in row:
                titles.append(btn)
        return titles

    start_menu_mrkup = ReplyKeyboardMarkup(resize_keyboard=True)
    start_menu_mrkup.add('👀Рассчитайте свой архетип')
    start_menu_mrkup.add('📋Информационный отдел')
    start_menu_mrkup.add('🎁Ежедневный подарок')
    titles_start_menu_mrkup = get_titles_from_kb(start_menu_mrkup)

    info_menu_mrkup = ReplyKeyboardMarkup(resize_keyboard=True)
    for item in Texts.info_items.keys():
        info_menu_mrkup.add(item)
    info_menu_mrkup.add("👈Обратно")

    sex_mrkup = ReplyKeyboardMarkup(resize_keyboard=True)
    sex_mrkup.add('М', 'Ж')
    sex_mrkup.add("👈Обратно")

    daily_bonus_mrkup = ReplyKeyboardMarkup(resize_keyboard=True)
    daily_bonus_mrkup.add('📝Получить чек-лист "Ограничивающие убеждения"')
    daily_bonus_mrkup.add('📝Получить чек-лист "Ресурсное состояние"')
    daily_bonus_mrkup.add('💫Узнать архетип дня')
    daily_bonus_mrkup.add("📚 Подборка книг об архетипах")
    daily_bonus_mrkup.add("🔥Архетип дня")
    daily_bonus_mrkup.add("👈Обратно")
    titles_daily_bonus = get_titles_from_kb(daily_bonus_mrkup)

    admin_mrkup = types.InlineKeyboardMarkup()
    admin_mrkup.add(types.InlineKeyboardButton(text='Пользователей всего', callback_data='Admin_Users_Total'))
    admin_mrkup.add(types.InlineKeyboardButton(text='Пользователей за сегодня', callback_data='Admin_Users_For_TODAY'))
    admin_mrkup.add(types.InlineKeyboardButton(text='Рассылка', callback_data='Admin_Send_Messages'))

    back_admin_mrkup = types.InlineKeyboardMarkup()
    back_admin_mrkup.add(types.InlineKeyboardButton(text='⬅️ В меню админа', callback_data='Admin_BACK'))

    @staticmethod
    def generate_send_msgs_step(sending_type: str) -> types.InlineKeyboardMarkup:
        send_messages_step_mrkup = types.InlineKeyboardMarkup()
        send_messages_step_mrkup.add(types.InlineKeyboardButton(text='Первая ступень', callback_data=f'Sending?Step=0&type={sending_type}'),
                                     types.InlineKeyboardButton(text='Вторая ступень', callback_data=f'Sending?Step=1&type={sending_type}'))
        send_messages_step_mrkup.add(types.InlineKeyboardButton(text='Третья ступень', callback_data=f'Sending?Step=2&type={sending_type}'),
                                     types.InlineKeyboardButton(text='Четвёртая ступень', callback_data=f'Sending?Step=3&type={sending_type}'))
        send_messages_step_mrkup.add(types.InlineKeyboardButton(text='Отправить всем', callback_data=f'Sending?Step=ALL&type={sending_type}'))
        send_messages_step_mrkup.add(types.InlineKeyboardButton(text='⬅️ В меню админа', callback_data='Admin_BACK'))
        return send_messages_step_mrkup

    back_to_steps = types.InlineKeyboardMarkup()
    back_to_steps.add(types.InlineKeyboardButton(text='⬅️ Назад', callback_data='Admin_Send_Messages'))

    cancel_sending = types.InlineKeyboardMarkup()
    cancel_sending.add(types.InlineKeyboardButton(text='Отмена!', callback_data='Cancel_Getting_Msg_For_Sending'))

    to_our_account_mrkup = types.InlineKeyboardMarkup()
    to_our_account_mrkup.add(types.InlineKeyboardButton("🙏 Получить бесплатную диагностику", url="https://t.me/Arhetype_Mentor"))
    to_menu_markup = ReplyKeyboardMarkup(resize_keyboard=True)
    to_menu_markup.add("👈Обратно")
