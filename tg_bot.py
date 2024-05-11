import asyncio
import re


from aiogram import Bot, Dispatcher
from aiogram import types, executor, exceptions
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import markdown

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from pathlib import Path
from datetime import datetime, timedelta

from conf import TG_TOKEN, ADMIN_IDS
from database import Database
from texts import Texts, MenuItem
from markups import Markups
from constants import *

from bf_texts import bf_sending, SendingData

class MyStates(StatesGroup):
    get_birthdate = State()
    get_sex = State()
    get_birthplace = State()
    admin_send_msgs = State()


bot = Bot(TG_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

db = Database()
daily_arhtypes = \
    [
        Path('photos/daily_arh_types/arh_type0.PNG'),
        Path('photos/daily_arh_types/arh_type1.PNG'),
        Path('photos/daily_arh_types/arh_type2.PNG'),
        Path('photos/daily_arh_types/arh_type3.PNG'),
        Path('photos/daily_arh_types/arh_type4.PNG')
    ]



@dp.message_handler(commands=['start'], state='*')
async def start_message(message: types.Message, state: FSMContext):
    await state.finish()
    if not db.check_if_user_exists(message.from_user.id):
        photo_path = PHOTOS_DIR / 'first_photo.png'
        db.registrate_user(message.from_user.id)
        await message.answer_photo(photo=types.InputFile(photo_path), caption=Texts.start_text, reply_markup=Markups.start_menu_mrkup)
    else:
        photo_path = PHOTOS_DIR / 'first_photo.png'
        await message.answer_photo(photo=types.InputFile(photo_path), caption=Texts.start_text, reply_markup=Markups.start_menu_mrkup)


@dp.message_handler(lambda message: message.from_user.id in ADMIN_IDS, state='*', commands=['admin'])
@logger.catch
async def admin_menu(message: types.Message, state: FSMContext) -> None:
    await bot.send_message(message.chat.id, text='Выберите действие', reply_markup=Markups.admin_mrkup)


@dp.message_handler(lambda message: message.text == '👈Обратно', state='*')
async def back_to_start_menu(message: types.Message, state: FSMContext):
    await state.finish()
    photo_path = PHOTOS_DIR / 'first_photo.png'

    await message.answer_photo(photo=types.InputFile(photo_path), caption=Texts.start_text, reply_markup=Markups.start_menu_mrkup)


@dp.callback_query_handler(lambda call: call.from_user.id in ADMIN_IDS and call.data.startswith('Admin'), state='*')
@logger.catch
async def admin_calls(call: types.CallbackQuery, state: FSMContext) -> None:
    action = '_'.join(call.data.split('_')[1:])
    if action == 'Users_Total':
        await call.message.edit_text(text=f'Пользователей всего: {db.get_all_users_count()}',
                                     reply_markup=Markups.back_admin_mrkup)

    elif action == 'Users_For_TODAY':
        await call.message.edit_text(text=f'Пользователей за сегодня: {db.get_today_users_count()}',
                                     reply_markup=Markups.back_admin_mrkup)

    elif action == 'BACK':
        await call.message.edit_text(text='Выберите действие', reply_markup=Markups.admin_mrkup)

    elif action == 'Send_Messages':  # Рассылка по любым
        await call.message.edit_text('Выберите ступень для рассылки:',
                                     reply_markup=Markups.generate_send_msgs_step('any'))


def get_value_of_arg(arg: str) -> str:
    """Получает значение из аргумент=значение"""
    return arg.split('=')[-1]


@dp.callback_query_handler(lambda call: call.data.startswith('Sending?') and call.from_user.id in ADMIN_IDS, state='*')
@logger.catch
async def choose_step(call: types.CallbackQuery, state: FSMContext) -> None:
    # Sending?Step={step_num}&type={sending_type}
    step, sending_type = [get_value_of_arg(arg) for arg in call.data.split('?')[1].split('&')]

    type_text = {'any': 'любым из ступени', 'special': 'только тем, кто не перешёл в автоответчик'}[sending_type]
    step_text = {'ALL': 'всем', '0': 'первая', '1': 'второая', '2': 'третья', '3': 'четвёртая'}[step]
    await call.message.edit_text(f'Тип рассылки: {type_text}\nСтупень: {step_text}\nНайдено пользователей:'
                                 f'{db.get_count_users_with_step(step) if step != "ALL" else db.get_count_all_users()} '
                                 f'(все с данной ступенью, при подсчёте нет проверки на существование в БД автоответчика)\n'
                                 f'Введите текст для рассылки:',
                                 reply_markup=Markups.back_admin_mrkup)
    await state.set_data({'step': step, 'sending_type': sending_type})
    await state.set_state(MyStates.admin_send_msgs.state)


@dp.callback_query_handler(state=MyStates.admin_send_msgs)
async def cancel_getting(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    if call.data == 'Cancel_Getting_Msg_For_Sending':
        await call.message.edit_text(text='Выбор рассылки отменён!', reply_markup=Markups.back_admin_mrkup)


@dp.message_handler(state=MyStates.admin_send_msgs)
@logger.catch
async def get_message_to_send(message: types.Message, state: FSMContext):
    state_data = (await state.get_data())
    step = state_data.get('step')
    sending_type = state_data.get('sending_type')
    await state.finish()
    try:
        assert step is not None and sending_type is not None
        if step == 'ALL':
            to_who_to_send = [int(user[0]) for user in db.get_all_users()]
        else:
            to_who_to_send = [int(user[0]) for user in db.get_users_with_step(int(step))]
    except AssertionError:
        await bot.send_message(message.chat.id,
                               'Произошла ошибка при получении списка пользователей, которым рассылать.',
                               reply_markup=Markups.back_admin_mrkup)
    else:
        asyncio.create_task(sending_to_people(message.text, to_who_to_send, sending_type, message.chat.id))


@logger.catch
async def sending_to_people(text: str, users: list[int], sending_type: str, admin_chat) -> None:
    length_users = len(users)
    msg_for_admin = await bot.send_message(admin_chat, f'Рассылка началась 0/{length_users}')
    message_id_to_edit = msg_for_admin.message_id
    chat_id_where_edit = msg_for_admin.chat.id
    main_counter = 0
    for enum_user, user in enumerate(users, start=1):
        try:
            if enum_user % 10 == 0:
                await bot.edit_message_text(text=f'Рассылка {enum_user}/{length_users}',
                                            chat_id=chat_id_where_edit, message_id=message_id_to_edit)
            await bot.send_message(user, text)
            db.update_step(user)
            logger.info(f'Updated {user} step+=1')
            await asyncio.sleep(0.1)
            main_counter += 1
        except exceptions.BotBlocked:
            logger.info(f'{user} заблочил бота. Удалён из БД')
        except Exception as ex:
            logger.error(f'Got error when tried to send to {user}. Error is {ex}')
    await bot.send_message(chat_id_where_edit, f'Рассылка окончена!\nКол-во пользователей: {length_users}\n'
                                               f'Получили: {main_counter}\nНе получили: {length_users - main_counter}')


async def answer_menu_item(message: types.Message, menu_item: MenuItem):
    text_to_send = None
    if menu_item.text and len(menu_item.text) > 1024:
        text_to_send = menu_item.text
        menu_item.text = None

    if isinstance(menu_item.photo, Path):
        with menu_item.photo.open('rb') as item_photo:
            msg = await message.answer_photo(item_photo, caption=menu_item.text, reply_markup=Markups.to_menu_markup)
        menu_item.photo = msg.photo[-1].file_id
    else:
        await message.answer_photo(menu_item.photo, caption=menu_item.text, reply_markup=Markups.to_menu_markup)
    if text_to_send:
        await message.answer(text_to_send, reply_markup=Markups.to_menu_markup)


@dp.message_handler(lambda message: message.text in Markups.titles_start_menu_mrkup, state='*')
async def start_menu(message: types.Message, state: FSMContext):
    if message.text == '📋Информационный отдел':
        await message.answer(Texts.info_menu_text, reply_markup=Markups.info_menu_mrkup)
    elif message.text == '👀Рассчитайте свой архетип':
        await message.answer(f'У человека с рождения обычно активированы лишь 1-3 архетипа личности🥲, по модели которых он и живет. Предлагаю вам {markdown.hbold("узнать свои активные")} и "спящие" архетипы, чтобы {markdown.hbold("активировать весь потенциал")}, данный  Вам с рождения. 🤩 Если готовы просто напишите эксперту - духовному наставнику @Arhetype_mentorr дату рождения в формате ДД.ММ.ГГГГ. Она проведет диагностику и даст рекомендации. Для вас это {markdown.hbold("бесплатно")}!', parse_mode='html')
        user_date = db.get_user_birthdate(message.from_user.id)
        if True or user_date is None:  # TODO: убрать True
            await state.set_state(MyStates.get_birthdate.state)
    elif message.text == '🎁Ежедневный подарок':
        await message.answer(Texts.daily_bonus_menu_text, reply_markup=Markups.daily_bonus_mrkup)


@dp.message_handler(lambda message: message.text in Texts.info_items, state="*")
async def info_menu_answer(message: types.Message, state: FSMContext):
    info_item = Texts.info_items[message.text]
    await answer_menu_item(message, info_item)


@dp.message_handler(lambda message: message.text in Markups.titles_daily_bonus, state='*')
async def calls_from_daily_bonus_menu(message: types.Message, state: FSMContext):
    if message.text in Texts.dict_check_lists:
        check_list = Texts.dict_check_lists[message.text]
        if isinstance(check_list.file, Path):
            with check_list.file.open('rb') as check_list_file:
                bot_msg = await message.answer_document(check_list_file, caption=check_list.text, reply_markup=Markups.to_menu_markup)
            check_list.file = bot_msg.document.file_id
        else:
            await message.answer_document(check_list.file, caption=check_list.text, reply_markup=Markups.to_menu_markup)

    elif message.text == '💫Узнать архетип дня':
        step = db.get_daily_arh_step(message.from_user.id)  # 0 to 4
        await message.answer(Texts.daily_arch_types[step], reply_markup=Markups.to_menu_markup)

    elif message.text == '📚 Подборка книг об архетипах':
        await answer_menu_item(message, Texts.books_recommendation)

    elif message.text == '🔥Архетип дня':
        await send_daily_arhtype(message.from_user.id)


async def send_daily_arhtype(user_id):
    user_step = db.get_daily_arh_step(user_id)
    daily_arh_type_photo = daily_arhtypes[int(user_step)]
    now_time = datetime.now()
    tomorrow_time = (now_time + timedelta(days=1))
    necessary_time = datetime(year=tomorrow_time.year, month=tomorrow_time.month, day=tomorrow_time.day, hour=0, minute=0, second=0)
    seconds_left = (necessary_time - now_time).total_seconds()
    hours_left = round(seconds_left / 60 // 60)
    minutes_left = round(seconds_left // 60 % 60)
    text = f"⏳До обновления архетипа дня осталось: {hours_left} часа {minutes_left} минут(ы)."

    if isinstance(daily_arh_type_photo, str):
        await bot.send_photo(user_id, photo=daily_arh_type_photo, caption=text, reply_markup=Markups.to_menu_markup)
    else:
        with daily_arh_type_photo.open("rb") as f:
            msg = await bot.send_photo(user_id, photo=f, caption=text, reply_markup=Markups.to_menu_markup)
            daily_arhtypes[user_step] = msg.photo[-1].file_id


async def send_arh_type(user_id: int, birthdate: str):
    # month = int(birthdate.split('.')[1])-1
    # arch_type = Texts.arch_types[month]
    main_text = 'У вас сейчас активирован архетип "Маг". Это когда человек становится катализатором изменений. Своими мыслями вы способны менять как свои реальности, так и жизни людей вокруг вас. Вы на глубинном уровне понимаете, как работает сознание, поэтому способны оказывать на окружающих влияние. \n\nСильная сторона: У магов часто возникают мечты, которые другие люди считают несбыточными, но суть магии заключается в том, чтобы обладать видением и уметь претворить это видение в жизнь.\n\nСлабые стороны: Теневой Маг — это еще и часть нас, способная негативными мыслями и действиями сделать себя или других больными.\n\nТаким образом, Магу предоставляется выбор — либо он имеет дело с реальностью, осваивая все новые способы работы с ней, либо он погружается в иллюзорные реальности, чтобы не получать угроз и задач от существующего мира. Магу очень важно проявляться в этом мире, иначе он закрывается от себя и от всех((\n\nУ человека, как правило, 3 архетипа находятся в активном состоянии, и 3 в пассивном, которые также можно пробудить и использовать в жизни. Об остальных своих аретипах вы можете более подробно узнать на бесплатной консультации у эксперта.'
    await bot.send_message(user_id, main_text)
    late_text = "Спасибо за использование моей методики самопознания! 💫\n\n\n✒️Только сегодня я готова бесплатно подробно разобрать Ваш архетип. Чтобы получить подробную бесплатную диагностику Вашего архетипа — напишите мне Вашу дату рождения в личные сообщения — @Arhetype_mentor\n\n<b>‼️Количество бесплатных мест ограничено‼️</b>"
    await asyncio.create_task(send_late_thanks(user_id, late_text))


async def send_late_thanks(user_id: int, text: str):
    if not db.check_if_push_set(user_id):
        db.set_or_unset_push(user_id, 1)
        await asyncio.sleep(2)  # TODO: 133
        await bot.send_message(user_id, text, parse_mode='html', reply_markup=Markups.to_our_account_mrkup)
        db.set_or_unset_push(user_id, 0)


@dp.message_handler(state=MyStates.get_birthdate)
async def get_user_birthdate(message: types.Message, state: FSMContext):
    if re.fullmatch(r'\d{1,2}\.\d{1,2}\.\d{4}', message.text):
        day, month, year = message.text.split('.')
        if 0 < int(day) < 32 and 0 < int(month) < 13 and int(year) < 2023:
            db.registrate_user_birthdate(message.from_user.id, message.text)
            await state.set_state(MyStates.get_sex.state)
            await message.answer("Напишите Ваш пол в формате М\Ж⬇️", reply_markup=Markups.sex_mrkup)
        else:
            await message.answer('Некорректная дата.\n'
                                 '🙏Для расчёта архетипа, пожалуйста, напишите дату рождения в форме дд.мм.гггг',
                                 reply_markup=Markups.to_menu_markup)
    else:
        await message.answer('Неверный формат.\n'
                             '🙏Для расчёта архетипа, пожалуйста, напишите дату рождения в форме дд.мм.гггг',
                             reply_markup=Markups.to_menu_markup)


@dp.message_handler(lambda message: message.text in ('М', 'Ж'), state=MyStates.get_sex)
async def get_user_sex(message: types.Message, state: FSMContext):
    await message.answer('Напишите название города в котором Вы родились⬇️', reply_markup=Markups.to_menu_markup)
    await state.set_state(MyStates.get_birthplace.state)


@dp.message_handler(state=MyStates.get_birthplace)
async def get_user_birth_place(message: types.Message, state: FSMContext):
    """Получаем место рождения пользователя и заканчиваем данный разбор"""
    if len(message.text) > 512:  # Чтобы не было много текста в БД, ограничиваем хотя бы в 512
        await message.answer("Слишком длинный текст.\nПожалуйста, ведите своё место рождения короче.")
    else:
        db.update_user_birth_place(message.from_user.id, message.text)
        await state.finish()
        await message.answer('🪄Обрабатываю информацию...', reply_markup=Markups.to_menu_markup)
        await asyncio.sleep(0.5)  # TODO: 3.5
        asyncio.create_task(send_arh_type(message.chat.id, db.get_user_birthdate(message.from_user.id)))


async def update_db_advices_step_func():
    db.update_daily_arh_step()


async def sending_messages_2h():
    while True:
        await asyncio.sleep(7)
        text_for_2h_autosending = f"{markdown.hbold('Архетип')} – это понятие, которое обозначает образы, символы и картинки в коллективном бессознательном🧠. Считается, что они существуют в глубинах нашего разума с рождения и передаются от предков.\n\n 🤩 Не упустите возможность узнать свои активные архетипы! Сегодня для вас бесплатная консультация эксперта. Просто напишите мне 👉{markdown.hbold('@Arhetype_mentorr')} ваше имя и дату рождения!"
        users_for_2h_autosending = db.get_users_2h_autosending()
        mrkup = types.InlineKeyboardMarkup()
        mrkup.add(types.InlineKeyboardButton('⭐️ Рассчитать свой архетип ⭐️', url=f'https://t.me/Arhetype_mentorr'))
        for user in users_for_2h_autosending:
            try:
                photo_path = PHOTOS_DIR / 'sending_photos/2_hours.png'
                await bot.send_photo(user, photo=types.InputFile(photo_path), caption=text_for_2h_autosending,
                                    reply_markup=mrkup, parse_mode='html')
                logger.info(f'ID: {user}. Got 2h_autosending')
                db.mark_got_2h_autosending(user)
                await asyncio.sleep(0.07)
            except exceptions.BotBlocked:
                logger.exception(f'ID: {user}. DELETED')
                db.delete_user(user)
            except exceptions.UserDeactivated:
                logger.exception(f'ID: {user}. DELETED')
                db.delete_user(user)
            except Exception as ex:
                logger.error(f'got error: {ex}')


async def sending_messages_24h():
    while True:
        await asyncio.sleep(7)
        text_for_24h_autosending = f"А вы знали, что понятие архетипа в психологии обозначает базовые стратегии {markdown.hbold('реализации целей, задач,')} универсальные ролевые модели. 😎 Зная и умея применять архетипы, можно:\nлучше понять себя;\nпонять окружающих;\nгармонично управлять состоянием, эмоциями;\nзадействовать внутренние ресурсы.\n\nПолная расшифровка индивида благодаря архетипам  {markdown.hbold('порядок в жизни,')} порядок в жизни, в голове, поможет создать свой неповторимый стиль💃.\n\nСегодня {markdown.hbold('осталось всего 4 места')} на бесплатную диагностику и расшифровку всех ваших архетипов.{markdown.hbold('Записать вас?')}\n\nДля этого нужно лишь ваше имя и дата рождения в формате чч.мм.гггг. Просто пришлите мне их в личку 👉 @Arhetype_mentorr"
        users_for_24h_autosending = db.get_users_24h_autosending()
        mrkup = types.InlineKeyboardMarkup()
        mrkup.add(types.InlineKeyboardButton('🔥 Бесплатная консультация🔥', url=f'https://t.me/Arhetype_mentorr'))
        for user in users_for_24h_autosending:
            try:
                photo_path = PHOTOS_DIR / 'sending_photos/24_hours.png'
                await bot.send_photo(user, photo=types.InputFile(photo_path), caption=text_for_24h_autosending,
                                    reply_markup=mrkup, parse_mode='html')
                logger.info(f'ID: {user}. Got 24h_autosending')
                db.mark_got_24h_autosending(user)
                await asyncio.sleep(0.07)
            except exceptions.BotBlocked:
                logger.exception(f'ID: {user}. DELETED')
                db.delete_user(user)
            except exceptions.UserDeactivated:
                logger.exception(f'ID: {user}. DELETED')
                db.delete_user(user)
            except Exception as ex:
                logger.error(f'got error: {ex}')


async def sending_messages_48h():
    while True:
        await asyncio.sleep(7)
        text_for_48h_autosending = f"Бизнесмены, блогеры и артисты создают свои страницы в социальных сетях, онлайн продукты и свой стиль исходя из своего архетипа😉.\n\nБлагодаря знанию архетипов можно добиться:\n\n1. Раскрытия потенциала, найти свое место в мире.\n2. Вовлечь аудиторию в проекты.\n3. Осознать глубинные смыслы, таланты, сильные стороны.\nПри желании можно построить блестящую карьеру, создать уникальное позиционирование.\n\nЕсли Вы искали свою {markdown.hbold('уникальность и изюминку')} - напишите в личку нашему эксперту @Arhetype_mentorr и она распишет для вас полную расшифровку по вашим данным рождения."
        users_for_48h_autosending = db.get_users_48h_autosending()
        mrkup = types.InlineKeyboardMarkup()
        mrkup.add(types.InlineKeyboardButton('Бесплатная диагностика архетипов', url=f'https://t.me/Arhetype_mentorr'))
        for user in users_for_48h_autosending:
            try:
                photo_path = PHOTOS_DIR / 'sending_photos/48_hours.png'
                await bot.send_photo(user, photo=types.InputFile(photo_path), caption=text_for_48h_autosending,
                                    reply_markup=mrkup, parse_mode='html')
                logger.info(f'ID: {user}. Got 48h_autosending')
                db.mark_got_48h_autosending(user)
                await asyncio.sleep(0.07)
            except exceptions.BotBlocked:
                logger.exception(f'ID: {user}. DELETED')
                db.delete_user(user)
            except exceptions.UserDeactivated:
                logger.exception(f'ID: {user}. DELETED')
                db.delete_user(user)
            except Exception as ex:
                logger.error(f'got error: {ex}')


async def sending_messages_72h():
    while True:
        await asyncio.sleep(7)
        text_for_72h_autosending = f"Сегодня уникальный день, когда принятые решения меняют реальности и улучшают судьбу. И в этот день желающих прийти на консультацию всегда выше) Но своим подписчикам я всегда оставляю 5 мест. {markdown.hbold('Оставить за Вами место?')}\n\n Мы пришли в этот мир, чтобы познавать себя😇. Учиться на ошибках и {markdown.hbold('становится осознаннее, счастливее и изобильнее.')} И именно система познания себя через архетипы считается 🥳 эффективной и результативной🤩. Ею используют все опытные психологи и эксперты. Ведь она показывает наши бессознательные патерны поведения.\n\n Напиши мне @Arhetype_mentorr👈 свое имя и я оставлю для вас место на {markdown.hbold('бесплатную консультацию.')} Не упускай возможность улучшить свою личность и жизнь. Пиши👇"
        users_for_72h_autosending = db.get_users_72h_autosending()
        mrkup = types.InlineKeyboardMarkup()
        mrkup.add(types.InlineKeyboardButton('😎 Получить консультацию 😎', url=f'https://t.me/Arhetype_mentorr'))
        for user in users_for_72h_autosending:
            try:
                photo_path = PHOTOS_DIR / 'sending_photos/72_hours.png'
                await bot.send_photo(user, photo=types.InputFile(photo_path), caption=text_for_72h_autosending,
                                    reply_markup=mrkup, parse_mode='html')
                logger.info(f'ID: {user}. Got 72h_autosending')
                db.mark_got_72h_autosending(user)
                await asyncio.sleep(0.07)
            except exceptions.BotBlocked:
                logger.exception(f'ID: {user}. DELETED')
                db.delete_user(user)
            except exceptions.UserDeactivated:
                logger.exception(f'ID: {user}. DELETED')
                db.delete_user(user)
            except Exception as ex:
                logger.error(f'got error: {ex}')


async def bf_task(id_: int, sending: SendingData, db_func, skip_if_chat_member: bool = False, only_for_chat_member: bool = False):
    try:

        if skip_if_chat_member or only_for_chat_member:
            chat_member = await bot.get_chat_member(-1002059782974, id_)
            if chat_member.is_chat_member() and skip_if_chat_member:
                return 'skip'
            elif not chat_member.is_chat_member() and only_for_chat_member:
                return 'skip'
            name = chat_member.user.first_name
        else:
            name = None

        text = await sending.get_text(bot, id_, name)
        if sending.photo is not None:
            await bot.send_photo(id_, types.InputFile(sending.photo), caption=text, reply_markup=sending.kb,
                                 parse_mode='html')
        elif sending.video is not None:
            await bot.send_video(id_, sending.video, caption=text, reply_markup=sending.kb, parse_mode='html')
        else:
            await bot.send_message(id_, text=text, reply_markup=sending.kb,
                                   parse_mode='html', disable_web_page_preview=True)
        db_func(id_)
        sending.count += 1
        logger.success(f'{id_} sending_{sending.uid} text')

    except (exceptions.BotBlocked, exceptions.UserDeactivated, exceptions.ChatNotFound) as ex:
        logger.error(f'{id_} {ex}')
        db.delete_user(id_)
    # except Exception as e:
    #     logger.error(f'BUG: {e}')
    else:
        return 'success'
    return 'false'


async def sending_newsletter():
    white_day = 4
    now_time = datetime.now()

    if now_time.day > white_day:
        return

    while True:
        await asyncio.sleep(2)
        if now_time.day == white_day and now_time.hour >= 7:
            try:
                tasks = []
                users = [1371617744] + list(db.get_users_for_sending_newsletter())
                print(len(users))
                for user in users:
                    logger.info(f"Пытаюсь отправить сообщение рассылки - {user}")
                    try:
                        _s = bf_sending
                        # if _s.count >= 80000:
                        #     break
                        tasks.append(asyncio.create_task(bf_task(user, _s, db.set_newsletter)))
                        if len(tasks) > 40:
                            print(len(tasks))
                            r = await asyncio.gather(*tasks, return_exceptions=False)
                            await asyncio.wait(tasks)
                            await asyncio.sleep(0.4)
                            logger.info(f"{r.count('success')=}", f"{r.count('false')=}", f"{r.count('skip')=}")
                            tasks.clear()

                    except Exception as ex:
                        logger.error(f'Ошибка в малом блоке sending: {ex}')
                    finally:
                        await asyncio.sleep(0.03)
            except Exception as ex:
                logger.error(f"Ошибка в большом блоке sending - {ex}")
            finally:
                await bot.send_message(1371617744, f"ERROR Рассылка стопнулась.")
                logger.info("Рассылка завершилась")

async def on_startup(_):
    asyncio.create_task(sending_newsletter())
    asyncio.create_task(sending_messages_2h())
    asyncio.create_task(sending_messages_24h())
    asyncio.create_task(sending_messages_48h())
    asyncio.create_task(sending_messages_72h())


def main():
    scheduler = AsyncIOScheduler({'apscheduler.timezone': 'Europe/Moscow'})
    scheduler.add_job(trigger='cron', hour='00', minute='00', func=update_db_advices_step_func)
    scheduler.start()
    executor.start_polling(dp, on_startup=on_startup)


main()
