# 🎬 CinemaBot — Telegram Онлайн Кинотеатр

Платный кинотеатр в Telegram с оплатой через **Telegram Stars** и **криптовалюту** (TON/USDT).

---

## 📁 Структура проекта

```
cinema_bot/
├── bot.py              # Точка входа
├── config.py           # Настройки (токен, цены, кошельки)
├── database.py         # SQLite база данных
├── keyboards.py        # Все клавиатуры
├── requirements.txt    # Зависимости
└── handlers/
    ├── start.py        # Старт и главное меню
    ├── catalog.py      # Каталог фильмов
    ├── subscription.py # Подписка + Stars-оплата
    ├── cabinet.py      # Личный кабинет
    ├── payment.py      # Крипто-платежи за фильмы
    └── admin.py        # Панель администратора
```

---

## 🚀 Установка

### 1. Установи зависимости
```bash
pip install -r requirements.txt
```

### 2. Настрой config.py
```python
BOT_TOKEN = "твой_токен_от_BotFather"
ADMIN_IDS = [твой_telegram_id]

WALLETS = {
    "TON":  "твой_TON_кошелёк",
    "USDT": "твой_USDT_TRC20_кошелёк",
}
```

### 3. Настрой Telegram Stars
- Открой @BotFather
- `/mybots` → выбери бота → Payments → **Telegram Stars**

### 4. Запусти бота
```bash
python bot.py
```

---

## ⚙️ Настройка цен

В `config.py`:
```python
STARS_MONTH = 250    # цена подписки/месяц в Stars
STARS_YEAR  = 2000   # цена подписки/год в Stars
STARS_FILM  = 50     # цена одного фильма в Stars

CRYPTO_MONTH_USD = 3.5   # цена подписки/месяц в USD
CRYPTO_YEAR_USD  = 25.0  # цена подписки/год в USD
CRYPTO_FILM_USD  = 0.99  # цена одного фильма в USD
```

---

## 🎬 Добавление фильмов

**Через команду бота:**
```
/addmovie
```
Бот спросит всё по шагам: название, описание, жанр, год, рейтинг, длительность, ссылку на видео, цену.

**Видео можно добавить двумя способами:**
1. `file_id` — загрузи видео боту, скопируй file_id из логов
2. Прямая ссылка на `.mp4` файл (хостинг)

---

## 👮 Команды администратора

| Команда | Описание |
|---------|----------|
| `/admin` | Панель со статистикой |
| `/addmovie` | Добавить фильм |
| `/pending` | Ожидающие крипто-платежи |
| `/giveaccess 123456 30` | Выдать подписку на 30 дней |
| `/broadcast текст` | Рассылка всем пользователям |

---

## 💳 Как работает оплата

### Telegram Stars
- Встроенная оплата Telegram — мгновенно, автоматически
- Настрой через @BotFather → Payments → Stars

### Криптовалюта (TON/USDT)
1. Пользователь получает адрес кошелька и сумму
2. Переводит крипту
3. Нажимает «Я оплатил» и присылает хэш транзакции
4. Администратор получает уведомление с кнопками ✅/❌
5. После подтверждения — доступ открывается автоматически

---

## 🔒 Безопасность
- Проверяй хэши транзакций через [TONScan](https://tonscan.org) или [Tronscan](https://tronscan.org)
- Храни `BOT_TOKEN` в переменных окружения (`.env`) в продакшене
- Делай бэкап `cinema.db` регулярно

---

## 🌐 Деплой на сервер

```bash
# systemd service
[Unit]
Description=CinemaBot

[Service]
WorkingDirectory=/path/to/cinema_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```
