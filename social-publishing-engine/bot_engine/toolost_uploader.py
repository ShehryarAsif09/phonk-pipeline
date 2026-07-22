import asyncio
import random
import os
import sys
import argparse
import json
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Simulated human typing function to bypass bot detection
async def human_type(element, text):
    for char in text:
        await element.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.15))

async def upload_to_toolost(audio_path: str, cover_path: str, track_name: str, artist_name: str):
    print(f"Starting TooLost Upload for '{track_name}' by '{artist_name}'...")
    
    # In cloud (GitHub Actions), cookies are created in the workflow from a Secret
    cookie_path = "cookies/toolost_cookies.json"
    if not os.path.exists(cookie_path):
        print(f"ERROR: {cookie_path} not found! You must provide session cookies.")
        sys.exit(1)

    async with async_playwright() as p:
        # We run headless in the cloud, but with specific stealth arguments
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled", 
                "--no-sandbox",
                "--disable-infobars"
            ]
        )
        
        # Load cookies to bypass login
        context = await browser.new_context(
            storage_state=cookie_path,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        try:
            print("[TooLost Bot] Navigating to TooLost Dashboard...")
            await page.goto("https://toolost.com/user/releases", wait_until="networkidle")
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            # Check if login redirect happened (meaning cookies are invalid)
            if "login" in page.url.lower():
                print("ERROR: Cookies are expired or invalid. You were redirected to the login page.")
                await browser.close()
                sys.exit(1)
                
            print("[TooLost Bot] Successfully authenticated!")
            
            # Since we can't see the exact HTML, this is a generic script framework
            # that we will refine once we get the exact CSS selectors from the user.
            print("[TooLost Bot] Waiting for 'New Release' button (Generic Strategy)...")
            
            try:
                # Common selectors for creating a new release
                new_release_btn = page.get_by_text("New Release")
                await new_release_btn.click(timeout=10000)
            except PlaywrightTimeoutError:
                print("\n[CRASH LOG] Could not find the 'New Release' button.")
                print("ACTION REQUIRED: We need the exact HTML classes for the TooLost dashboard.")
                await browser.close()
                sys.exit(1)

            print("[TooLost Bot] Clicked New Release. Typing track metadata...")
            await asyncio.sleep(random.uniform(2.0, 3.0))
            
            # Example: finding the title input box
            try:
                title_input = page.locator("input[name='title'], input[placeholder*='Release Title']")
                await title_input.click()
                await human_type(title_input, track_name)
            except Exception as e:
                print(f"[TooLost Bot] Warning: Could not type title automatically: {e}")
            
            print("[TooLost Bot] Draft creation logic complete.")
            # We will expand the file upload section once the basic navigation is confirmed working.

        except Exception as e:
            print(f"UNEXPECTED ERROR: {e}")
            sys.exit(1)
        finally:
            await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True, help="Path to .wav file")
    parser.add_argument("--cover", required=True, help="Path to .png cover art")
    parser.add_argument("--title", required=True, help="Track Title")
    parser.add_argument("--artist", required=True, help="Artist Name")
    args = parser.parse_args()

    asyncio.run(upload_to_toolost(args.audio, args.cover, args.title, args.artist))
