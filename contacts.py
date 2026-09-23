from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = Path(__file__).parent / "whatsapp_profile"

with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
        viewport={"width": 1280, "height": 900},
    )

    page = context.pages[0] if context.pages else context.new_page()

    page.goto(
        "https://web.whatsapp.com",
        wait_until="domcontentloaded"
    )

    print("Waiting for WhatsApp...")

    page.get_by_role(
        "textbox",
        name="Search"
    ).wait_for(
        state="visible",
        timeout=120000
    )

    print("WhatsApp ready.")

    # Get the chat list
    contacts = page.locator(
        '#pane-side [role="listitem"]'
    )

    print("Chat items:", contacts.count())

    names = []

    for i in range(contacts.count()):

        item = contacts.nth(i)

        if not item.is_visible():
            continue

        text = item.inner_text().strip()

        if text:
            # First line is commonly the contact/group name
            name = text.split("\n")[0].strip()

            if name and name not in names:
                names.append(name)

    print("\n===== CONTACTS =====")

    for name in names:
        print(name)

    print("\nTotal:", len(names))

    context.close()