#!/usr/bin/env python3
"""
Multi-Brand LinkedIn Uploader using Headless Playwright Chromium.
Accepts: --brand <id> --file <path_to_mp4> --caption <caption_text>
Loads: cookies/<brand_id>_linkedin_cookies.json
"""

import argparse
import json
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

SCREENSHOT_DIR = Path("linkedin_debug_screenshots")

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
    parser = argparse.ArgumentParser(description="LinkedIn Playwright Uploader")
    parser.add_argument("--brand", required=True, help="Brand identifier (e.g. phonk_pipeline)")
    parser.add_argument("--file", required=True, help="Path to MP4 file")
    parser.add_argument("--caption", required=True, help="Caption text")
    args = parser.parse_args()

    local_file = Path(args.file).resolve()
    if not local_file.exists():
        print(f"[{args.brand}] ❌ ERROR: Video file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    cookie_file = Path("cookies") / f"{args.brand}_linkedin_cookies.json"
    if not cookie_file.exists():
        print(f"[{args.brand}] ❌ ERROR: Cookie file not found at {cookie_file}. Skipping.", file=sys.stderr)
        sys.exit(1)

    print(f"[{args.brand}] Launching Playwright Chromium for LinkedIn Upload...")
    storage_state_path = prepare_playwright_storage_state(cookie_file, ".linkedin.com")

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
            print(f"[{args.brand}] Navigating to LinkedIn Feed...")
            page.goto("https://www.linkedin.com/feed/", timeout=60000, wait_until="networkidle")
            screenshot(page, "01_feed_loaded", args.brand)
            
            # Step 1: Click "Media" or "Start a post"
            print(f"[{args.brand}] Opening post modal...")
            start_post_btn = page.locator('button:has-text("Start a post"), button[aria-label="Start a post"]')
            if start_post_btn.count() > 0:
                start_post_btn.first.click()
            else:
                # Direct media button fallback
                page.locator('button[aria-label="Add media"]').first.click()
                
            page.wait_for_timeout(3000)
            screenshot(page, "02_post_modal_open", args.brand)
            
            # Step 2: Upload File
            print(f"[{args.brand}] Attaching MP4 file...")
            file_input = page.locator('input[type="file"]')
            if file_input.count() > 0:
                file_input.first.set_input_files(str(local_file))
            else:
                # Sometimes LinkedIn needs you to click the add media button inside the modal first
                media_btn = page.locator('button[aria-label="Add media"], button[aria-label="Video"]')
                if media_btn.count() > 0:
                    media_btn.first.click()
                    page.wait_for_timeout(1000)
                    page.locator('input[type="file"]').first.set_input_files(str(local_file))

            page.wait_for_timeout(5000)
            screenshot(page, "03_after_file_attached", args.brand)

            # Step 3: Click Next if in media preview modal
            next_btn = page.locator('button:has-text("Next")')
            if next_btn.count() > 0:
                next_btn.first.click()
                page.wait_for_timeout(2000)

            # Step 4: Fill Caption
            print(f"[{args.brand}] Filling caption...")
            editor = page.locator('div[role="textbox"]')
            if editor.count() > 0:
                editor.first.fill(args.caption)
                
            screenshot(page, "04_after_caption_filled", args.brand)

            # Step 5: Post
            print(f"[{args.brand}] Attempting to click Post...")
            post_btn = page.locator('button:has-text("Post")')
            if post_btn.count() > 0:
                post_btn.first.click(force=True)
                print(f"[{args.brand}] Clicked Post. Waiting 20s for processing...")
                page.wait_for_timeout(20000)
            else:
                print(f"[{args.brand}] Could not find Post button!")
                screenshot(page, "05_post_button_missing", args.brand)

            screenshot(page, "06_final_state", args.brand)
            print(f"[{args.brand}] ✅ LinkedIn upload sequence completed.")

        except Exception as e:
            print(f"[{args.brand}] ❌ Fatal Error during LinkedIn upload: {e}", file=sys.stderr)
            try:
                screenshot(page, "error_fatal", args.brand)
            except:
                pass
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    main()
