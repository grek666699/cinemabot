"""
⌨️ Клавиатуры бота
"""

from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ─── ГЛАВНОЕ МЕНЮ ──────────────────────────────────────────

def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎬 Каталог"), KeyboardButton(text="💎 Подписка")],
            [KeyboardButton(text="👤 Кабинет"), KeyboardButton(text="ℹ️ О сервисе")],
        ],
        resize_keyboard=True,
    )


# ─── КАТАЛОГ ───────────────────────────────────────────────

def catalog_menu(genres: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎞 Все фильмы", callback_data="cat:all:0")
    for genre in genres:
        builder.button(text=f"🏷 {genre}", callback_data=f"cat:genre:{genre}:0")
    builder.adjust(2)
    return builder.as_markup()


def movies_list(movies, genre="all", offset=0, total=0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in movies:
        stars = "⭐" if not m["is_free"] else "🆓"
        builder.button(
            text=f"{stars} {m['title']} ({m['year']}) {m['rating']}★",
            callback_data=f"movie:{m['id']}"
        )
    builder.adjust(1)

    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"cat:{genre}:{offset-10}"))
    if offset + 10 < total:
        nav.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"cat:{genre}:{offset+10}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="🏠 Меню", callback_data="back_main"))
    return builder.as_markup()


def movie_detail(movie_id: int, has_access: bool, is_free: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_free or has_access:
        builder.button(text="▶️ Смотреть", callback_data=f"watch:{movie_id}")
    else:
        builder.button(text="⭐ Купить за Stars", callback_data=f"buy_stars:{movie_id}")
        builder.button(text="💎 Купить за крипту", callback_data=f"buy_crypto:{movie_id}")
        builder.button(text="♾ Оформить подписку", callback_data="go_sub")
    builder.button(text="◀️ К каталогу", callback_data="cat:all:0")
    builder.adjust(1)
    return builder.as_markup()


# ─── ПОДПИСКА ──────────────────────────────────────────────

def subscription_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Месяц", callback_data="sub:month")
    builder.button(text="🗓 Год  (-40%)", callback_data="sub:year")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🏠 Назад", callback_data="back_main"))
    return builder.as_markup()


def sub_payment_method(plan: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Telegram Stars", callback_data=f"subpay:stars:{plan}")
    builder.button(text="💎 TON",            callback_data=f"subpay:ton:{plan}")
    builder.button(text="💵 USDT",           callback_data=f"subpay:usdt:{plan}")
    builder.button(text="◀️ Назад",          callback_data="go_sub")
    builder.adjust(1)
    return builder.as_markup()


# ─── КРИПТО ОПЛАТА ─────────────────────────────────────────

def crypto_payment_kb(payment_id: int, currency: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Я оплатил — отправить хэш", callback_data=f"txhash:{payment_id}:{currency}")
    builder.button(text="❌ Отмена", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()


def confirm_tx_kb(payment_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"admin_confirm:{payment_id}")
    builder.button(text="❌ Отклонить",  callback_data=f"admin_reject:{payment_id}")
    builder.adjust(2)
    return builder.as_markup()


# ─── ЛИЧНЫЙ КАБИНЕТ ────────────────────────────────────────

def cabinet_kb(has_sub: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not has_sub:
        builder.button(text="💎 Оформить подписку", callback_data="go_sub")
    builder.button(text="📜 История покупок", callback_data="history")
    builder.button(text="🆘 Поддержка",        callback_data="support")
    builder.adjust(1)
    return builder.as_markup()
