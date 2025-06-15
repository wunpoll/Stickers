# token_manager.py
"""
Полностью автоматический менеджер Bearer-токенов.

Запустите этот файл напрямую (python token_manager.py), и он будет
автоматически получать payload из Telegram и обновлять Bearer-токен
каждые 30 минут.

Другие модули, как и прежде, могут импортировать get_bearer()
для получения актуального токена.
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, unquote

import requests
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest

# Импортируем общие настройки
try:
    import config
except ImportError:
    print("🚨 Не найден файл config.py. Пожалуйста, создайте его, скопировав из config.py.example")
    sys.exit(1)


# --- API details -----------------------------------------------------------
AUTH_URL = "https://api.stickerdom.store/api/v1/auth"
TOKEN_TXT = Path(__file__).with_name("bearer_token.txt")
REFRESH_EVERY = 30 * 2   # 30 минут

# --- Bot Configuration -----------------------------------------------------
BOT_USERNAME = "sticker_bot"  # Публичное @username бота
WEB_APP_URL = "https://app.stickerdom.store/"


# --------------------------------------------------7910-------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_bearer() -> str:
    """Return the last cached Bearer-token (without the leading "Bearer ")."""
    try:
        return TOKEN_TXT.read_text().strip()
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Bearer-токен ещё не получен. Запустите token_manager.py либо "
            "дождитесь первой выдачи токена."
        ) from exc


# ---------------------------------------------------------------------------
# Internal helpers used by the background worker
# ---------------------------------------------------------------------------

async def _fetch_token(tg_client: TelegramClient) -> None:
    """
    1. Получает актуальные данные для авторизации (payload) через Telethon.
    2. Отправляет эти данные на сервер StickerDom для получения Bearer-токена.
    3. Сохраняет токен в файл.
    """
    print("Запрос данных Web App у Telegram...")
    bot_entity = await tg_client.get_entity(BOT_USERNAME)
    result = await tg_client(RequestWebViewRequest(
        peer=bot_entity,
        bot=bot_entity,
        platform="web",
        url=WEB_APP_URL,
    ))
    
    # Нам нужен ИМЕННО закодированный payload (процент-кодирование должно сохраниться),
    # иначе подпись становится недействительной. Берём его напрямую из URL без decode.
    fragment = result.url.split('#', 1)[1]  # часть после #
    for part in fragment.split('&'):
        if part.startswith('tgWebAppData='):
            body_payload_encoded = part[len('tgWebAppData='):]
            break
    else:
        raise RuntimeError('tgWebAppData not found in URL fragment')

    # Для отладки можно посмотреть декодированное содержимое, но на сервер пойдёт кодированное.
    # decoded_debug = unquote(body_payload_encoded)
    # print('DEBUG decoded payload:', decoded_debug)
    body_payload_once = unquote(body_payload_encoded)
            
    body_payload_bytes = body_payload_once.encode('utf-8')

    print("Payload получен. Запрос Bearer-токена с помощью `requests`...")
    print(body_payload_once)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Origin": "https://app.stickerdom.store",
        "Referer": "https://app.stickerdom.store/",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    
    # --- Используем requests в отдельном потоке, чтобы не блокировать asyncio ---
    def do_request():
        # requests ожидает байты для raw data с Content-Type: x-www-form-urlencoded
        return requests.post(AUTH_URL, data=body_payload_bytes, headers=headers)

    resp = await asyncio.to_thread(do_request)
    
    try:
        data = resp.json()
    except requests.exceptions.JSONDecodeError:
        raise RuntimeError(f"Non-JSON response ({resp.status_code} {resp.reason}):\n{resp.text[:300]}")
    
    if resp.status_code != 200 or not data.get("ok"):
        raise RuntimeError(f"Auth failed ({resp.status_code}): {data}")
    
    token = data["data"]
    TOKEN_TXT.write_text(token)
    print(f"[{time.strftime('%H:%M:%S')}] ✅ Bearer token refreshed")


async def _worker() -> None:
    if config.API_ID == 123 or not config.API_HASH:
        print("🚨 ВНИМАНИЕ: Откройте config.py и укажите ваши API_ID и API_HASH.")
        return

    async with TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH) as tg_client:
        me = await tg_client.get_me()
        print(f"Авторизация в Telegram как: {me.first_name}")
        
        while True:
            try:
                await _fetch_token(tg_client)
            except Exception as exc:
                print(f"❌ Token refresh error: {exc}")
            
            print(f"Ожидание {REFRESH_EVERY // 60} минут перед следующим обновлением...")
            await asyncio.sleep(REFRESH_EVERY)


# ---------------------------------------------------------------------------
# Convenience API for running the refresh loop in the background
# ---------------------------------------------------------------------------

def start_background_refresh(loop: asyncio.AbstractEventLoop | None = None) -> None:
    """Spawn the refresh worker as a background task inside *loop*."""
    loop = loop or asyncio.get_event_loop()
    loop.create_task(_worker())


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        asyncio.run(_worker())
    except KeyboardInterrupt:
        print("\n⏹  Token refresh stopped by user") 