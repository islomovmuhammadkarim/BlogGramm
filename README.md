# BlogGram

Yozuvchilar platformasi — Django + Telegram Bot

## Ishga tushirish

```bash
# 1. Venv aktivlashtirish
source venv/bin/activate

# 2. .env faylni sozlash (SITE_URL ni o'zgartiring!)
nano .env

# 3. Server ishga tushirish
python manage.py runserver 0.0.0.0:8000

# 4. Bot ishga tushirish (alohida terminal)
python bot_polling.py
```

## .env sozlamalari

Fayl: `.env` (loyiha root da)

```
SITE_URL=https://yourdomain.com    ← BU YERGA DOMEN YOZING
SECRET_KEY=random-64-belgi
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_BOT_USERNAME=your-bot-username
```

## Admin kirish

- URL: `/dashboard/`
- Login: `/login/` → "Admin login" → `mrton` / `admin123`

## Production deploy

```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn config.wsgi --bind 0.0.0.0:8000
```
