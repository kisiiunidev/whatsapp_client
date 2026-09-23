from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from pathlib import Path

CONTACT_NAME = "eliezerkenya"
MESSAGE = "😂❤️Hello! This message was sent using Playwright22000"

PROFILE_DIR = Path(__file__).parent / "whatsapp_profile"

def send_whatsapp_message(page, contact_name, message):
    print("Looking for WhatsApp search box...")

    # WhatsApp's search box is usually exposed with an aria-label
    search = page.get_by_role("textbox", name="Search")

    try:
        search.wait_for(state="visible", timeout=30000)
    except PlaywrightTimeoutError:
        print("Could not find the WhatsApp search box.")
        print("Current URL:", page.url)
        page.screenshot(path="whatsapp_error.png")
        raise

    print(f"Searching for: {contact_name}")

    search.click()
    search.fill(contact_name)

    # Give WhatsApp a moment to update the search results
    page.wait_for_timeout(1500)

    # Click the contact from the results
    contact = page.get_by_text(contact_name, exact=True).first

    try:
        contact.wait_for(state="visible", timeout=10000)
        contact.click()
    except PlaywrightTimeoutError:
        print(f"Could not find contact: {contact_name}")
        page.screenshot(path="contact_not_found.png")
        raise

    print(f"Opened chat with {contact_name}")

    # Find the message textbox.
    # There may be several contenteditable elements on the page,
    # so use the textbox role and select the visible one.
    message_box = page.locator(
        'div[contenteditable="true"]'
    ).filter(visible=True).last

    message_box.wait_for(state="visible", timeout=10000)

    message_box.click()
    message_box.fill(message)
    message_box.press("Enter")

    print("Message sent successfully!")

async def send_image(page, recipient, image_path, caption=None):
    """
    Send an image to an individual contact or WhatsApp group.

    recipient:
        Exact contact/group name shown in WhatsApp.

    image_path:
        Path to the image on the Linux server.

    caption:
        Optional text to accompany the image.
    """

    print(f"Sending image to: {recipient}")

    # Search for recipient
    search_box = page.get_by_role("textbox", name="Search")
    await search_box.click()
    await search_box.fill(recipient)

    await page.wait_for_timeout(2000)

    # Open contact/group
    result = page.get_by_text(recipient, exact=True).first
    await result.wait_for(timeout=15_000)
    await result.click()

    await page.wait_for_timeout(1000)

    # Make sure the file exists
    image = Path(image_path)

    if not image.exists():
        raise FileNotFoundError(
            f"Image not found: {image}"
        )

    # Click attachment button
    attach_button = page.get_by_role(
        "button",
        name="Attach"
    )

    await attach_button.click()

    await page.wait_for_timeout(500)

    # Locate the file input.
    # WhatsApp uses a hidden file input for uploads.
    file_input = page.locator(
        'input[type="file"]'
    ).last

    await file_input.set_input_files(
        str(image)
    )

    # Wait for image preview
    await page.wait_for_timeout(1500)

    # Add optional caption
    if caption:
        caption_box = page.locator(
            'div[contenteditable="true"]'
        ).last

        await caption_box.fill(caption)

    # Send the image
    send_button = page.get_by_role(
        "button",
        name="Send"
    )

    await send_button.click()

    print(f"Image sent to: {recipient}")

    await page.wait_for_timeout(1500)
import asyncio
with sync_playwright() as p:
    
    # This profile stores the WhatsApp login session.
    context = p.chromium.launch_persistent_context(
    user_data_dir=str(PROFILE_DIR),
    executable_path=r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    headless=False,
    viewport={
        "width": 1280,
        "height": 900
    },
)

    page = context.pages[0] if context.pages else context.new_page()

    page.goto(
        "https://web.whatsapp.com",
        wait_until="domcontentloaded"
    )

    print("Waiting for WhatsApp Web...")

    # First run:
    # Scan the QR code manually.
    #
    # Instead of checking #side, wait for the search box.
    search = page.get_by_role("textbox", name="Search")

    try:
        search.wait_for(state="visible", timeout=120000)
    except PlaywrightTimeoutError:
        print("WhatsApp did not become ready.")
        page.screenshot(path="whatsapp_login_error.png")
        context.close()
        raise

    print("WhatsApp Web is ready.")

    # send_whatsapp_message(
    #     page,
    #     CONTACT_NAME,
    #     MESSAGE
    # )

    await send_image(page,
        "eliezerkenya",
        "D:\\code\\apps\\headless_whatsapp.png",
        "Here is the latest project update."
    )
    
    # Keep browser open for a few seconds so you can see the result.
    page.wait_for_timeout(5000)

    context.close()