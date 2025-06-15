# StickerDom Helper Scripts

Этот репозиторий содержит набор скриптов на Python, упрощающих автоматическую работу с маркетплейсом стыкеров **StickerDom** и Telegram-ботом `@stickerdom_bot`.

---

## Содержание

1. **`token_manager.py`**  — автоматически обновляет Bearer-токен каждые 30 минут.
2. **`purchase_sticker.py`**  — совершает одну попытку покупки конкретной коллекции/персонажа.
3. **`sticker_monitor.py`**  — следит за появлением новых коллекций и запускает несколько попыток покупки.
4. **`config.py`**  — единственное место, где хранятся ваши учётные данные Telegram.

> **Важно ❗**  Код не использует прокси или обходы лимитов StickerDom/Telegram. Вы берёте на себя ответственность за соблюдение правил площадки.

---

## Быстрый старт

### 1. Клонируйте репозиторий и создайте виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install --upgrade pip
```

### 2. Установите зависимости

```bash
pip install -r requirements.txt
```

### 3. Настройте `config.py`

Скопируйте пример и подставьте свои данные из [my.telegram.org](https://my.telegram.org):

```python
API_ID = 123456  # Ваш api_id
API_HASH = "abcdef0123456789abcdef0123456789"  # Ваш api_hash
SESSION_NAME = "telegram_session"  # Имя файла сессии (.session будет добавлено автоматически)
```

### 4. Получите Bearer-токен

```bash
python token_manager.py
```

Сценарий инициирует веб-вью запрос к боту, получает `tgWebAppData`, обменивает его на Bearer-токен и сохраняет в `bearer_token.txt`. Обновление выполняется в фоне каждые 30 минут.

Остановить можно `Ctrl + C`.

### 5. Тестовая покупка наклейки

```bash
python purchase_sticker.py <collection_id> [character_id]
# пример
python purchase_sticker.py 1234 2
```

Скрипт сформирует ссылку оплаты через API StickerDom и попытается отправить платёж с помощью звёзд Telegram. Если звёзд нет, появится ожидаемая ошибка `PAYMENT_FAILED`.

### 6. Мониторинг новых коллекций

```bash
python sticker_monitor.py
```

Скрипт каждые 5 секунд проверяет следующий `collection_id`, при успехе запускает `PURCHASE_COUNT` (по умолчанию 10) попыток покупки.

---

## Часто задаваемые вопросы

**Где взять `Bearеr` ?** — Запустите `token_manager.py`. Он сам всё сделает.

**Нужен ли прокси/VPN?** — Нет, скрипты используют обычные HTTPS-запросы и MTProto-API.

**Можно ли запустить из Docker?** — Да. Создайте образ на базе `python:3.11`, скопируйте код, установите зависимости, установите переменные окружения или тома для хранения `*.session` и `bearer_token.txt`.

---

## Планы на будущее

* Переписать логику на Node.js/TypeScript (см. GramJS).
* Настроить CI для линтинга и тестов.

---

## Лицензия

MIT License © 2024 