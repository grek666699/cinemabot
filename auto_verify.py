"""
🔍 Автоматическая проверка крипто-транзакций

TON  — через TON Center API (бесплатно, без ключа)
USDT — через Tronscan API (бесплатно, без ключа)

Фоновая задача запускается каждые 60 секунд и проверяет
все pending-платежи. При совпадении суммы — активирует доступ.
"""

import asyncio
import logging
import aiohttp
from datetime import datetime, timedelta

import database as db
from config import WALLETS, ADMIN_IDS, SUBSCRIPTION_PLANS

log = logging.getLogger(__name__)

# ─── Настройки ──────────────────────────────────────────────
CHECK_INTERVAL   = 60       # секунды между проверками
PAYMENT_TIMEOUT  = 3600     # 1 час — после этого платёж считается просроченным
TOLERANCE        = 0.01     # погрешность суммы (1%)

TON_API_URL  = "https://toncenter.com/api/v2"
TRON_API_URL = "https://apilist.tronscanapi.com/api"


# ════════════════════════════════════════════════════════════
# TON API
# ════════════════════════════════════════════════════════════

async def get_ton_transactions(wallet: str, limit: int = 20) -> list:
    """Получить последние транзакции на TON кошелёк"""
    url = f"{TON_API_URL}/getTransactions"
    params = {"address": wallet, "limit": limit, "to_lt": 0}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
                if data.get("ok"):
                    return data.get("result", [])
    except Exception as e:
        log.warning(f"TON API error: {e}")
    return []


def parse_ton_amount(nano: int) -> float:
    """Нанотоны → TON"""
    return nano / 1_000_000_000


async def find_ton_payment(expected_amount: float, wallet: str, since: datetime) -> dict | None:
    """
    Найти входящую транзакцию на сумму expected_amount ± TOLERANCE
    созданную после since
    """
    txs = await get_ton_transactions(wallet, limit=30)
    for tx in txs:
        try:
            # Время транзакции
            tx_time = datetime.utcfromtimestamp(tx.get("utime", 0))
            if tx_time < since:
                continue  # транзакция старше платежа

            # Входящее сообщение
            in_msg = tx.get("in_msg", {})
            value_nano = int(in_msg.get("value", 0))
            if value_nano == 0:
                continue

            amount = parse_ton_amount(value_nano)
            diff = abs(amount - expected_amount) / expected_amount

            if diff <= TOLERANCE:
                return {
                    "hash":   tx.get("transaction_id", {}).get("hash", ""),
                    "amount": amount,
                    "from":   in_msg.get("source", ""),
                    "time":   tx_time.isoformat(),
                }
        except Exception as e:
            log.debug(f"parse tx error: {e}")
    return None


# ════════════════════════════════════════════════════════════
# USDT TRC-20 (Tronscan)
# ════════════════════════════════════════════════════════════

USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # USDT TRC-20 contract


