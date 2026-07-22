import asyncio
import argparse
import sys
import os
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

async def upload_to_routenote(file_path: str, cover_path: str, track_name: str, artist_name: str):
    print(f"Starting RouteNote Upload for '{track_name}' by '{artist_name}'...")
    
    if not os.path.exists("cookies/routenote_cookies.json"):
        print("ERROR: cookies/routenote_cookies.json not found! Export them using EditThisCookie and save them locally.")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Headful mode for local testing!
        context = await browser.new_context(
            storage_state="cookies/routenote_cookies.json",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            print("Navigating to RouteNote dashboard...")
            await page.goto("https://www.routenote.com/rn/dashboard", wait_until="networkidle")
            
            # Wait to see if we are logged in
            await page.wait_for_timeout(5000)
            
            if "login" in page.url:
                print("ERROR: Cookies are invalid or expired. You were redirected to the login page.")
                await browser.close()
                return
                
            print("Successfully authenticated. Looking for 'Create New Release' button...")
            
            try:
                # First try the generic "Create New Release" link or button
                await page.get_by_role("link", name="Create New Release").click(timeout=10000)
            except PlaywrightTimeoutError:
                print("\n[CRASH LOG] Could not find the 'Create New Release' button.")
                print("ACTION REQUIRED: Look at the browser window. Tell me what the button says, or inspect the HTML!\n")
                
                input("Press ENTER to close the browser...")
                await browser.close()
                return

            print("Clicked Create New Release. Wait for next page...")
            await page.wait_for_timeout(5000)
            
            print("Script reached the end of the initial skeleton!")
            input("Press ENTER to close the browser...")

        except Exception as e:
            print(f"UNEXPECTED ERROR: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True, help="Path to .wav file")
    parser.add_argument("--cover", required=True, help="Path to .png cover art")
    parser.add_argument("--title", required=True, help="Track Title")
    parser.add_argument("--artist", required=True, help="Artist Name")
    args = parser.parse_args()

    asyncio.run(upload_to_routenote(args.audio, args.cover, args.title, args.artist))
