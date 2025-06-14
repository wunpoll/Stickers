# token_manager.py
"""Centralised Bearer-token helper.

1. Запускайте этот файл напрямую (python token_manager.py) — он будет
   раз в 30 минут запрашивать новый Bearer-токен и сохранять его в
   bearer_token.txt рядом с собой.
2. В других модулях просто импортируйте get_bearer() чтобы получить
   актуальный токен. Если хотите, чтобы обновление работало в фоне,
   вызовите start_background_refresh() в уже запущенном asyncio-цикле.
"""
from __future__ import annotations

import asyncio
import json
import time
import urllib.parse
from pathlib import Path

import aiohttp

# Where the token is cached
TOKEN_TXT = Path(__file__).with_name("bearer_token.txt")

# ---  API details -----------------------------------------------------------
AUTH_URL = "https://api.stickerdom.store/api/v1/auth"
REFRESH_EVERY = 30 * 60  # 30 минут

# !!!  ✨  Подставьте реальные значения из Telegram Web-App   ✨
# RAW_PAYLOAD может быть либо dict, либо готовой query-строкой (str).
# Чтобы не приходилось вручную разбирать, допустим оба варианта.
# Пример строки (обновите на актуальную из Web-App):
#   "query_id=...&user=%7B...%7D&auth_date=...&signature=...&hash=..."
RAW_PAYLOAD: object = (
    "query_id=AAFc4tx3AAAAAFzi3He9l9xO&user=%7B%22id%22%3A2010964572%2C%22first_name%22%3A%22%C2%A5%26%24%22%2C%22last_name%22%3A%22%22%2C%22username%22%3A%22dafawq%22%2C%22language_code%22%3A%22en%22%2C%22is_premium%22%3Atrue%2C%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2Fl89qmw7-Ih_rT3uDNXFXR2NTGk6_w3zvh1l71fQNmX8.svg%22%7D&auth_date=1749944275&signature=9WK5kGOri4lHUd7NQ-4JOup6f8X50qmE99G7bTUlXJxNN9HOaRKi9jUSBOxRKqA4d8Pwk9RXQNkWTXZy4MBpAw&hash=7a69361099e678b0bc5af3af6f66629ac7858293620a8512fe332a087d43b1ca"
)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
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

def _build_body() -> str:
    """Вернуть тело запроса для AUTH_URL.

    Если RAW_PAYLOAD — строка (уже готовая query-строка), отдаём её как есть.
    Иначе считаем, что это словарь и кодируем в x-www-form-urlencoded.
    """
    if isinstance(RAW_PAYLOAD, str):
        return RAW_PAYLOAD

    return urllib.parse.urlencode(
        {k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in RAW_PAYLOAD.items()}
    )


async def _fetch_token(session: aiohttp.ClientSession) -> None:
    """Сделать запрос на AUTH_URL и сохранить Bearer-токен.

    Сервер иногда возвращает заголовок *Content-Type: text/plain*, хотя тело
    содержит JSON. `aiohttp.ClientResponse.json()` по умолчанию считает это
    ошибкой, поэтому принудительно разрешаем декодирование через
    `content_type=None`.
    """
    body = _build_body()
    # Сервер блокирует "голые" запросы без User-Agent и других заголовков,
    # которые обычно присылает браузер. Добавляем их, чтобы имитировать
    # легитимный запрос из Web-App.
    # Если знаете точный Referer/Origin, подставьте сюда.
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Origin": "https://app.stickerdom.store",
        "Referer": "https://app.stickerdom.store/",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    async with session.post(AUTH_URL, data=body, headers=headers) as resp:
        try:
            # Даже при ошибочных статусах сервер отдаёт полезный JSON.
            data = await resp.json(content_type=None)
        except (aiohttp.ContentTypeError, ValueError):
            # Получили не-JSON или пустой ответ – выводим первые 300 символов
            raw = await resp.text()
            raise RuntimeError(
                f"Non-JSON response ({resp.status} {resp.reason}):\n{raw[:300]}"
            )

        if resp.status != 200 or not data.get("ok"):
            raise RuntimeError(f"Auth failed ({resp.status}): {data}")

        token = data["data"]
        TOKEN_TXT.write_text(token)
        print(f"[{time.strftime('%H:%M:%S')}] ✅ Bearer token refreshed")


async def _worker() -> None:
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await _fetch_token(session)
            except Exception as exc:  # pylint: disable=broad-except
                print(f"❌ Token refresh error: {exc}")
            await asyncio.sleep(REFRESH_EVERY)


# ---------------------------------------------------------------------------
# Convenience API for running the refresh loop in the background
# ---------------------------------------------------------------------------

def start_background_refresh(loop: asyncio.AbstractEventLoop | None = None) -> None:
    """Spawn the refresh worker as a background task inside *loop*.

    Example:
        >>> asyncio.run(your_main())

    Make sure this function is called *after* the event-loop has started.
    """
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