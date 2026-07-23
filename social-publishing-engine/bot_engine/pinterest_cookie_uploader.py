#!/usr/bin/env python3
"""
Multi-Brand Pinterest Uploader using Headless Playwright Chromium.
Accepts: --brand <id> --file <path_to_mp4> --caption <caption_text> --link <url>
Loads: cookies/<brand_id>_pinterest_cookies.json
"""

import argparse
import json
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

SCREENSHOT_DIR = Path("pinterest_debug_screenshots")

def screenshot(page, step_name: str, brand: str):
    """Capture a debug screenshot and log its path."""
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    path = SCREENSHOT_DIR / f"{brand}_{step_name}.png"
    page.screenshot(path=str(path), full_page=False)
    print(f"[{brand}] 📸 Screenshot saved: {path}")

def prepare_playwright_storage_state(cookie_path: Path, domain: str) -> str:
    """Auto-converts raw array cookies (EditThisCookie) into Playwright storage_state dict."""
    try:
        raw_text = cookie_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)

        if isinstance(data, list):
            formatted_cookies = []
            for c in data:
                cookie = {
                    "name": c.get("name"),
                    "value": c.get("value"),
                    "domain": c.get("domain", domain),
                    "path": c.get("path", "/"),
                    "secure": c.get("secure", True),
                    "httpOnly": c.get("httpOnly", False),
                    "sameSite": "Lax"
                }
                if "expirationDate" in c:
                    cookie["expires"] = int(c["expirationDate"])
                formatted_cookies.append(cookie)

            storage_dict = {"cookies": formatted_cookies, "origins": []}
            prepared_path = cookie_path.parent / f"playwright_{cookie_path.name}"
            prepared_path.write_text(json.dumps(storage_dict), encoding="utf-8")
            return str(prepared_path)
    except Exception as e:
        print(f"Warning normalizing cookie format: {e}", file=sys.stderr)

    return str(cookie_path)


def main():
    parser = argparse.ArgumentParser(description="Pinterest Playwright Uploader")
    parser.add_argument("--brand", required=True, help="Brand identifier (e.g. phonk_pipeline)")
    parser.add_argument("--file", required=True, help="Path to MP4 file")
    parser.add_argument("--caption", required=True, help="Caption text")
    parser.add_argument("--link", default="https://publixion.com", help="Destination link")
    args = parser.parse_args()

    local_file = Path(args.file).resolve()
    if not local_file.exists():
        print(f"[{args.brand}] ❌ ERROR: Video file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    cookie_file = Path("cookies") / f"{args.brand}_pinterest_cookies.json"
    if not cookie_file.exists():
        print(f"[{args.brand}] ❌ ERROR: Cookie file not found at {cookie_file}. Skipping.", file=sys.stderr)
        sys.exit(1)

    print(f"[{args.brand}] Launching Playwright Chromium for Pinterest Upload...")
    storage_state_path = prepare_playwright_storage_state(cookie_file, ".pinterest.com")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        context = browser.new_context(
            storage_state=storage_state_path,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )

        page = context.new_page()

        try:
            print(f"[{args.brand}] Navigating to Pinterest Pin Builder...")
            page.goto("https://www.pinterest.com/pin-builder/", timeout=60000, wait_until="networkidle")
            screenshot(page, "01_builder_loaded", args.brand)
            
            # Step 1: Upload File
            print(f"[{args.brand}] Attaching MP4 file...")
            file_input = page.locator('input[type="file"]')
            file_input.set_input_files(str(local_file))
            page.wait_for_timeout(5000)
            screenshot(page, "02_after_file_attached", args.brand)
            
            # Step 2: Fill Title
            print(f"[{args.brand}] Filling title...")
            title_input = page.locator('textarea[placeholder*="title" i], input[placeholder*="title" i]')
            if title_input.count() > 0:
                title_input.first.fill("Gym Phonk Motivation 🔥")
            
            # Step 3: Fill Description
            print(f"[{args.brand}] Filling description...")
            desc_input = page.locator('div[data-test-id="editor-with-mentions"] [contenteditable="true"]')
            if desc_input.count() > 0:
                desc_input.first.type(args.caption)
            else:
                fallback_desc = page.locator('textarea[placeholder*="Tell everyone" i]')
                if fallback_desc.count() > 0:
                    fallback_desc.first.fill(args.caption)
            
            # Step 4: Fill Link
            print(f"[{args.brand}] Filling link...")
            link_input = page.locator('textarea[placeholder*="destination link" i], input[placeholder*="destination link" i]')
            if link_input.count() > 0:
                link_input.first.fill(args.link)
                
            screenshot(page, "03_after_details_filled", args.brand)

            # Step 5: Select Board (Optional - usually remembers last, but let's try to just hit publish)
            print(f"[{args.brand}] Attempting to click Publish...")
            publish_btn = page.locator('button[data-test-id="board-dropdown-save-button"]')
            if publish_btn.count() == 0:
                publish_btn = page.locator('button:has-text("Save")')
            
            if publish_btn.count() > 0:
                publish_btn.first.click(force=True)
                print(f"[{args.brand}] Clicked Publish/Save. Waiting 20s for processing...")
                page.wait_for_timeout(20000)
            else:
                print(f"[{args.brand}] Could not find Publish button!")
                screenshot(page, "04_publish_button_missing", args.brand)

            screenshot(page, "05_final_state", args.brand)
            print(f"[{args.brand}] ✅ Pinterest upload sequence completed.")

        except Exception as e:
            print(f"[{args.brand}] ❌ Fatal Error during Pinterest upload: {e}", file=sys.stderr)
            try:
                screenshot(page, "error_fatal", args.brand)
            except:
                pass
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    main()
