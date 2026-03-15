"""
💎 Подписка
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery

import database as db
from keyboards import subscription_menu, sub_payment_method, crypto_payment_kb
from config import SUBSCRIPTION_PLANS, WALLETS, RATES

router = Router()


async def show_subscription(msg: Message):
    user_id = msg.from_user.id if msg.from_user else 0
    has_sub = db.has_active_subscription(user_id)
    user = db.get_user(user_id)

    sub_info = ""
    if has_sub and user and user["sub_until"]:
        from datetime import datetime
        until = datetime.fromisoformat(user["sub_until"])
        days_left = (until - datetime.now()).days
        sub_info = f"\n\n✅ <b>Подписка активна</b> — ещё {days_left} дн."

    plans_text = ""
    for key, plan in SUBSCRIPTION_PLANS.items():
        badge = f"  <i>{plan.get('badge','')}</i>" if plan.get('badge') else ""
        plans_text += (
            f"\n{plan['emoji']} <b>{plan['name']}</b>{badge}\n"
            f"   ⭐ {plan['stars']} Stars / 💵 ${plan['usd']} USD\n"
        )

    await msg.answer(
        f"💎 <b>Подписка CinemaBot</b>{sub_info}\n\n"
        f"Безлимитный доступ ко всем фильмам и новинкам.\n"
        f"{plans_text}\n"
        "Выбери план 👇",
        parse_mode="HTML",
        reply_markup=subscription_menu(),
    )


@router.message(F.text == "💎 Подписка")
async def sub_menu(msg: Message):
    await show_subscription(msg)


@router.callback_query(F.data.startswith("sub:"))
async def choose_sub_plan(call: CallbackQuery):
    plan_key = call.data.split(":")[1]
    plan = SUBSCRIPTION_PLANS.get(plan_key)
    if not plan:
        await call.answer("Неверный план", show_alert=True)
        return

    badge = f"\n🏷 {plan['badge']}" if plan.get("badge") else ""
    await call.message.edit_text(
        f"{plan['emoji']} <b>Подписка — {plan['name']}</b>{badge}\n\n"
        f"⭐ {plan['stars']} Telegram Stars\n"
        f"💵 ${plan['usd']} в криптовалюте\n\n"
        "Выбери способ оплаты 👇",
        parse_mode="HTML",
        reply_markup=sub_payment_method(plan_key),
    )
    await call.answer()


@router.callback_query(F.data.startswith("subpay:"))
async def process_sub_payment(call: CallbackQuery):
    _, method, plan_key = call.data.split(":")
    plan = SUBSCRIPTION_PLANS.get(plan_key)
    if not plan:
        await call.answer("Ошибка плана", show_alert=True)
        return

    user_id = call.from_user.id

    if method == "stars":
        await call.message.answer_invoice(
            title=f"Подписка {plan['name']}",
            description=f"Безлимитный доступ ко всем фильмам на {plan['days']} дней",
            payload=f"sub:{plan_key}:{user_id}",
            currency="XTR",
            prices=[LabeledPrice(label=f"Подписка {plan['name']}", amount=plan["stars"])],
        )
        await call.answer()

    elif method in ("ton", "usdt"):
        currency = method.upper()
        rate = RATES[currency]
        amount = round(plan["usd"] / rate, 6 if currency == "TON" else 2)
        wallet = WALLETS[currency]

        purpose = f"subscription_{plan_key}"
        payment_id = db.create_crypto_payment(user_id, purpose, currency, amount, wallet)

        network = "TON Network" if currency == "TON" else "TRC-20 Network"
        await call.message.answer(
            f"💎 <b>Оплата подписки — {plan['name']}</b>\n\n"
            f"Переведи точную сумму:\n\n"
            f"<code>{amount} {currency}</code>\n\n"
            f"На кошелёк ({network}):\n"
            f"<code>{wallet}</code>\n\n"
            f"⚠️ <b>Важно:</b>\n"
            f"• Переводи точную сумму\n"
            f"• После оплаты нажми кнопку и пришли хэш транзакции\n"
            f"• Подтверждение занимает до 30 минут\n\n"
            f"🔖 ID платежа: <code>{payment_id}</code>",
            parse_mode="HTML",
            reply_markup=crypto_payment_kb(payment_id, currency),
        )
        await call.answer()


# ─── Telegram Stars Pre-checkout ───────────────────────────

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(msg: Message):
    payload = msg.successful_payment.invoice_payload
    # payload: "sub:month:user_id" или "movie:id:user_id"

    parts = payload.split(":")
    user_id = msg.from_user.id

    if parts[0] == "sub":
        plan_key = parts[1]
        plan = SUBSCRIPTION_PLANS[plan_key]
        ends = db.set_subscription(user_id, plan_key, plan["days"])
        from datetime import datetime
        formatted = ends.strftime("%d.%m.%Y")
        await msg.answer(
            f"✅ <b>Подписка активирована!</b>\n\n"
            f"🎬 Доступ открыт до <b>{formatted}</b>\n"
            f"Приятного просмотра! 🍿",
            parse_mode="HTML",
        )

    elif parts[0] == "movie":
        movie_id = int(parts[1])
        purchase_id = db.create_purchase(
            user_id, movie_id, "stars",
            msg.successful_payment.total_amount, "XTR"
        )
        db.confirm_purchase(purchase_id, "stars_payment")
        m = db.get_movie(movie_id)
        await msg.answer(
            f"✅ <b>Оплачено!</b>\n\n"
            f"🎬 Фильм <b>{m['title']}</b> доступен.\n"
            "Нажми «Смотреть» в каталоге 👇",
            parse_mode="HTML",
        )
