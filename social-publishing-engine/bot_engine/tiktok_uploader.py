#!/usr/bin/env python3
"""
Multi-Brand TikTok Uploader using Headless Playwright Chromium.
Accepts: --brand <id> --file <path_to_mp4> --caption <caption_text>
Loads: /data/cookies/<brand_id>_tiktok_cookies.json or TIKTOK_COOKIES_JSON env var.
Automatically converts raw EditThisCookie JSON arrays into Playwright storage_state format.
Captures debug screenshots at every step for CI/CD visibility.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


SCREENSHOT_DIR = Path("tiktok_debug_screenshots")


def screenshot(page, step_name: str, brand: str):
    """Capture a debug screenshot and log its path."""
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    path = SCREENSHOT_DIR / f"{brand}_{step_name}.png"
    page.screenshot(path=str(path), full_page=False)
    print(f"[{brand}] 📸 Screenshot saved: {path}")


def prepare_playwright_storage_state(cookie_path: Path) -> str:
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
                    "domain": c.get("domain", ".tiktok.com"),
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
    parser = argparse.ArgumentParser(description="Multi-Brand TikTok Uploader")
    parser.add_argument("--brand", required=True, help="Brand ID (e.g. phonk_pipeline)")
    parser.add_argument("--file", required=True, help="Absolute path to .mp4 file")
    parser.add_argument("--caption", required=True, help="Caption text including hashtags")
    args = parser.parse_args()

    cookie_path = Path(f"/data/cookies/{args.brand}_tiktok_cookies.json")

    env_cookies = os.getenv("TIKTOK_COOKIES_JSON")
    if env_cookies:
        os.makedirs("./cookies", exist_ok=True)
        cookie_path = Path(f"./cookies/{args.brand}_tiktok_cookies.json")
        cookie_path.write_text(env_cookies, encoding="utf-8")
    elif not cookie_path.exists():
        local_cookie = Path(f"./cookies/{args.brand}_tiktok_cookies.json")
        if local_cookie.exists():
            cookie_path = local_cookie
        else:
            print(f"ERROR: Cookie file not found for brand '{args.brand}' at {cookie_path}", file=sys.stderr)
            sys.exit(1)

    if not Path(args.file).exists():
        print(f"ERROR: Video file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    storage_state_file = prepare_playwright_storage_state(cookie_path)

    print(f"[{args.brand}] Launching Playwright Chromium for TikTok Upload...")
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
            storage_state=storage_state_file,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        # Step 1: Visit homepage to warm session cookies
        print(f"[{args.brand}] Initializing TikTok session on homepage...")
        try:
            page.goto("https://www.tiktok.com/", timeout=30000)
            page.wait_for_timeout(3000)
        except Exception:
            pass

        # Step 2: Navigate to TikTok Studio upload page
        print(f"[{args.brand}] Navigating to TikTok Creator Center Upload Page...")
        page.goto("https://www.tiktok.com/tiktokstudio/upload?lang=en", timeout=60000)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass

        screenshot(page, "01_upload_page_loaded", args.brand)
        print(f"[{args.brand}] Current URL: {page.url}")

        # Step 3: Check if redirected to login
        if "login" in page.url.lower():
            screenshot(page, "FAIL_redirected_to_login", args.brand)
            print(f"[{args.brand}] ERROR: TikTok session cookies expired or invalid. Redirected to login.", file=sys.stderr)
            browser.close()
            sys.exit(1)

        # Step 4: Attach video file
        print(f"[{args.brand}] Attaching MP4 file: {args.file}...")
        file_input = None
        if page.locator('input[type="file"]').count() > 0:
            file_input = page.locator('input[type="file"]').first
        elif page.locator('iframe[data-testid="cc_app_frame"]').count() > 0:
            iframe = page.frame_locator('iframe[data-testid="cc_app_frame"]').first
            file_input = iframe.locator('input[type="file"]').first
        else:
            file_input = page.locator('input[accept*="video"]').first

        file_input.set_input_files(args.file)
        print(f"[{args.brand}] File attached. Waiting 10s for video processing...")
        page.wait_for_timeout(10000)
        screenshot(page, "02_after_file_attached", args.brand)

        # Step 5: Dismiss ALL modals/popups aggressively
        for attempt in range(3):
            try:
                dismiss_selectors = [
                    'button:has-text("Turn on")',
                    'button:has-text("Got it")',
                    'button:has-text("Allow")',
                    'button:has-text("OK")',
                    '.TUXModal-close-icon',
                ]
                for sel in dismiss_selectors:
                    if page.locator(sel).count() > 0:
                        print(f"[{args.brand}] Dismissing popup (attempt {attempt+1}): {sel}")
                        page.locator(sel).first.click(force=True)
                        page.wait_for_timeout(1000)
            except Exception:
                pass

        screenshot(page, "03_after_modal_dismiss", args.brand)

        # Step 6: Set caption
        print(f"[{args.brand}] Setting caption...")
        try:
            editor = page.locator('.public-DraftEditor-content, div[contenteditable="true"]').first
            editor.wait_for(state="visible", timeout=15000)
            editor.click(force=True)
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(args.caption, delay=10)
            print(f"[{args.brand}] Caption set successfully.")
            # Close hashtag suggestion dropdown by pressing Escape and clicking outside
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            page.mouse.click(640, 100)
            page.wait_for_timeout(500)
        except Exception as e:
            print(f"[{args.brand}] Warning setting caption: {e}")

        screenshot(page, "04_after_caption_set", args.brand)

        # Step 7: Wait for video to finish processing before clicking Post
        print(f"[{args.brand}] Waiting 15s for TikTok video transcoding to complete...")
        page.wait_for_timeout(15000)
        screenshot(page, "05_before_post_click", args.brand)

        # Step 8: Dump all visible buttons for debugging
        all_buttons = page.locator("button:visible")
        btn_count = all_buttons.count()
        print(f"[{args.brand}] DEBUG: Found {btn_count} visible buttons on page:")
        for i in range(min(btn_count, 20)):
            btn = all_buttons.nth(i)
            try:
                text = btn.inner_text(timeout=2000).strip().replace("\n", " ")
                classes = btn.get_attribute("class", timeout=2000) or ""
                data_tt = btn.get_attribute("data-tt", timeout=2000) or ""
                disabled = btn.get_attribute("aria-disabled", timeout=2000) or "false"
                print(f"  Button[{i}]: text='{text[:50]}' data-tt='{data_tt}' disabled={disabled}")
            except Exception:
                pass

        # Step 9: Scroll to bottom to reveal the Post button
        print(f"[{args.brand}] Scrolling page to reveal Post button...")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
        screenshot(page, "05b_after_scroll", args.brand)

        # Step 10: Click the Post button
        posted = False
        print(f"[{args.brand}] Attempting to click Post button...")
        try:
            post_selectors = [
                'button[data-e2e="post_video"]',
                'div.btn-post button',
                'button.btn-post',
                'div[class*="btn-post"] button',
                'button:has-text("Post"):not([data-tt*="Sidebar"]):not([data-tt*="Upload"])',
            ]
            for sel in post_selectors:
                locator = page.locator(sel)
                if locator.count() > 0:
                    btn = locator.first
                    is_disabled = btn.get_attribute("aria-disabled", timeout=2000)
                    data_disabled = btn.get_attribute("data-disabled", timeout=2000)
                    print(f"[{args.brand}] Found post button via '{sel}', aria-disabled={is_disabled}, data-disabled={data_disabled}")
                    if is_disabled == "true" or data_disabled == "true":
                        print(f"[{args.brand}] Post button is disabled. Waiting 15 more seconds for processing...")
                        page.wait_for_timeout(15000)
                    btn.scroll_into_view_if_needed(timeout=5000)
                    btn.click(force=True)
                    posted = True
                    print(f"[{args.brand}] ✅ Post button CLICKED!")
                    break

            if not posted:
                print(f"[{args.brand}] ❌ No matching Post button found. Dumping all buttons:")
                all_btns = page.locator("button")
                for i in range(min(all_btns.count(), 30)):
                    try:
                        b = all_btns.nth(i)
                        txt = b.inner_text(timeout=1000).strip()[:40]
                        dtt = b.get_attribute("data-tt", timeout=1000) or ""
                        vis = b.is_visible()
                        print(f"  [{i}] text='{txt}' data-tt='{dtt}' visible={vis}")
                    except Exception:
                        pass
        except Exception as e:
            print(f"[{args.brand}] ❌ Error clicking post button: {e}")

        # Step 11: Wait for upload, handle final confirmation modal, and capture final state
        if posted:
            print(f"[{args.brand}] Waiting to see if 'Continue to post?' confirmation modal appears...")
            page.wait_for_timeout(3000)
            try:
                # Handle the "Continue to post?" modal
                post_now_btn = page.locator('button:has-text("Post now")')
                if post_now_btn.count() > 0:
                    print(f"[{args.brand}] Found 'Continue to post?' modal. Clicking 'Post now'...")
                    post_now_btn.first.click(force=True)
                    page.wait_for_timeout(2000)
            except Exception as e:
                print(f"[{args.brand}] No confirmation modal or error handling it: {e}")
            
            print(f"[{args.brand}] Waiting 25s for upload to complete...")
            page.wait_for_timeout(25000)

        screenshot(page, "06_final_state", args.brand)

        # Check if a success/confirmation message appeared
        final_url = page.url
        print(f"[{args.brand}] Final URL: {final_url}")

        # Save refreshed cookies
        context.storage_state(path=str(cookie_path))

        if posted:
            print(f"[{args.brand}] ✅ TikTok upload sequence completed. Check profile to confirm.")
        else:
            print(f"[{args.brand}] ❌ FAILED: Post button was never clicked. Check debug screenshots.")

        browser.close()


if __name__ == "__main__":
    main()
