import asyncio
import os
import threading
from pathlib import Path
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify
from playwright.async_api import async_playwright

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

PROFILE_DIR = BASE_DIR / "whatsapp_profile"

CHROME_PATH = (
    "/usr/bin/google-chrome"
)
API_KEY = os.environ.get("WHATSAPP_API_KEY")
HOST = "0.0.0.0"
PORT = 5000


app = Flask(__name__)


playwright_instance = None
context = None
page = None

whatsapp_ready = False

# Messages captured by the listener
received_messages = []

# Prevent simultaneous WhatsApp operations
whatsapp_lock = None

# Background asyncio loop
loop = None

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        supplied_key = request.headers.get("X-API-Key")

        if not API_KEY or supplied_key != API_KEY:
            return jsonify({
                "success": False,
                "error": "Unauthorized"
            }), 401

        return f(*args, **kwargs)

    return decorated
  
async def send_message(page, recipient, message):

    search = page.get_by_role("textbox", name="Search")

    await search.fill(recipient)

    await page.wait_for_timeout(1000)

    await page.get_by_text(
        recipient,
        exact=True
    ).first.click()

    await page.wait_for_timeout(1000)

    composer = page.locator(
        'div[contenteditable="true"]'
    ).last

    await composer.fill(message)

    await composer.press("Enter")

    await page.wait_for_timeout(1000)


async def send_image(
    page,
    recipient,
    image_path,
    caption=None
):

    search = page.get_by_role("textbox", name="Search")

    await search.fill(recipient)

    await page.wait_for_timeout(1000)

    await page.get_by_text(
        recipient,
        exact=True
    ).first.click()

    await page.wait_for_timeout(1000)

    # Open attachment menu
    await page.get_by_role(
        "button",
        name="Attach"
    ).click()

    await page.wait_for_timeout(500)

    # Select image
    file_input = page.locator(
        'input[type="file"]'
    ).last

    await file_input.set_input_files(
        str(image_path)
    )

    # Wait for image preview
    await page.wait_for_timeout(2000)

    # Add caption
    if caption:

        caption_box = page.locator(
            'div[contenteditable="true"]'
        ).last

        await caption_box.fill(caption)

    # WhatsApp currently exposes multiple Send buttons.
    # Use the first matching Send button.
    send_button = page.get_by_role(
        "button",
        name="Send"
    ).first

    await send_button.wait_for(
        state="visible",
        timeout=10000
    )

    await send_button.click()

    await page.wait_for_timeout(2000)


async def read_new_messages(page):

    seen_messages = set()

    while True:

        try:

            # Incoming WhatsApp messages
            incoming = page.locator(
                "div.message-in"
            )

            count = await incoming.count()

            for i in range(count):

                message_element = incoming.nth(i)

                try:

                    text = await message_element.inner_text()

                    text = text.strip()

                    if not text:
                        continue

                    # Avoid processing the same message repeatedly
                    if text in seen_messages:
                        continue

                    seen_messages.add(text)

                    # Keep memory from growing forever
                    if len(seen_messages) > 1000:

                        seen_messages = set(
                            list(seen_messages)[-500:]
                        )

                    message_data = {
                        "message": text,
                        "timestamp": datetime.now().isoformat()
                    }

                    received_messages.append(
                        message_data
                    )

                    # Keep only the latest 500 messages
                    if len(received_messages) > 500:

                        del received_messages[:-500]

                    print(
                        f"[INCOMING] {text}"
                    )

                except Exception:
                    pass

            await asyncio.sleep(2)

        except Exception as e:

            print(
                f"[MESSAGE LISTENER ERROR] {e}"
            )

            await asyncio.sleep(5)

