"""
⚙️ Конфигурация бота
"""

# ===== ОСНОВНЫЕ НАСТРОЙКИ =====
BOT_TOKEN = "8775148913:AAEgLi86H6j5nqdG6rNRDoBVQNsZ66nNSZw"          # Токен от @BotFather
ADMIN_IDS = [483567956]

# ===== TELEGRAM STARS =====
# Цены в Stars (1 Star ≈ $0.013)
STARS_MONTH  = 250   # ~$3.25/месяц
STARS_YEAR   = 2000  # ~$26/год
STARS_FILM   = 50    # ~$0.65 за фильм

# ===== КРИПТОВАЛЮТА =====
CRYPTO_MONTH_USD  = 3.5    # $3.5/месяц
CRYPTO_YEAR_USD   = 25.0   # $25/год
CRYPTO_FILM_USD   = 0.99   # $0.99 за фильм

# Кошельки
WALLETS = {
    "TON":  "EQCLfvbkTrdUJ1wfyNI9uOdcK30z1wbWWX060mrXBNwp2Tse",
    "USDT": "TXv32UfZBZWcYSLqPtnmZRTeKdZDDjrqbH",
}

# Курс (обновляй вручную или подключи API)
RATES = {
    "TON":  6.5,    # 1 TON = $6.5
    "USDT": 1.0,    # 1 USDT = $1.0
}

# ===== БАЗА ДАННЫХ =====
DB_PATH = "cinema.db"

# ===== НАСТРОЙКИ ПОДПИСКИ =====
SUBSCRIPTION_PLANS = {
    "month": {
        "name": "Месяц",
        "days": 30,
        "stars": STARS_MONTH,
        "usd":  CRYPTO_MONTH_USD,
        "emoji": "📅",
    },
    "year": {
        "name": "Год",
        "days": 365,
        "stars": STARS_YEAR,
        "usd":  CRYPTO_YEAR_USD,
        "emoji": "🗓",
        "badge": "ВЫГОДА -40%",
    },
}

# ===== ТЕХПОДДЕРЖКА =====
SUPPORT_USERNAME = "@your_support_username"