async def get_usdt_transactions(wallet: str, limit: int = 20) -> list:
    """Получить последние USDT TRC-20 транзакции"""
    url = f"{TRON_API_URL}/token_trc20/transfers"
    params = {
        "toAddress":       wallet,
        "contractAddress": USDT_CONTRACT,
        "limit":           limit,
        "start":           0,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
                return data.get("token_transfers", [])
    except Exception as e:
        log.warning(f"Tronscan API error: {e}")
    return []


async def find_usdt_payment(expected_amount: float, wallet: str, since: datetime) -> dict | None:
    """Найти USDT-транзакцию на нужную сумму"""
    txs = await get_usdt_transactions(wallet, limit=30)
    for tx in txs:
        try:
            # Время в миллисекундах
            ts = tx.get("block_ts", 0)
            tx_time = datetime.utcfromtimestamp(ts / 1000)
            if tx_time < since:
                continue

            # USDT имеет 6 знаков
            raw_amount = int(tx.get("quant", 0))
            amount = raw_amount / 1_000_000
            diff = abs(amount - expected_amount) / expected_amount

            if diff <= TOLERANCE:
                return {
                    "hash":   tx.get("transaction_id", ""),
                    "amount": amount,
                    "from":   tx.get("from_address", ""),
                    "time":   tx_time.isoformat(),
                }
        except Exception as e:
            log.debug(f"parse usdt tx: {e}")
    return None


# ════════════════════════════════════════════════════════════
# АКТИВАЦИЯ ДОСТУПА
# ════════════════════════════════════════════════════════════

async def activate_access(bot, payment: dict, tx: dict):
    """Активировать подписку или покупку фильма после подтверждения платежа"""
    user_id = payment["user_id"]
    purpose = payment["purpose"]
    payment_id = payment["id"]

    # Подтвердить в БД
    db.confirm_crypto_payment(payment_id, tx["hash"])

    if purpose.startswith("subscription_"):
        plan_key = purpose.replace("subscription_", "")
        plan = SUBSCRIPTION_PLANS.get(plan_key, {})
        days = plan.get("days", 30)
        ends = db.set_subscription(user_id, plan_key, days)

        text = (
            f"✅ <b>Оплата подтверждена автоматически!</b>\n\n"
            f"💎 Подписка <b>{plan.get('name', plan_key)}</b> активирована\n"
            f"📅 Действует до: <b>{ends.strftime('%d.%m.%Y')}</b>\n\n"
            f"🔗 Хэш: <code>{tx['hash'][:20]}...</code>\n"
            f"💰 Получено: {tx['amount']} {payment['currency']}\n\n"
            "Приятного просмотра! 🍿"
        )

    elif purpose.startswith("movie_"):
        movie_id = int(purpose.replace("movie_", ""))
        purchase_id = db.create_purchase(
            user_id, movie_id,
            payment["currency"], payment["amount"], payment["currency"]
        )
        db.confirm_purchase(purchase_id, tx["hash"])
        m = db.get_movie(movie_id)

        text = (
            f"✅ <b>Оплата подтверждена автоматически!</b>\n\n"
            f"🎬 Фильм <b>{m['title'] if m else '?'}</b> теперь доступен\n"
            f"🔗 Хэш: <code>{tx['hash'][:20]}...</code>\n"
            f"💰 Получено: {tx['amount']} {payment['currency']}\n\n"
            "Перейди в каталог и нажми «Смотреть» 🎬"
        )
    else:
        text = f"✅ Платёж #{payment_id} подтверждён автоматически."

    # Уведомить пользователя
    try:
        await bot.send_message(user_id, text, parse_mode="HTML")
    except Exception as e:
        log.warning(f"Cannot notify user {user_id}: {e}")

    # Уведомить администраторов
    admin_text = (
        f"🤖 <b>Авто-подтверждение #{payment_id}</b>\n\n"
        f"👤 User: <code>{user_id}</code>\n"
        f"💰 {tx['amount']} {payment['currency']}\n"
        f"🎯 {purpose}\n"
        f"🔗 <code>{tx['hash']}</code>\n"
        f"⏱ {tx['time']}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, parse_mode="HTML")
        except Exception:
            pass

    log.info(f"✅ Payment #{payment_id} auto-confirmed | {tx['hash'][:16]}...")


async def expire_payment(bot, payment: dict):
    """Пометить платёж как просроченный и уведомить пользователя"""
    from database import get_conn
    with get_conn() as conn:
        conn.execute(
            "UPDATE crypto_payments SET status='expired' WHERE id=?",
            (payment["id"],)
        )

    try:
        await bot.send_message(
            payment["user_id"],
            f"⏰ <b>Платёж #{payment['id']} просрочен</b>\n\n"
            f"Транзакция не найдена в течение 1 часа.\n"
            f"Если ты уже оплатил — обратись в поддержку с хэшем транзакции.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    log.info(f"⏰ Payment #{payment['id']} expired")


# ════════════════════════════════════════════════════════════
# ФОНОВАЯ ЗАДАЧА
# ════════════════════════════════════════════════════════════

async def check_pending_payments(bot):
    """Проверить все pending-платежи"""
    from database import get_conn
    with get_conn() as conn:
        payments = conn.execute("""
            SELECT * FROM crypto_payments
            WHERE status = 'pending'
            ORDER BY created_at ASC
        """).fetchall()

    if not payments:
        return

    log.info(f"🔍 Проверяю {len(payments)} pending платежей...")

    for p in payments:
        p = dict(p)
        try:
            created = datetime.fromisoformat(p["created_at"])
            currency = p["currency"]
            amount = float(p["amount"])
            wallet = WALLETS.get(currency, "")

            # Просрочен?
            if datetime.utcnow() - created > timedelta(seconds=PAYMENT_TIMEOUT):
                await expire_payment(bot, p)
                continue

            # Ищем транзакцию
            tx = None
            if currency == "TON":
                tx = await find_ton_payment(amount, wallet, created)
            elif currency == "USDT":
                tx = await find_usdt_payment(amount, wallet, created)

            if tx:
                log.info(f"💰 Найден платёж #{p['id']}: {tx['hash'][:16]}...")
                await activate_access(bot, p, tx)
            else:
                log.debug(f"⏳ Платёж #{p['id']} ({amount} {currency}) — не найден пока")

            await asyncio.sleep(1)  # пауза между запросами к API

        except Exception as e:
            log.error(f"Error checking payment #{p.get('id')}: {e}")


async def auto_verify_loop(bot):
    """Бесконечный цикл проверки"""
    log.info(f"🤖 Авто-верификатор запущен (интервал: {CHECK_INTERVAL}с)")
    while True:
        try:
            await check_pending_payments(bot)
        except Exception as e:
            log.error(f"Auto-verify loop error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)
