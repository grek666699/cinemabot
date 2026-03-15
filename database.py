"""
🗄 База данных (SQLite)
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from config import DB_PATH

log = logging.getLogger(__name__)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создать таблицы при первом запуске"""
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            full_name   TEXT,
            joined_at   TEXT DEFAULT (datetime('now')),
            sub_until   TEXT,          -- дата окончания подписки
            sub_plan    TEXT,          -- 'month' / 'year'
            total_spent REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS movies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            description TEXT,
            genre       TEXT,
            year        INTEGER,
            rating      REAL,
            duration    INTEGER,       -- минуты
            poster_url  TEXT,
            video_url   TEXT,          -- прямая ссылка или file_id
            is_free     INTEGER DEFAULT 0,
            price_stars INTEGER DEFAULT 0,
            price_usd   REAL DEFAULT 0,
            added_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS purchases (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            movie_id    INTEGER,
            payment_type TEXT,         -- 'stars' / 'ton' / 'usdt' / 'subscription'
            amount      REAL,
            currency    TEXT,
            status      TEXT DEFAULT 'pending',  -- pending / confirmed / failed
            tx_hash     TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            plan        TEXT,
            payment_type TEXT,
            amount      REAL,
            currency    TEXT,
            status      TEXT DEFAULT 'pending',
            tx_hash     TEXT,
            starts_at   TEXT,
            ends_at     TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS crypto_payments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            purpose     TEXT,          -- 'subscription_month' / 'subscription_year' / 'movie_ID'
            currency    TEXT,
            amount      REAL,
            wallet      TEXT,
            status      TEXT DEFAULT 'pending',
            tx_hash     TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );
        """)
    log.info("✅ База данных инициализирована")
    _seed_movies()


def _seed_movies():
    """Заполнить тестовыми фильмами если база пустая"""
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        if count > 0:
            return

        sample = [
            ("Начало", "Вор, крадущий секреты из снов, получает задание внедрить идею.", "Фантастика", 2010, 8.8, 148,
             "https://example.com/inception.jpg", "", 0, 50, 0.99),
            ("Интерстеллар", "Команда исследователей путешествует через червоточину в поисках нового дома.", "Фантастика", 2014, 8.6, 169,
             "https://example.com/interstellar.jpg", "", 0, 50, 0.99),
            ("Зелёная книга", "История дружбы водителя и пианиста в расистской Америке.", "Драма", 2018, 8.2, 130,
             "https://example.com/greenbook.jpg", "", 0, 50, 0.99),
            ("Паразиты", "Бедная семья проникает в жизнь богатых.", "Триллер", 2019, 8.5, 132,
             "https://example.com/parasite.jpg", "", 0, 50, 0.99),
            ("Дюна", "Юный аристократ прибывает на опасную пустынную планету.", "Фантастика", 2021, 8.0, 155,
             "https://example.com/dune.jpg", "", 0, 50, 0.99),
            ("Всё везде и сразу", "Женщина открывает для себя параллельные вселенные.", "Фантастика", 2022, 7.9, 139,
             "https://example.com/everything.jpg", "", 1, 0, 0),   # бесплатный
        ]

        conn.executemany("""
            INSERT INTO movies (title, description, genre, year, rating, duration,
                                poster_url, video_url, is_free, price_stars, price_usd)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, sample)
        log.info("🎬 Тестовые фильмы добавлены")


# ─── ПОЛЬЗОВАТЕЛИ ──────────────────────────────────────────

def get_user(user_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def upsert_user(user_id: int, username: str, full_name: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name
        """, (user_id, username, full_name))


def has_active_subscription(user_id: int) -> bool:
    user = get_user(user_id)
    if not user or not user["sub_until"]:
        return False
    return datetime.fromisoformat(user["sub_until"]) > datetime.now()


def set_subscription(user_id: int, plan: str, days: int):
    now = datetime.now()
    user = get_user(user_id)
    if user and user["sub_until"]:
        try:
            current = datetime.fromisoformat(user["sub_until"])
            start = max(now, current)
        except Exception:
            start = now
    else:
        start = now
    ends = start + timedelta(days=days)
    with get_conn() as conn:
        conn.execute("""
            UPDATE users SET sub_until=?, sub_plan=? WHERE user_id=?
        """, (ends.isoformat(), plan, user_id))
    return ends


def has_purchased_movie(user_id: int, movie_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute("""
            SELECT id FROM purchases
            WHERE user_id=? AND movie_id=? AND status='confirmed'
        """, (user_id, movie_id)).fetchone()
    return row is not None


# ─── ФИЛЬМЫ ────────────────────────────────────────────────

def get_movies(genre: str = None, limit: int = 20, offset: int = 0):
    with get_conn() as conn:
        if genre:
            return conn.execute(
                "SELECT * FROM movies WHERE genre=? ORDER BY rating DESC LIMIT ? OFFSET ?",
                (genre, limit, offset)
            ).fetchall()
        return conn.execute(
            "SELECT * FROM movies ORDER BY rating DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()


def get_movie(movie_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM movies WHERE id=?", (movie_id,)).fetchone()


def get_genres():
    with get_conn() as conn:
        rows = conn.execute("SELECT DISTINCT genre FROM movies").fetchall()
    return [r["genre"] for r in rows]


def add_movie(title, description, genre, year, rating, duration,
              poster_url, video_url, price_stars, price_usd, is_free=0):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO movies (title, description, genre, year, rating, duration,
                                poster_url, video_url, price_stars, price_usd, is_free)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (title, description, genre, year, rating, duration,
               poster_url, video_url, price_stars, price_usd, is_free))


# ─── ПЛАТЕЖИ ───────────────────────────────────────────────

def create_purchase(user_id, movie_id, payment_type, amount, currency):
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO purchases (user_id, movie_id, payment_type, amount, currency)
            VALUES (?,?,?,?,?)
        """, (user_id, movie_id, payment_type, amount, currency))
        return cur.lastrowid


def confirm_purchase(purchase_id: int, tx_hash: str = ""):
    with get_conn() as conn:
        conn.execute("""
            UPDATE purchases SET status='confirmed', tx_hash=? WHERE id=?
        """, (tx_hash, purchase_id))


def create_crypto_payment(user_id, purpose, currency, amount, wallet):
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO crypto_payments (user_id, purpose, currency, amount, wallet)
            VALUES (?,?,?,?,?)
        """, (user_id, purpose, currency, amount, wallet))
        return cur.lastrowid


def confirm_crypto_payment(payment_id: int, tx_hash: str):
    with get_conn() as conn:
        conn.execute("""
            UPDATE crypto_payments SET status='confirmed', tx_hash=? WHERE id=?
        """, (tx_hash, payment_id))


def get_pending_crypto_payments():
    with get_conn() as conn:
        return conn.execute("""
            SELECT * FROM crypto_payments WHERE status='pending'
            ORDER BY created_at DESC
        """).fetchall()


# ─── СТАТИСТИКА ────────────────────────────────────────────

def get_stats():
    with get_conn() as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_subs = conn.execute("""
            SELECT COUNT(*) FROM users WHERE sub_until > datetime('now')
        """).fetchone()[0]
        total_movies = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        total_purchases = conn.execute("""
            SELECT COUNT(*) FROM purchases WHERE status='confirmed'
        """).fetchone()[0]
    return {
        "total_users": total_users,
        "active_subs": active_subs,
        "total_movies": total_movies,
        "total_purchases": total_purchases,
    }
