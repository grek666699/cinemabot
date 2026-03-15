"""
🔧 Панель администратора
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import ADMIN_IDS, SUBSCRIPTION_PLANS

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class AddMovieState(StatesGroup):
    title       = State()
    description = State()
    genre       = State()
    year        = State()
    rating      = State()
    duration    = State()
    video_url   = State()
    price       = State()


# ─── Статистика ────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_panel(msg: Message):
    if not is_admin(msg.from_user.id):
        return

    stats = db.get_stats()
    await msg.answer(
        "🔧 <b>Панель администратора</b>\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"💎 Активных подписок: {stats['active_subs']}\n"
        f"🎬 Фильмов в каталоге: {stats['total_movies']}\n"
        f"💳 Успешных покупок: {stats['total_purchases']}\n\n"
        "<b>Команды:</b>\n"
        "/addmovie — добавить фильм\n"
        "/pending — ожидающие крипто-платежи\n"
        "/giveaccess [user_id] [days] — дать подписку\n"
        "/broadcast [текст] — рассылка всем",
        parse_mode="HTML",
    )


# ─── Добавление фильма ─────────────────────────────────────

@router.message(Command("addmovie"))
async def add_movie_start(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    await state.set_state(AddMovieState.title)
    await msg.answer("🎬 Введи <b>название</b> фильма:", parse_mode="HTML")


@router.message(AddMovieState.title)
async def add_movie_title(msg: Message, state: FSMContext):
    await state.update_data(title=msg.text.strip())
    await state.set_state(AddMovieState.description)
    await msg.answer("📖 Введи <b>описание</b>:", parse_mode="HTML")


@router.message(AddMovieState.description)
async def add_movie_desc(msg: Message, state: FSMContext):
    await state.update_data(description=msg.text.strip())
    await state.set_state(AddMovieState.genre)
    await msg.answer("🏷 Введи <b>жанр</b> (Фантастика / Драма / ...):  ", parse_mode="HTML")


@router.message(AddMovieState.genre)
async def add_movie_genre(msg: Message, state: FSMContext):
    await state.update_data(genre=msg.text.strip())
    await state.set_state(AddMovieState.year)
    await msg.answer("📅 Введи <b>год</b> выхода:", parse_mode="HTML")


@router.message(AddMovieState.year)
async def add_movie_year(msg: Message, state: FSMContext):
    try:
        year = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи число (например, 2023)")
        return
    await state.update_data(year=year)
    await state.set_state(AddMovieState.rating)
    await msg.answer("⭐ Введи <b>рейтинг</b> (например, 8.5):", parse_mode="HTML")


@router.message(AddMovieState.rating)
async def add_movie_rating(msg: Message, state: FSMContext):
    try:
        rating = float(msg.text.strip().replace(",", "."))
    except ValueError:
        await msg.answer("❌ Введи число (например, 8.5)")
        return
    await state.update_data(rating=rating)
    await state.set_state(AddMovieState.duration)
    await msg.answer("⏱ Введи <b>длительность</b> в минутах:", parse_mode="HTML")


@router.message(AddMovieState.duration)
async def add_movie_duration(msg: Message, state: FSMContext):
    try:
        duration = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи число минут")
        return
    await state.update_data(duration=duration)
    await state.set_state(AddMovieState.video_url)
    await msg.answer(
        "🎥 Введи <b>ссылку на видео</b> или Telegram file_id.\n"
        "Отправь <code>-</code> чтобы пропустить:",
        parse_mode="HTML"
    )


@router.message(AddMovieState.video_url)
async def add_movie_video(msg: Message, state: FSMContext):
    url = msg.text.strip()
    await state.update_data(video_url="" if url == "-" else url)
    await state.set_state(AddMovieState.price)
    await msg.answer(
        "💰 Введи цену в формате: <code>Stars USD</code>\n"
        "Например: <code>50 0.99</code>\n"
        "Для бесплатного: <code>0 0</code>",
        parse_mode="HTML"
    )


@router.message(AddMovieState.price)
async def add_movie_price(msg: Message, state: FSMContext):
    try:
        parts = msg.text.strip().split()
        stars = int(parts[0])
        usd   = float(parts[1])
    except Exception:
        await msg.answer("❌ Формат: 50 0.99")
        return

    data = await state.get_data()
    is_free = 1 if stars == 0 and usd == 0 else 0

    db.add_movie(
        title=data["title"],
        description=data["description"],
        genre=data["genre"],
        year=data["year"],
        rating=data["rating"],
        duration=data["duration"],
        poster_url="",
        video_url=data["video_url"],
        price_stars=stars,
        price_usd=usd,
        is_free=is_free,
    )

    free_label = "🆓 Бесплатно" if is_free else f"⭐{stars} Stars / ${usd}"
    await msg.answer(
        f"✅ <b>Фильм добавлен!</b>\n\n"
        f"🎬 {data['title']} ({data['year']})\n"
        f"💰 {free_label}",
        parse_mode="HTML",
    )
    await state.clear()


# ─── Ожидающие крипто-платежи ──────────────────────────────

@router.message(Command("pending"))
async def pending_payments(msg: Message):
    if not is_admin(msg.from_user.id): return

    payments = db.get_pending_crypto_payments()
    if not payments:
        await msg.answer("✅ Нет ожидающих платежей")
        return

    from keyboards import confirm_tx_kb
    for p in payments[:10]:
        await msg.answer(
            f"💳 <b>Платёж #{p['id']}</b>\n\n"
            f"👤 User: <code>{p['user_id']}</code>\n"
            f"💰 {p['amount']} {p['currency']}\n"
            f"🎯 {p['purpose']}\n"
            f"🔗 Хэш: <code>{p['tx_hash'] or 'не указан'}</code>\n"
            f"📅 {p['created_at'][:16]}",
            parse_mode="HTML",
            reply_markup=confirm_tx_kb(p["id"]),
        )


# ─── Подтверждение/отклонение платежа ──────────────────────

@router.callback_query(F.data.startswith("admin_confirm:"))
async def admin_confirm_payment(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав", show_alert=True)
        return

    payment_id = int(call.data.split(":")[1])
    from database import get_conn
    with get_conn() as conn:
        p = conn.execute("SELECT * FROM crypto_payments WHERE id=?", (payment_id,)).fetchone()

    if not p:
        await call.answer("Платёж не найден", show_alert=True)
        return

    user_id  = p["user_id"]
    purpose  = p["purpose"]

    if purpose.startswith("subscription_"):
        plan_key = purpose.replace("subscription_", "")
        plan = SUBSCRIPTION_PLANS.get(plan_key, {})
        days = plan.get("days", 30)
        ends = db.set_subscription(user_id, plan_key, days)
        msg_text = (
            f"✅ <b>Подписка активирована!</b>\n\n"
            f"Действует до: <b>{ends.strftime('%d.%m.%Y')}</b>\n"
            "Приятного просмотра! 🍿"
        )

    elif purpose.startswith("movie_"):
        movie_id = int(purpose.replace("movie_", ""))
        purchase_id = db.create_purchase(user_id, movie_id, p["currency"], p["amount"], p["currency"])
        db.confirm_purchase(purchase_id, p["tx_hash"])
        m = db.get_movie(movie_id)
        msg_text = (
            f"✅ <b>Доступ открыт!</b>\n\n"
            f"🎬 Фильм <b>{m['title'] if m else '?'}</b> теперь доступен.\n"
            "Найди его в каталоге 🎬"
        )
    else:
        msg_text = "✅ Платёж подтверждён!"

    # Уведомить пользователя
    try:
        await call.bot.send_message(user_id, msg_text, parse_mode="HTML")
    except Exception:
        pass

    await call.message.edit_text(
        call.message.text + f"\n\n✅ <b>ПОДТВЕРЖДЁН</b> администратором {call.from_user.full_name}",
        parse_mode="HTML",
    )
    await call.answer("✅ Подтверждено!")


@router.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject_payment(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав", show_alert=True)
        return

    payment_id = int(call.data.split(":")[1])
    from database import get_conn
    with get_conn() as conn:
        p = conn.execute("SELECT * FROM crypto_payments WHERE id=?", (payment_id,)).fetchone()
        conn.execute("UPDATE crypto_payments SET status='rejected' WHERE id=?", (payment_id,))

    if p:
        try:
            await call.bot.send_message(
                p["user_id"],
                "❌ <b>Платёж отклонён</b>\n\n"
                "Хэш транзакции не прошёл проверку.\n"
                "Если считаешь это ошибкой — обратись в поддержку.",
                parse_mode="HTML",
            )
        except Exception:
            pass

    await call.message.edit_text(
        call.message.text + "\n\n❌ <b>ОТКЛОНЁН</b>",
        parse_mode="HTML",
    )
    await call.answer("❌ Отклонено")


# ─── Выдача подписки вручную ───────────────────────────────

@router.message(Command("giveaccess"))
async def give_access(msg: Message):
    if not is_admin(msg.from_user.id): return
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.answer("Использование: /giveaccess [user_id] [days]")
        return
    try:
        uid = int(parts[1])
        days = int(parts[2])
    except ValueError:
        await msg.answer("❌ Неверные параметры")
        return

    ends = db.set_subscription(uid, "manual", days)
    await msg.answer(f"✅ Пользователю {uid} выдана подписка до {ends.strftime('%d.%m.%Y')}")
    try:
        await msg.bot.send_message(
            uid,
            f"🎁 <b>Администратор подарил вам подписку!</b>\n\n"
            f"Действует до: <b>{ends.strftime('%d.%m.%Y')}</b>\n"
            "Приятного просмотра! 🍿",
            parse_mode="HTML",
        )
    except Exception:
        pass


# ─── Рассылка ──────────────────────────────────────────────

@router.message(Command("broadcast"))
async def broadcast(msg: Message):
    if not is_admin(msg.from_user.id): return
    text = msg.text[len("/broadcast "):].strip()
    if not text:
        await msg.answer("Использование: /broadcast [текст]")
        return

    from database import get_conn
    with get_conn() as conn:
        users = conn.execute("SELECT user_id FROM users").fetchall()

    sent, failed = 0, 0
    for u in users:
        try:
            await msg.bot.send_message(u["user_id"], text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1

    await msg.answer(f"📨 Рассылка завершена\n✅ Доставлено: {sent}\n❌ Ошибок: {failed}")
