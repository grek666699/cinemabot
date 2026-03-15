"""
💳 Платежи — покупка фильмов + крипто-инвойсы
Верификация теперь полностью автоматическая через auto_verify.py
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, LabeledPrice, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
from config import WALLETS, RATES, STARS_FILM, CRYPTO_FILM_USD

router = Router()


@router.callback_query(F.data.startswith("buy_stars:"))
async def buy_movie_stars(call: CallbackQuery):
    movie_id = int(call.data.split(":")[1])
    m = db.get_movie(movie_id)
    if not m:
        await call.answer("Фильм не найден", show_alert=True)
        return
    price = m["price_stars"] or STARS_FILM
    await call.message.answer_invoice(
        title=m["title"],
        description=(m["description"][:100] + "...") if len(m["description"]) > 100 else m["description"],
        payload=f"movie:{movie_id}:{call.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label=m["title"], amount=price)],
    )
    await call.answer()


@router.callback_query(F.data.startswith("buy_crypto:"))
async def buy_movie_crypto(call: CallbackQuery):
    movie_id = int(call.data.split(":")[1])
    m = db.get_movie(movie_id)
    if not m:
        await call.answer("Фильм не найден", show_alert=True)
        return
    price_usd   = m["price_usd"] or CRYPTO_FILM_USD
    ton_amount  = round(price_usd / RATES["TON"],  4)
    usdt_amount = round(price_usd / RATES["USDT"], 2)
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💎 TON — {ton_amount} TON",    callback_data=f"filmcrypto:ton:{movie_id}")
    builder.button(text=f"💵 USDT — {usdt_amount} USDT", callback_data=f"filmcrypto:usdt:{movie_id}")
    builder.button(text="◀️ Назад",                       callback_data=f"movie:{movie_id}")
    builder.adjust(1)
    await call.message.edit_text(
        f"💳 <b>Покупка: {m['title']}</b>\n\nЦена: <b>${price_usd}</b>\n\nВыбери криптовалюту 👇",
        parse_mode="HTML", reply_markup=builder.as_markup(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("filmcrypto:"))
async def film_crypto_invoice(call: CallbackQuery):
    _, currency_raw, movie_id_str = call.data.split(":")
    currency = currency_raw.upper()
    movie_id = int(movie_id_str)
    m = db.get_movie(movie_id)
    if not m:
        await call.answer("Фильм не найден", show_alert=True)
        return
    price_usd  = m["price_usd"] or CRYPTO_FILM_USD
    amount     = round(price_usd / RATES[currency], 6 if currency == "TON" else 2)
    wallet     = WALLETS[currency]
    payment_id = db.create_crypto_payment(call.from_user.id, f"movie_{movie_id}", currency, amount, wallet)
    network    = "TON Network" if currency == "TON" else "TRC-20 Network"
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Проверить оплату", callback_data=f"checkpay:{payment_id}")
    builder.button(text="◀️ Назад",            callback_data=f"movie:{movie_id}")
    builder.adjust(1)
    await call.message.answer(
        f"💳 <b>Оплата фильма</b>\n\n🎬 {m['title']}\n\n"
        f"Переведи <b>точную сумму</b>:\n\n"
        f"<code>{amount} {currency}</code>\n\n"
        f"Кошелёк ({network}):\n<code>{wallet}</code>\n\n"
        f"🤖 <b>Оплата определяется автоматически</b> — за 1–2 минуты\n"
        f"🔖 ID платежа: <code>{payment_id}</code>",
        parse_mode="HTML", reply_markup=builder.as_markup(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("checkpay:"))
async def manual_check(call: CallbackQuery):
    payment_id = int(call.data.split(":")[1])
    from database import get_conn
    with get_conn() as conn:
        p = conn.execute("SELECT * FROM crypto_payments WHERE id=?", (payment_id,)).fetchone()
    if not p:
        await call.answer("Платёж не найден", show_alert=True); return
    if p["status"] == "confirmed":
        await call.answer("✅ Уже подтверждён!", show_alert=True); return
    if p["status"] == "expired":
        await call.answer("⏰ Просрочен. Обратитесь в поддержку.", show_alert=True); return
    await call.answer("🔍 Проверяю...", show_alert=False)
    from auto_verify import find_ton_payment, find_usdt_payment, activate_access
    from datetime import datetime
    currency = p["currency"]
    tx = None
    if currency == "TON":
        tx = await find_ton_payment(float(p["amount"]), WALLETS["TON"], datetime.fromisoformat(p["created_at"]))
    elif currency == "USDT":
        tx = await find_usdt_payment(float(p["amount"]), WALLETS["USDT"], datetime.fromisoformat(p["created_at"]))
    if tx:
        await activate_access(call.bot, dict(p), tx)
        await call.message.answer("✅ <b>Оплата подтверждена!</b>", parse_mode="HTML")
    else:
        await call.message.answer(
            "⏳ <b>Транзакция ещё не найдена</b>\n\nПодожди 2–3 минуты — проверка идёт автоматически.",
            parse_mode="HTML",
        )


@router.pre_checkout_query()
async def pre_checkout(query):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(msg: Message):
    from config import SUBSCRIPTION_PLANS
    parts   = msg.successful_payment.invoice_payload.split(":")
    user_id = msg.from_user.id
    if parts[0] == "sub":
        plan = SUBSCRIPTION_PLANS[parts[1]]
        ends = db.set_subscription(user_id, parts[1], plan["days"])
        await msg.answer(
            f"✅ <b>Подписка активирована!</b>\n\nДо: <b>{ends.strftime('%d.%m.%Y')}</b>\n\nПриятного просмотра! 🍿",
            parse_mode="HTML",
        )
    elif parts[0] == "movie":
        movie_id    = int(parts[1])
        purchase_id = db.create_purchase(user_id, movie_id, "stars", msg.successful_payment.total_amount, "XTR")
        db.confirm_purchase(purchase_id, "stars_payment")
        m = db.get_movie(movie_id)
        await msg.answer(
            f"✅ <b>Оплачено!</b>\n\n🎬 <b>{m['title']}</b> доступен. Найди в каталоге 🎬",
            parse_mode="HTML",
        )
