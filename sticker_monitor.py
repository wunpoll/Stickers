import os
import time
import requests
import purchase_sticker
import asyncio
import nest_asyncio
from token_manager import get_bearer
from params import BASE_URL, CHECK_INTERVAL_SECONDS, LAST_ID_FILE, PURCHASE_COUNT, CHARACTER_ID

# --- Configuration ---
# The base URL for the sticker collections API endpoint.
# We will append the sticker ID to this URL.
# BASE_URL = "https://api.stickerdom.store/api/v1/collection/"

# Time to wait in seconds between checks if no new sticker is found.
# CHECK_INTERVAL_SECONDS = 5 

# File to store the ID of the last successfully found sticker.
# LAST_ID_FILE = "last_sticker_id.txt"

# How many times to attempt purchasing each new collection.
# PURCHASE_COUNT = 10

# CHARACTER_ID = 2

# BEARER_TOKEN is now loaded dynamically from a file.

# --- End of Configuration ---

# Конфигурация теперь живёт в params.py

def read_last_id():
    """Reads the last sticker ID from the state file."""
    try:
        with open(LAST_ID_FILE, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        print(f"Warning: Could not read a valid ID from {LAST_ID_FILE}. Starting from ID 0.")
        return 0

def write_last_id(sticker_id):
    """Writes the given sticker ID to the state file."""
    with open(LAST_ID_FILE, 'w') as f:
        f.write(str(sticker_id))

def main():
    """Main monitoring loop."""
    print("--- Sticker Monitor Started ---")
    
    last_id = read_last_id()
    print(f"Starting check from ID: {last_id + 1}")

    # Use a session object for performance improvements (connection reusing).
    session = requests.Session()

    try:
        while True:
            id_to_check = last_id + 1
            url = f"{BASE_URL}{id_to_check}"
            print(url)
            try:
                print(f"Checking for sticker with ID: {id_to_check}...")
                
                # Get the latest token from the helper for each request
                bearer_token = get_bearer()
                headers = {
                    "Authorization": f"Bearer {bearer_token}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                }
                response = session.get(url, headers=headers)

                # Try to parse JSON safely; some 4xx pages may return HTML
                try:
                    data = response.json()
                except ValueError:
                    data = None  # Non-JSON response

                if response.status_code == 200 and data and data.get("ok") is True:
                    print(f"✅ SUCCESS! Found new sticker collection with ID: {id_to_check}")
                    # You could add logic here to do something with the response data,
                    # for example: print(response.json())
                    last_id = id_to_check
                    write_last_id(last_id)
                    for attempt in range(1, PURCHASE_COUNT + 1):
                        print(f"🎯 Purchase attempt {attempt}/{PURCHASE_COUNT} for collection {id_to_check}…")
                        try:
                            # Запускаем напрямую асинхронную функцию purchase_once
                            asyncio.run(purchase_sticker.purchase_once(collection_id=id_to_check, character_id=CHARACTER_ID))
                        except RuntimeError:
                            # Если event-loop уже запущен (редко), разрешаем вложенный запуск
                            nest_asyncio.apply()
                            asyncio.run(purchase_sticker.purchase_once(collection_id=id_to_check, character_id=CHARACTER_ID))
                        except Exception as e:
                            print(f"🚨 Purchase attempt {attempt} failed: {e}")
                        time.sleep(1)  # slight delay between attempts to avoid spamming the API
                    print(f"Finished {PURCHASE_COUNT} purchase attempts for collection {id_to_check}")
                    # Don't wait, immediately check for the next one.
                    continue 

                elif response.status_code == 404 or (data and data.get("ok") is False):
                    print(f"Not found. Waiting {CHECK_INTERVAL_SECONDS} seconds...")
                    time.sleep(CHECK_INTERVAL_SECONDS)

                else:
                    print(f"⚠️  Warning: Received status code {response.status_code}.")
                    print(f"Response: {response.text}")
                    print(f"Waiting {CHECK_INTERVAL_SECONDS} seconds before retrying...")
                    time.sleep(CHECK_INTERVAL_SECONDS)
            
            except (requests.exceptions.RequestException, RuntimeError) as e:
                print(f"🚨 Error: An exception occurred during the request or getting token: {e}")
                print(f"Waiting {CHECK_INTERVAL_SECONDS * 2} seconds before retrying...")
                time.sleep(CHECK_INTERVAL_SECONDS * 2)

    except KeyboardInterrupt:
        print("\n--- Sticker Monitor Stopped ---")

if __name__ == "__main__":
    main() 