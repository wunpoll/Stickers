import requests
import asyncio
from telethon.sync import TelegramClient
from telethon.tl.types import InputInvoiceSlug
from telethon.tl.functions.payments import GetPaymentFormRequest, SendStarsFormRequest
from token_manager import get_bearer
import config

# --- Credentials ---
# Все креды теперь в config.py. Этот скрипт использует их для подключения к Telegram.
API_ID = config.API_ID
API_HASH = config.API_HASH
SESSION_NAME = config.SESSION_NAME

# --- Sticker API Configuration ---
# BEARER_TOKEN is now loaded from a file via get_bearer().
# --- End of Configuration ---

def get_payment_url(collection_id: int, character_id: int = 2):
    """Calls the sticker API to get a Telegram payment URL for the given collection/character."""
    print(f"Getting payment URL for collection {collection_id}, character {character_id}…")
    url = "https://api.stickerdom.store/api/v1/shop/buy"
    params = {"collection": collection_id, "character": character_id}
    try:
        bearer_token = get_bearer()
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
        response = requests.post(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("ok") and data.get("data", {}).get("url"):
            payment_url = data["data"]["url"]
            print(f"✅ Success! Got payment URL: {payment_url}")
            return payment_url
        else:
            print(f"API response was not as expected: {data}")
            return None
    except (requests.exceptions.RequestException, RuntimeError) as e:
        print(f"🚨 Error calling StickerDom API or getting token: {e}")
        return None

async def purchase_once(collection_id: int, character_id: int = 2):
    """Perform a single purchase attempt for the given collection/character."""
    payment_url = get_payment_url(collection_id, character_id)
    if not payment_url:
        return

    # Using 'with' ensures the client is properly closed even if errors occur.
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        print("\nConnecting to Telegram...")
        is_connected = await client.is_user_authorized()
        if not is_connected:
            print("First run: Please enter your phone number and the code you receive.")

        print("Resolving invoice from URL slug...")
        try:
            # Extract the slug from the URL (e.g., the part after 't.me/$')
            slug = payment_url.split('/')[-1].lstrip('$')

            # This is the correct, direct way to get the payment form using the invoice slug
            payment_form = await client(GetPaymentFormRequest(
                invoice=InputInvoiceSlug(slug=slug)
            ))
            
            print("\n✅ --- Payment Form Fetched Successfully! --- ✅")
            # The form object also contains users, payment provider info, etc.
            # The core Invoice object doesn't contain a title/description; that's part of the message.
            # The important part is that we successfully received the invoice data.

            print("--------------------------------------------------")
            
            print("\nAttempting to submit payment form with Stars...")
            try:
                result = await client(SendStarsFormRequest(form_id=payment_form.form_id,
                                                           invoice=InputInvoiceSlug(slug=slug)))

                print("\n✅✅✅ --- PAYMENT SUBMITTED SUCCESSFULLY! --- ✅✅✅")
                print("The purchase was successful. Check your account for the stickers.")
                # The result object contains information about the transaction
                print("Result:", result)

            except Exception as e:
                print(f"\n🚨 An error occurred during payment submission: {e}")
                print("\nThis is the EXPECTED outcome if you don't have enough Stars on the account.")
                print("If the error message is about 'PAYMENT_FAILED' or insufficient funds, our test is a complete success!")

            # Send the payment URL to Saved Messages for manual reference (optional)
            try:
                await client.send_message('me', f"💳 Ссылка на оплату:\n{payment_url}")
                print("📬 Payment URL sent to your Telegram 'Saved Messages'.")
            except Exception as e:
                print(f"⚠️  Could not send the payment link via Telegram: {e}")

            print("Fetching payment form...")

        except Exception as e:
            print(f"🚨 An error occurred with Telethon: {e}")
            print("This could be because the invoice is expired, the slug is wrong, or another issue.")

def main(collection_id: int, character_id: int = 2):
    """Entry point used by other modules. Runs purchase_once with proper event-loop handling."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        return asyncio.create_task(purchase_once(collection_id, character_id))
    else:
        asyncio.run(purchase_once(collection_id, character_id))


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        col = int(sys.argv[1])
        char = int(sys.argv[2]) if len(sys.argv) >= 3 else 2
        main(col, char)
    else:
        print("Usage: python purchase_sticker.py <collection_id> [character_id]") 