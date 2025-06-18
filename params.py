BASE_URL = "https://api.stickerdom.store/api/v1/collection/"

# Time to wait in seconds between checks if no new sticker is found.
CHECK_INTERVAL_SECONDS = 5

# File to store the ID of the last successfully found sticker.
LAST_ID_FILE = "last_sticker_id.txt"

# How many times to attempt purchasing each new collection.
PURCHASE_COUNT = 10

# ID of the character to use in purchase requests.
CHARACTER_ID = 2

# ---------------------------------------------------------------------------
# Token manager / Web-App settings
# ---------------------------------------------------------------------------

AUTH_URL = "https://api.stickerdom.store/api/v1/auth"
WEB_APP_URL = "https://app.stickerdom.store/"

# Public username of the StickerDom bot. Using @username instead of numeric ID
# ensures Telethon can resolve the entity even on fresh sessions.
BOT_USERNAME = "sticker_bot"

# How often, in seconds, to refresh the bearer token (30 minutes by default).
REFRESH_EVERY = 30 * 2  # 30 минут (set small for testing)