async def whatsapp_worker():

    global playwright_instance
    global context
    global page
    global whatsapp_ready
    global whatsapp_lock

    whatsapp_lock = asyncio.Lock()

    print("Starting Playwright...")

    playwright_instance = await async_playwright().start()

    context = await playwright_instance.chromium.launch_persistent_context(

        user_data_dir=str(PROFILE_DIR),

        executable_path=CHROME_PATH,

        headless=True,

        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage"
        ],

        viewport={
            "width": 1280,
            "height": 900
        }
    )

    page = await context.new_page()

    print("Opening WhatsApp Web...")

    await page.goto(
        "https://web.whatsapp.com"
    )

    print("Waiting for WhatsApp Web...")

    try:

        await page.locator("#side").wait_for(
            state="visible",
            timeout=120000
        )

        whatsapp_ready = True

        print(
            "WhatsApp is ready!"
        )

    except Exception as e:

        whatsapp_ready = False

        print(
            "WhatsApp did not become ready."
        )

        print(e)

        return

    # Start incoming message listener
    await read_new_messages(page)


# ============================================================
# START ASYNCIO THREAD
# ============================================================

def start_whatsapp():

    global loop

    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)

    loop.run_until_complete(
        whatsapp_worker()
    )


def run_async(coro):

    if loop is None:

        raise RuntimeError(
            "WhatsApp event loop is not running."
        )

    future = asyncio.run_coroutine_threadsafe(
        coro,
        loop
    )

    return future.result()



@app.get("/status")
def status():

    return jsonify({
        "success": True,
        "whatsapp_ready": whatsapp_ready,
        "messages_received": len(received_messages)
    })



@app.post("/send")
@require_api_key
def api_send():

    if not whatsapp_ready:

        return jsonify({
            "success": False,
            "error": "WhatsApp is not ready"
        }), 503

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "error": "JSON body required"
        }), 400

    recipient = data.get(
        "recipient"
    )

    message = data.get(
        "message"
    )

    if not recipient:

        return jsonify({
            "success": False,
            "error": "recipient is required"
        }), 400

    if not message:

        return jsonify({
            "success": False,
            "error": "message is required"
        }), 400

    async def operation():

        async with whatsapp_lock:

            await send_message(
                page,
                recipient,
                message
            )

    try:

        run_async(operation())

        return jsonify({
            "success": True,
            "recipient": recipient,
            "message": message
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.post("/send-image")
@require_api_key
def api_send_image():

    if not whatsapp_ready:

        return jsonify({
            "success": False,
            "error": "WhatsApp is not ready"
        }), 503

    recipient = request.form.get(
        "recipient"
    )

    caption = request.form.get(
        "caption"
    )

    image = request.files.get(
        "image"
    )

    if not recipient:

        return jsonify({
            "success": False,
            "error": "recipient is required"
        }), 400

    if not image:

        return jsonify({
            "success": False,
            "error": "image file is required"
        }), 400

    # Create temporary upload directory
    upload_dir = BASE_DIR / "uploads"

    upload_dir.mkdir(
        exist_ok=True
    )

    # Keep original filename
    filename = Path(
        image.filename
    ).name

    image_path = upload_dir / filename

    image.save(
        str(image_path)
    )

    async def operation():

        async with whatsapp_lock:

            await send_image(
                page,
                recipient,
                image_path,
                caption
            )

    try:

        run_async(operation())

        return jsonify({
            "success": True,
            "recipient": recipient,
            "filename": filename,
            "caption": caption
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.get("/messages")
@require_api_key
def api_messages():

    limit = request.args.get(
        "limit",
        default=50,
        type=int
    )

    if limit < 1:
        limit = 1

    if limit > 500:
        limit = 500

    return jsonify({
        "success": True,
        "count": min(
            limit,
            len(received_messages)
        ),
        "messages": received_messages[-limit:]
    })


if __name__ == "__main__":

    print()
    print("==============================")
    print(" WhatsApp Flask API")
    print("==============================")
    print()

    # Start WhatsApp/Playwright in background
    whatsapp_thread = threading.Thread(
        target=start_whatsapp,
        daemon=True
    )

    whatsapp_thread.start()

    print(
        f"Starting Flask API on "
        f"http://{HOST}:{PORT}"
    )

    app.run(
        host=HOST,
        port=PORT,
        debug=False,
        threaded=True,
        use_reloader=False
    )