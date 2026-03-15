"""
👤 Личный кабинет
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from datetime import datetime

import database as db
from keyboards import cabinet_kb

router = Router()


@router.message(F.text == "👤 Кабинет")
async def cabinet(msg: Message):
    user_id = msg.from_user.id
    user = db.get_user(user_id)
    if not user:
        db.upsert_user(user_id, msg.from_user.username or "", msg.from_user.full_name)
        user = db.get_user(user_id)

    has_sub = db.has_active_subscription(user_id)

    # Подписка
    if has_sub and user["sub_until"]:
        until = datetime.fromisoformat(user["sub_until"])
        days_left = (until - datetime.now()).days
        sub_text = (
            f"✅ <b>Активна</b> — план «{user['sub_plan'] or '—'}»\n"
            f"   Истекает: {until.strftime('%d.%m.%Y')} ({days_left} дн.)"
        )
    else:
        sub_text = "❌ Нет активной подписки"

    # Дата регистрации
    joined = datetime.fromisoformat(user["joined_at"]).strftime("%d.%m.%Y")

    await msg.answer(
        f"👤 <b>Личный кабинет</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Имя: {user['full_name']}\n"
        f"📅 С нами с: {joined}\n\n"
        f"💎 <b>Подписка:</b>\n{sub_text}",
        parse_mode="HTML",
        reply_markup=cabinet_kb(has_sub),
    )


@router.callback_query(F.data == "history")
async def purchase_history(call: CallbackQuery):
    from database import get_conn
    user_id = call.from_user.id

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT p.*, m.title FROM purchases p
            LEFT JOIN movies m ON p.movie_id = m.id
            WHERE p.user_id = ? AND p.status = 'confirmed'
            ORDER BY p.created_at DESC LIMIT 10
        """, (user_id,)).fetchall()

    if not rows:
        await call.message.answer("📜 История покупок пуста.")
        await call.answer()
        return

    lines = ["📜 <b>История покупок</b>\n"]
    for r in rows:
        date = r["created_at"][:10]
        lines.append(
            f"🎬 <b>{r['title'] or '?'}</b>\n"
            f"   {date} · {r['payment_type']} · {r['amount']} {r['currency']}"
        )

    await call.message.answer("\n\n".join(lines), parse_mode="HTML")
    await call.answer()
