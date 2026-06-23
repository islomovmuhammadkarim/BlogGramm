#!/usr/bin/env python
"""Telegram bot: /start {token} → verify user → link to login session"""
import os, sys, django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import time, requests, json
from django.conf import settings
from django.contrib.auth.models import User
from blog.models import LoginToken, TelegramUser

TOKEN = settings.TELEGRAM_BOT_TOKEN
API = f'https://api.telegram.org/bot{TOKEN}'


def send(chat_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        payload['reply_markup'] = reply_markup
    r = requests.post(f'{API}/sendMessage', json=payload, timeout=10)
    if not r.json().get('ok'):
        print(f'⚠ Send failed: {r.json()}')


def handle(update):
    # callback queries
    cb = update.get('callback_query')
    if cb:
        cb_data = cb.get('data', '')
        cb_chat = cb['message']['chat']['id']
        site_url = settings.SITE_URL
        if cb_data == 'login':
            markup = json.dumps({'inline_keyboard': [[{'text': '🌐 Saytni ochish', 'url': f'{site_url}/login/'}]]})
            send(cb_chat, '🔐 Login sahifasini oching:', reply_markup=markup)
        elif cb_data == 'explore':
            markup = json.dumps({'inline_keyboard': [[{'text': '📖 Saytni ochish', 'url': f'{site_url}/explore/'}]]})
            send(cb_chat, '📖 Explore sahifasini oching:', reply_markup=markup)
        requests.post(f'{API}/answerCallbackQuery', json={'callback_query_id': cb['id']}, timeout=5)
        return

    msg = update.get('message', {})
    chat_id = msg.get('chat', {}).get('id')
    if not chat_id:
        return

    text = msg.get('text', '')
    first_name = msg.get('from', {}).get('first_name', '')
    tg_username = msg.get('from', {}).get('username', '')
    tg_id = msg.get('from', {}).get('id', chat_id)

    # /start with token (saytdan kelgan deep link)
    if text.startswith('/start '):
        token = text.split(' ', 1)[1].strip()
        try:
            lt = LoginToken.objects.get(token=token, verified=False)
        except LoginToken.DoesNotExist:
            # Token noto'g'ri — oddiy start ga o'tish
            _handle_start(chat_id, first_name, tg_username, tg_id)
            return

        if lt.is_expired():
            lt.delete()
            _handle_start(chat_id, first_name, tg_username, tg_id)
            return

        # get or create user
        user = _get_or_create_user(tg_id, first_name, tg_username)

        # verify token
        lt.user = user
        lt.verified = True
        lt.save()

        send(chat_id, f'✅ <b>Muvaffaqiyatli!</b>\n\n{first_name}, siz tizimga kirdingiz. 🎉',
            reply_markup=json.dumps({'inline_keyboard': [[
                {'text': '🌐 Saytga o\'tish', 'url': f'{settings.SITE_URL}/'}
            ]]})
        )

    elif text == '/start' or text.startswith('/start'):
        _handle_start(chat_id, first_name, tg_username, tg_id)

    elif text == '/help':
        site_url = settings.SITE_URL
        send(chat_id,
            f'📚 <b>BlogGram Bot — Yordam</b>\n\n'
            f'<b>🤖 Bot komandalar:</b>\n'
            f'/start — Ro\'yxatdan o\'tish va saytga kirish\n'
            f'/help — Yordam (shu xabar)\n\n'
            f'<b>🌐 Sayt imkoniyatlari:</b>\n'
            f'✍️ Post yozish, 📢 Stories, 💬 DM\n'
            f'🔖 Bookmarks, 🔔 Notifications\n'
            f'🔄 Repost, 🔍 Explore, 🏷️ Tags\n'
            f'📅 Scheduled posts, 🌍 3 til (UZ/RU/EN)\n\n'
            f'🔗 <b>Sayt:</b> {site_url}',
            reply_markup=json.dumps({'inline_keyboard': [[
                {'text': '🌐 Saytga o\'tish', 'url': f'{site_url}/'}
            ]]})
        )
    else:
        send(chat_id, '💡 /start — kirish | /help — yordam')


def _get_or_create_user(tg_id, first_name, tg_username):
    try:
        tg_user = TelegramUser.objects.get(telegram_id=tg_id)
        user = tg_user.user
        tg_user.first_name = first_name
        tg_user.username = tg_username
        tg_user.save()
    except TelegramUser.DoesNotExist:
        username = f'id{tg_id}'
        user = User.objects.create_user(username=username, first_name=first_name)
        TelegramUser.objects.create(user=user, telegram_id=tg_id, first_name=first_name, username=tg_username)
    return user


def _handle_start(chat_id, first_name, tg_username, tg_id):
    import secrets
    site_url = settings.SITE_URL
    user = _get_or_create_user(tg_id, first_name, tg_username)
    token = secrets.token_urlsafe(32)
    LoginToken.objects.create(token=token, user=user, verified=True)
    login_url = f'{site_url}/auto-login/{token}/'

    markup = json.dumps({'inline_keyboard': [
        [{'text': '🌐 Saytga kirish', 'url': login_url}],
    ]})
    send(chat_id,
        f'👋 Salom <b>{first_name}</b>!\n\n'
        f'📝 <b>BlogGram</b> — yozuvchilar platformasi.\n\n'
        f'👇 Tugmani bosing — avtomatik kirasiz:',
        reply_markup=markup
    )


def main():
    print(f'🤖 Bot started (@{settings.TELEGRAM_BOT_USERNAME})')
    requests.get(f'{API}/deleteWebhook', timeout=10)
    offset = 0
    session = requests.Session()
    while True:
        try:
            resp = session.get(f'{API}/getUpdates', params={
                'offset': offset, 'timeout': 5
            }, timeout=15)
            for u in resp.json().get('result', []):
                try:
                    handle(u)
                except Exception as e:
                    import traceback
                    print(f'⚠ {e}\n{traceback.format_exc()}')
                offset = u['update_id'] + 1
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f'⚠ {e}')
            session.close()
            session = requests.Session()
            time.sleep(1)


if __name__ == '__main__':
    main()
