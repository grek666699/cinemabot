"""
🔧 Панель администратора
"""

import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
from config import ADMIN_IDS, SUBSCRIPTION_PLANS

router = Router()

TMDB_API_KEY = "4f6e4f86a8e8c7b3d2a1f09e5c3b2a18"
TMDB_URL     = "https://api.themoviedb.org/3"


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


class QuickAddState(StatesGroup):
    search    = State()
    select    = State()
    video_url = State()
    price     = State()


# ─── TMDB API ──────────────────────────────────────────────

async def search_tmdb(query: str) -> list:
    url    = f"{TMDB_URL}/search/movie"
    params = {"api_key": TMDB_API_KEY, "query": query, "language": "ru-RU", "include_adult": False}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
                return data.get("results", [])[:5]
    except Exception:
        return []


async def get_tmdb_details(movie_id: int) -> dict:
    url    = f"{TMDB_URL}/movie/{movie_id}"
    params = {"api_key": TMDB_API_KEY, "language": "ru-RU"}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                return await r.json()
    except Exception:
        return {}


# ─── Быстрое добавление ────────────────────────────────────

@router.message(Command("quickadd"))
async def quick_add(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    await state.set_state(QuickAddState.search)
    await msg.answer(
        "🔍 <b>Быстрое добавление</b>\n\nНапиши название фильма — найду всё автоматически:",
        parse_mode="HTML",
    )


@router.message(QuickAddState.search)
async def quick_search(msg: Message, state: FSMContext):
    results = await search_tmdb(msg.text.strip())
    if not results:
        await msg.answer("❌ Ничего не найдено. Попробуй другое название:")
        return
    builder = InlineKeyboardBuilder()
    for m in results:
        year = m.get("release_date", "")[:4] or "?"
        builder.button(text=f"{m.get('title','?')} ({year})", callback_data=f"qadd:{m['id']}")
    builder.button(text="❌ Отмена", callback_data="qadd:cancel")
    builder.adjust(1)
    await state.set_state(QuickAddState.select)
    await msg.answer(f"🎬 Найдено {len(results)} фильмов. Выбери нужный:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("qadd:"))
async def quick_select(call: CallbackQuery, state: FSMContext):
    val = call.data.split(":")[1]
    if val == "cancel":
        await state.clear()
        await call.message.answer("❌ Отменено")
        await call.answer()
        return
    details = await get_tmdb_details(int(val))
    if not details:
        await call.answer("❌ Ошибка загрузки", show_alert=True)
        return
    genres = [g["name"] for g in details.get("genres", [])]
    movie_data = {
        "title":       details.get("title", "?"),
        "description": details.get("overview", "Описание отсутствует"),
        "genre":       genres[0] if genres else "Другое",
        "year":        int(details.get("release_date", "2000")[:4] or 2000),
        "rating":      round(details.get("vote_average", 0), 1),
        "duration":    details.get("runtime", 90) or 90,
        "poster_url":  f"https://image.tmdb.org/t/p/w500{details.get('poster_path','')}",
    }
    await state.update_data(movie=movie_data)
    await state.set_state(QuickAddState.video_url)
    await call.message.edit_text(
        f"✅ <b>Найдено!</b>\n\n"
        f"🎬 <b>{movie_data['title']}</b> ({movie_data['year']})\n"
        f"📖 {movie_data['description'][:200]}\n"
        f"🏷 {movie_data['genre']} · ⭐{movie_data['rating']} · ⏱{movie_data['duration']} мин\n\n"
        f"🎥 Отправь видеофайл, ссылку или <code>-</code> чтобы пропустить:",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(QuickAddState.video_url)
async def quick_video(msg: Message, state: FSMContext):
    if msg.video:
        video_url = msg.video.file_id
    elif msg.document and msg.document.mime_type and "video" in msg.document.mime_type:
        video_url = msg.document.file_id
    else:
        video_url = "" if msg.text.strip() == "-" else msg.text.strip()
    await state.update_data(video_url=video_url)
    await state.set_state(QuickAddState.price)
    await msg.answer(
        "💰 Введи цену: <code>Stars USD</code>\nНапример: <code>50 0.99</code>\nБесплатно: <code>0 0</code>",
        parse_mode="HTML",
    )


@router.message(QuickAddState.price)
async def quick_price(msg: Message, state: FSMContext):
    try:
        parts = msg.text.strip().split()
        stars = int(parts[0])
        usd   = float(parts[1])
    except Exception:
        await msg.answer("❌ Формат: 50 0.99")
        return
    data      = await state.get_data()
    movie     = data["movie"]
    video_url = data.get("video_url", "")
    is_free   = 1 if stars == 0 and usd == 0 else 0
    db.add_movie(
        title=movie["title"], description=movie["description"],
        genre=movie["genre"], year=movie["year"], rating=movie["rating"],
        duration=movie["duration"], poster_url=movie["poster_url"],
        video_url=video_url, price_stars=stars, price_usd=usd, is_free=is_free,
    )
    await msg.answer(
        f"✅ <b>Добавлено!</b>\n🎬 {movie['title']} ({movie['year']})\n"
        f"💰 {'🆓 Бесплатно' if is_free else f'⭐{stars} / ${usd}'}",
        parse_mode="HTML",
    )
    await state.clear()


# ─── Статистика ────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_panel(msg: Message):
    if not is_admin(msg.from_user.id): return
    stats = db.get_stats()
    await msg.answer(
        "🔧 <b>Панель администратора</b>\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"💎 Активных подписок: {stats['active_subs']}\n"
        f"🎬 Фильмов в каталоге: {stats['total_movies']}\n"
        f"💳 Успешных покупок: {stats['total_purchases']}\n\n"
        "<b>Команды:</b>\n"
        "/quickadd — ⚡ быстро по названию (авто)\n"
        "/addmovie — добавить вручную\n"
        "/pending — ожидающие платежи\n"
        "/giveaccess [id] [дни] — выдать подписку\n"
        "/broadcast [текст] — рассылка",
        parse_mode="HTML",
    )


# ─── Ручное добавление ─────────────────────────────────────

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
    await msg.answer("🏷 Введи <b>жанр</b>:", parse_mode="HTML")


@router.message(AddMovieState.genre)
async def add_movie_genre(msg: Message, state: FSMContext):
    await state.update_data(genre=msg.text.strip())
    await state.set_state(AddMovieState.year)
    await msg.answer("📅 Введи <b>год</b>:", parse_mode="HTML")


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
    await msg.answer("🎥 Введи ссылку или file_id. <code>-</code> чтобы пропустить:", parse_mode="HTML")


@router.message(AddMovieState.video_url)
async def add_movie_video(msg: Message, state: FSMContext):
    url = msg.text.strip()
    await state.update_data(video_url="" if url == "-" else url)
    await state.set_state(AddMovieState.price)
    await msg.answer("💰 Цена: <code>Stars USD</code>\nПример: <code>50 0.99</code>\nБесплатно: <code>0 0</code>", parse_mode="HTML")


@router.message(AddMovieState.price)
async def add_movie_price(msg: Message, state: FSMContext):
    try:
        parts = msg.text.strip().split()
        stars = int(parts[0])
        usd   = float(parts[1])
    except Exception:
        await msg.answer("❌ Формат: 50 0.99")
        return
    data    = await state.get_data()
    is_free = 1 if stars == 0 and usd == 0 else 0
    db.add_movie(
        title=data["title"], description=data["description"],
        genre=data["genre"], year=data["year"], rating=data["rating"],
        duration=data["duration"], poster_url="", video_url=data["video_url"],
        price_stars=stars, price_usd=usd, is_free=is_free,
    )
    await msg.answer(
        f"✅ <b>Фильм добавлен!</b>\n🎬 {data['title']}\n💰 {'🆓' if is_free else f'⭐{stars} / ${usd}'}",
        parse_mode="HTML",
    )
    await state.clear()


# ─── Ожидающие платежи ─────────────────────────────────────

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
            f"💳 <b>Платёж #{p['id']}</b>\n👤 <code>{p['user_id']}</code>\n"
            f"💰 {p['amount']} {p['currency']}\n🎯 {p['purpose']}\n"
            f"🔗 <code>{p['tx_hash'] or 'не указан'}</code>",
            parse_mode="HTML", reply_markup=confirm_tx_kb(p["id"]),
        )


# ─── Подтверждение/отклонение ──────────────────────────────

@router.callback_query(F.data.startswith("admin_confirm:"))
async def admin_confirm_payment(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав", show_alert=True); return
    payment_id = int(call.data.split(":")[1])
    from database import get_conn
    with get_conn() as conn:
        p = conn.execute("SELECT * FROM crypto_payments WHERE id=?", (payment_id,)).fetchone()
    if not p:
        await call.answer("Не найден", show_alert=True); return
    user_id = p["user_id"]
    purpose = p["purpose"]
    if purpose.startswith("subscription_"):
        plan_key = purpose.replace("subscription_", "")
        plan = SUBSCRIPTION_PLANS.get(plan_key, {})
        ends = db.set_subscription(user_id, plan_key, plan.get("days", 30))
        msg_text = f"✅ <b>Подписка активирована!</b>\nДо: <b>{ends.strftime('%d.%m.%Y')}</b>\n🍿"
    elif purpose.startswith("movie_"):
        movie_id    = int(purpose.replace("movie_", ""))
        purchase_id = db.create_purchase(user_id, movie_id, p["currency"], p["amount"], p["currency"])
        db.confirm_purchase(purchase_id, p["tx_hash"])
        m = db.get_movie(movie_id)
        msg_text = f"✅ <b>Доступ открыт!</b>\n🎬 <b>{m['title'] if m else '?'}</b>"
    else:
        msg_text = "✅ Подтверждено!"
    try:
        await call.bot.send_message(user_id, msg_text, parse_mode="HTML")
    except Exception:
        pass
    await call.message.edit_text(call.message.text + "\n\n✅ <b>ПОДТВЕРЖДЁН</b>", parse_mode="HTML")
    await call.answer("✅ Подтверждено!")


@router.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject_payment(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав", show_alert=True); return
    payment_id = int(call.data.split(":")[1])
    from database import get_conn
    with get_conn() as conn:
        p = conn.execute("SELECT * FROM crypto_payments WHERE id=?", (payment_id,)).fetchone()
        conn.execute("UPDATE crypto_payments SET status='rejected' WHERE id=?", (payment_id,))
    if p:
        try:
            await call.bot.send_message(p["user_id"], "❌ <b>Платёж отклонён.</b>\nОбратитесь в поддержку.", parse_mode="HTML")
        except Exception:
            pass
    await call.message.edit_text(call.message.text + "\n\n❌ <b>ОТКЛОНЁН</b>", parse_mode="HTML")
    await call.answer("❌ Отклонено")


# ─── Выдача подписки вручную ───────────────────────────────

@router.message(Command("giveaccess"))
async def give_access(msg: Message):
    if not is_admin(msg.from_user.id): return
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.answer("Использование: /giveaccess [user_id] [days]"); return
    try:
        uid  = int(parts[1])
        days = int(parts[2])
    except ValueError:
        await msg.answer("❌ Неверные параметры"); return
    ends = db.set_subscription(uid, "manual", days)
    await msg.answer(f"✅ Пользователю {uid} выдана подписка до {ends.strftime('%d.%m.%Y')}")
    try:
        await msg.bot.send_message(uid, f"🎁 <b>Подписка активирована!</b>\nДо: <b>{ends.strftime('%d.%m.%Y')}</b>\n🍿", parse_mode="HTML")
    except Exception:
        pass


# ─── Рассылка ──────────────────────────────────────────────

@router.message(Command("broadcast"))
async def broadcast(msg: Message):
    if not is_admin(msg.from_user.id): return
    text = msg.text[len("/broadcast "):].strip()
    if not text:
        await msg.answer("Использование: /broadcast [текст]"); return
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
    await msg.answer(f"📨 Рассылка завершена\n✅ {sent}\n❌ {failed}")
