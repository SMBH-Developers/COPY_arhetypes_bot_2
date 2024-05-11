from dataclasses import dataclass, field
from string import Template

from aiogram import types, Bot
from aiogram.utils import markdown as m



@dataclass
class SendingData:
    uid: str
    text: str | Template
    url: str
    btn_title: str
    photo: str | None = None

    kb: types.InlineKeyboardMarkup = field(init=False)
    count: int = field(init=False)

    async def get_text(self, bot: Bot, user_id: int, name: str = None):
        if isinstance(self.text, str):
            return self.text
        else:
            if name is None:
                chat_member = await bot.get_chat_member(user_id, user_id)
                name = chat_member.user.first_name
            name = m.quote_html(name)
            return self.text.substitute(name=name)

    def __post_init__(self):
        self.kb = types.InlineKeyboardMarkup()
        self.kb.add(types.InlineKeyboardButton(self.btn_title, url=self.url))
        self.count = 0


bf_sending = SendingData("sending_4_april",
                         Template(f'КАК ОБРЕСТИ БОГАТСТВО ⬇️\nУ меня есть  Лекарство 💊 от бедности, я нашла способ помочь каждому человеку определить его сильные стороны в заработке денег с помощью нумерологии 💫\n\nПишите мне в личные сообщение слово " Богатство " \n➡️  @soulful_mentorship\nСегодня у Вас старт новой жизни 💸'),
                         url="https://t.me/soulful_mentorship",
                         btn_title="Изменить жизнь",
                         photo='photos/arhetype_sending.png'
                         )
