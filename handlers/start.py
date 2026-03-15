"""
🚀 Старт и главное меню
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

import database as db
from keyboards import main_menu
from config import SUPPORT_USERNAME

router = Router()


@router.message(CommandStart())
async def cmd_start(msg: Message):
    db.init_db()
    db.upsert_user(msg.from_user.id, msg.from_user.username or "", msg.from_user.full_name)

    await msg.answer(
        f"🎬 <b>Добро пожаловать в CinemaBot!</b>\n\n"
        f"Здесь тебя ждут лучшие фильмы в HD качестве.\n\n"
        f"<b>Варианты доступа:</b>\n"
        f"♾ <b>Подписка</b> — безлимитный доступ ко всем фильмам\n"
        f"🎞 <b>Разовый просмотр</b> — покупка отдельного фильма\n"
        f"🆓 <b>Бесплатные</b> — часть фильмов доступна без оплаты\n\n"
        f"Выбери раздел в меню 👇",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


@router.message(F.text == "ℹ️ О сервисе")
async def about(msg: Message):
    await msg.answer(
        "ℹ️ <b>О CinemaBot</b>\n\n"
        "🎬 Онлайн-кинотеатр прямо в Telegram\n"
        "🔐 Безопасная оплата через Stars и криптовалюту\n"
        "📱 Смотри в любом месте без рекламы\n"
        "🆕 Новинки каждую неделю\n\n"
        f"💬 Поддержка: {SUPPORT_USERNAME}",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery):
    await call.message.answer("Главное меню 👇", reply_markup=main_menu())
    await call.answer()


@router.callback_query(F.data == "support")
async def support(call: CallbackQuery):
    await call.message.answer(
        f"🆘 <b>Поддержка</b>\n\nПишите сюда: {SUPPORT_USERNAME}\n\n"
        "При обращении укажите:\n"
        "• Вашу проблему\n"
        "• Скриншот если нужно\n"
        "• ID транзакции (для платёжных вопросов)",
        parse_mode="HTML",
    )
    await call.answer()
