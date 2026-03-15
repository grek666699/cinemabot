"""
🎬 Каталог фильмов
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

import database as db
from keyboards import catalog_menu, movies_list, movie_detail

router = Router()

PAGE_SIZE = 8


@router.message(F.text == "🎬 Каталог")
async def show_catalog(msg: Message):
    genres = db.get_genres()
    await msg.answer(
        "🎬 <b>Каталог фильмов</b>\n\nВыбери жанр или смотри все фильмы:",
        parse_mode="HTML",
        reply_markup=catalog_menu(genres),
    )


@router.callback_query(F.data.startswith("cat:"))
async def catalog_page(call: CallbackQuery):
    parts = call.data.split(":")
    # cat:all:offset  или  cat:genre:ИМЯ:offset
    if parts[1] == "all":
        genre = None
        genre_key = "all"
        offset = int(parts[2])
    else:
        genre = parts[2]
        genre_key = genre
        offset = int(parts[3])

    movies = db.get_movies(genre=genre, limit=PAGE_SIZE, offset=offset)
    all_movies = db.get_movies(genre=genre, limit=9999)
    total = len(all_movies)

    if not movies:
        await call.answer("Фильмы не найдены 😕", show_alert=True)
        return

    label = f"жанр: {genre}" if genre else "все фильмы"
    text = (
        f"🎬 <b>Каталог</b> — {label}\n"
        f"Показано: {offset+1}–{min(offset+PAGE_SIZE, total)} из {total}\n\n"
        "Выбери фильм 👇"
    )

    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=movies_list(movies, genre_key, offset, total),
    )
    await call.answer()


@router.callback_query(F.data.startswith("movie:"))
async def movie_info(call: CallbackQuery):
    movie_id = int(call.data.split(":")[1])
    m = db.get_movie(movie_id)
    if not m:
        await call.answer("Фильм не найден", show_alert=True)
        return

    user_id = call.from_user.id
    has_sub = db.has_active_subscription(user_id)
    has_purchase = db.has_purchased_movie(user_id, movie_id)
    has_access = has_sub or has_purchase or bool(m["is_free"])

    free_label = "🆓 Бесплатно" if m["is_free"] else f"⭐ {m['price_stars']} Stars / 💵 ${m['price_usd']}"
    sub_note = "\n✅ <i>У вас есть подписка — смотрите бесплатно!</i>" if has_sub and not m["is_free"] else ""
    bought_note = "\n✅ <i>Фильм куплен</i>" if has_purchase else ""

    text = (
        f"🎬 <b>{m['title']}</b> ({m['year']})\n\n"
        f"📖 {m['description']}\n\n"
        f"🏷 Жанр: {m['genre']}\n"
        f"⭐ Рейтинг: {m['rating']}\n"
        f"⏱ Длительность: {m['duration']} мин\n"
        f"💰 Цена: {free_label}"
        f"{sub_note}{bought_note}"
    )

    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=movie_detail(movie_id, has_access, bool(m["is_free"])),
    )
    await call.answer()


@router.callback_query(F.data.startswith("watch:"))
async def watch_movie(call: CallbackQuery):
    movie_id = int(call.data.split(":")[1])
    m = db.get_movie(movie_id)
    if not m:
        await call.answer("Фильм не найден", show_alert=True)
        return

    user_id = call.from_user.id
    has_sub = db.has_active_subscription(user_id)
    has_purchase = db.has_purchased_movie(user_id, movie_id)

    if not (has_sub or has_purchase or m["is_free"]):
        await call.answer("❌ Нет доступа. Купите фильм или оформите подписку.", show_alert=True)
        return

    # Если есть video_url — отправляем видео, иначе заглушка
    if m["video_url"]:
        await call.message.answer_video(
            m["video_url"],
            caption=f"▶️ <b>{m['title']}</b> ({m['year']})\n\nПриятного просмотра! 🍿",
            parse_mode="HTML",
        )
    else:
        await call.message.answer(
            f"▶️ <b>{m['title']}</b>\n\n"
            "🎬 Здесь будет видеофайл или ссылка на стриминг.\n"
            "📝 Добавьте video_url через команду /addmovie",
            parse_mode="HTML",
        )
    await call.answer()


@router.callback_query(F.data == "go_sub")
async def go_sub(call: CallbackQuery):
    from handlers.subscription import show_subscription
    await show_subscription(call.message)
    await call.answer()
