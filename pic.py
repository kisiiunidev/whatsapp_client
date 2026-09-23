
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / "whatsapp_profile"
CHROME_PATH = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"


async def send_message(page, recipient, message):
    search = page.get_by_role("textbox", name="Search")
    await search.fill(recipient)
    await page.wait_for_timeout(1000)

    await page.get_by_text(recipient, exact=True).first.click()
    await page.wait_for_timeout(1000)

    composer = page.locator('div[contenteditable="true"]').last
    await composer.fill(message)
    await composer.press("Enter")

    await page.wait_for_timeout(1000)


async def send_image(page, recipient, image_path, caption=None):
    # Search for recipient
    search = page.get_by_role("textbox", name="Search")
    await search.fill(recipient)
    await page.wait_for_timeout(1000)

    # Open chat
    await page.get_by_text(recipient, exact=True).first.click()
    await page.wait_for_timeout(1000)

    # Open attachment menu
    await page.get_by_role("button", name="Attach").click()
    await page.wait_for_timeout(500)

    # Select image
    file_input = page.locator('input[type="file"]').last
    await file_input.set_input_files(str(image_path))

    # Wait for image preview to appear
    await page.wait_for_timeout(2000)

    # Add caption if provided
    if caption:
        caption_box = page.locator('div[contenteditable="true"]').last
        await caption_box.fill(caption)

    # WhatsApp can have two Send buttons:
    # 1. Send 1 selected - image preview
    # 2. Send - normal message composer
    #
    # Select the first matching Send button.
    send_button = page.get_by_role("button", name="Send").first

    await send_button.wait_for(
        state="visible",
        timeout=10000
    )

    await send_button.click()

    await page.wait_for_timeout(2000)

    print(f"Image sent to {recipient}")


async def main():

    messages = [
        {
            "recipient": "Eliezer Kitendawili",
            "message": "Hello eliezerkenya!"
        },
    ]

    images = [
        {
            "recipient": "Eliezer Kitendawili",
            "image": BASE_DIR / "IMG_20260911_223518_678.webp",
            "caption": "Here is the photo."
        },
    ]

    async with async_playwright() as p:

        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            executable_path=CHROME_PATH,
            headless=False,
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

        await page.goto("https://web.whatsapp.com")

        print("Waiting for WhatsApp Web...")

        await page.locator("#side").wait_for(
            state="visible",
            timeout=120000
        )

        print("WhatsApp is ready!")

        # Send text messages
        for item in messages:
            print(f"Sending message to {item['recipient']}...")

            await send_message(
                page,
                item["recipient"],
                item["message"]
            )

        # Send images
        for item in images:
            print(f"Sending image to {item['recipient']}...")

            await send_image(
                page,
                item["recipient"],
                item["image"],
                item["caption"]
            )

        print("All messages and images sent.")

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
