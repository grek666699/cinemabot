"""
🎬 CinemaBot — Telegram платный кинотеатр
Оплата: Telegram Stars + Криптовалюта (TON/USDT)
Авто-верификация крипто-транзакций через TON Center + Tronscan API
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import start, catalog, subscription, cabinet, payment, admin
from auto_verify import auto_verify_loop
import database as db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger(__name__)


async def main():
    db.init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(subscription.router)
    dp.include_router(cabinet.router)
    dp.include_router(payment.router)
    dp.include_router(admin.router)

    log.info("🎬 CinemaBot запущен!")
    log.info("🔍 Авто-верификация: TON Center + Tronscan")

    # Бот + авто-верификатор параллельно
    await asyncio.gather(
        dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()),
        auto_verify_loop(bot),
    )


if __name__ == "__main__":
    asyncio.run(main())
