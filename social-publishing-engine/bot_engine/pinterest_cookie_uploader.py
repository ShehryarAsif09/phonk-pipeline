#!/usr/bin/env python3
"""
Multi-Brand Pinterest Uploader using Headless Playwright + Google Chrome.

CRITICAL: Uses channel="chrome" (Google Chrome) instead of the default
Playwright Chromium because Chromium on Linux does NOT include proprietary
H.264/H.265 codecs. Pinterest validates uploaded videos client-side using
a <video> element — if the browser can't decode H.264, Pinterest rejects
the file with "This video isn't encoded in H.264 or H.265" regardless of
the actual encoding. Google Chrome ships with these codecs.

Accepts: --brand <id> --file <path_to_mp4_or_image> --caption <caption_text> --link <url>
Loads: cookies/<brand_id>_pinterest_cookies.json
"""

import argparse
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path("pinterest_debug_screenshots")


def screenshot(page, step_name: str, brand: str):
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    path = SCREENSHOT_DIR / f"{brand}_{step_name}.png"
    page.screenshot(path=str(path), full_page=False)
    print(f"[{brand}] 📸 Screenshot saved: {path}")


def prepare_playwright_storage_state(cookie_path: Path, domain: str) -> str:
    """Auto-converts raw array cookies (EditThisCookie export) into Playwright storage_state format."""
    try:
        data = json.loads(cookie_path.read_text(encoding="utf-8"))
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
                    "sameSite": "Lax",
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
    parser = argparse.ArgumentParser(description="Pinterest Playwright Uploader (Chrome)")
    parser.add_argument("--brand", required=True, help="Brand identifier (e.g. phonk_pipeline)")
    parser.add_argument("--file", required=True, help="Path to MP4 or image file")
    parser.add_argument("--caption", required=True, help="Caption / description text")
    parser.add_argument("--link", default="https://publixion.com", help="Destination link")
    args = parser.parse_args()

    local_file = Path(args.file).resolve()
    if not local_file.exists():
        print(f"[{args.brand}] ❌ ERROR: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    cookie_file = Path("cookies") / f"{args.brand}_pinterest_cookies.json"
    if not cookie_file.exists():
        print(f"[{args.brand}] ❌ ERROR: Cookie file not found at {cookie_file}.", file=sys.stderr)
        sys.exit(1)

    print(f"[{args.brand}] Launching Google Chrome for Pinterest Upload...")
    storage_state_path = prepare_playwright_storage_state(cookie_file, ".pinterest.com")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        context = browser.new_context(
            storage_state=storage_state_path,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
        )

        page = context.new_page()

        try:
            # --- Navigate to Pin Builder ---
            print(f"[{args.brand}] Navigating to Pinterest Pin Builder...")
            page.goto("https://www.pinterest.com/pin-builder/", timeout=60000, wait_until="networkidle")
            screenshot(page, "01_builder_loaded", args.brand)

            # --- Dismiss any tutorial/onboarding popups ---
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)

            # --- Upload File ---
            print(f"[{args.brand}] Attaching file...")
            file_input = page.locator('input[type="file"]')
            file_input.set_input_files(str(local_file))
            page.wait_for_timeout(5000)

            # Dismiss popups again (tutorials can appear after upload)
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            for selector in ['button[aria-label*="close" i]', 'button:has-text("Next")', 'button:has-text("Done")']:
                btn = page.locator(selector)
                for i in range(btn.count()):
                    try:
                        btn.nth(i).click(timeout=500)
                    except Exception:
                        pass
            page.wait_for_timeout(1000)
            screenshot(page, "02_after_file_attached", args.brand)

            # --- Check for video codec rejection ---
            error_el = page.locator('text="This video isn\'t encoded"')
            if error_el.count() > 0:
                print(f"[{args.brand}] ⚠️  Pinterest rejected video encoding. This typically means the browser lacks H.264 codec support.", file=sys.stderr)
                print(f"[{args.brand}] ⚠️  Ensure 'playwright install chrome' is used, NOT 'playwright install chromium'.", file=sys.stderr)
                screenshot(page, "error_codec_rejected", args.brand)
                sys.exit(1)

            # --- Fill Title ---
            print(f"[{args.brand}] Filling title...")
            title_input = page.locator('textarea[placeholder*="title" i], input[placeholder*="title" i]')
            if title_input.count() > 0:
                title_input.first.fill("Gym Phonk Motivation 🔥")

            # --- Fill Description ---
            print(f"[{args.brand}] Filling description...")
            desc_input = page.get_by_placeholder("Tell everyone what your Pin is about")
            if desc_input.count() > 0:
                desc_input.first.fill(args.caption)
            else:
                fallback_desc = page.locator('div[data-test-id="editor-with-mentions"] [contenteditable="true"]')
                if fallback_desc.count() > 0:
                    fallback_desc.first.type(args.caption)

            # --- Fill Link ---
            print(f"[{args.brand}] Filling link...")
            link_input = page.locator('textarea[placeholder*="destination link" i], input[placeholder*="destination link" i]')
            if link_input.count() > 0:
                link_input.first.fill(args.link)

            screenshot(page, "03_after_details_filled", args.brand)

            # --- Publish ---
            print(f"[{args.brand}] Clicking Publish...")
            publish_btn = page.locator('button[data-test-id="board-dropdown-save-button"], button:has-text("Publish")')
            if publish_btn.count() > 0:
                # Check if the button is actually enabled
                is_disabled = publish_btn.first.is_disabled()
                if is_disabled:
                    print(f"[{args.brand}] ⚠️  Publish button is DISABLED. Video may have been rejected or board not selected.", file=sys.stderr)
                    screenshot(page, "04_publish_disabled", args.brand)
                    sys.exit(1)

                publish_btn.first.click()
                print(f"[{args.brand}] Clicked Publish. Waiting for confirmation...")
                page.wait_for_timeout(15000)
            else:
                print(f"[{args.brand}] ❌ Could not find Publish button!", file=sys.stderr)
                screenshot(page, "04_publish_button_missing", args.brand)
                sys.exit(1)

            screenshot(page, "05_final_state", args.brand)

            # --- Verify publish succeeded ---
            current_url = page.url
            if "/pin/" in current_url or "created" in current_url:
                print(f"[{args.brand}] ✅ Pinterest pin published successfully! URL: {current_url}")
            else:
                print(f"[{args.brand}] ⚠️  Publish may not have succeeded. Final URL: {current_url}")

        except Exception as e:
            print(f"[{args.brand}] ❌ Fatal Error: {e}", file=sys.stderr)
            try:
                screenshot(page, "error_fatal", args.brand)
            except Exception:
                pass
            sys.exit(1)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
