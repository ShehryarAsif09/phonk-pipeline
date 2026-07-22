#!/usr/bin/env python3
"""
Multi-Brand TikTok Uploader using Headless Playwright Chromium.
Accepts: --brand <id> --file <path_to_mp4> --caption <caption_text>
Loads: /data/cookies/<brand_id>_tiktok_cookies.json or TIKTOK_COOKIES_JSON env var.
"""

import argparse
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def main():
    parser = argparse.ArgumentParser(description="Multi-Brand TikTok Uploader")
    parser.add_argument("--brand", required=True, help="Brand ID (e.g. phonk_pipeline)")
    parser.add_argument("--file", required=True, help="Absolute path to .mp4 file")
    parser.add_argument("--caption", required=True, help="Caption text including hashtags")
    args = parser.parse_args()

    cookie_path = Path(f"/data/cookies/{args.brand}_tiktok_cookies.json")
    
    # Check if TIKTOK_COOKIES_JSON environment variable is set directly
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
            storage_state=str(cookie_path),
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        print(f"[{args.brand}] Navigating to TikTok Creator Center Upload Page...")
        page.goto("https://www.tiktok.com/tiktokstudio/upload?lang=en", timeout=60000)
        page.wait_for_load_state("networkidle")

        # Check if redirected to login
        if "login" in page.url.lower():
            print(f"[{args.brand}] ERROR: TikTok session cookies expired or invalid. Redirected to login.", file=sys.stderr)
            browser.close()
            sys.exit(1)

        print(f"[{args.brand}] Attaching MP4 file: {args.file}...")
        
        # Robust check: try main page file input first, fallback to iframe if present
        file_input = None
        if page.locator('input[type="file"]').count() > 0:
            file_input = page.locator('input[type="file"]').first
        elif page.locator('iframe[data-testid="cc_app_frame"]').count() > 0:
            iframe = page.frame_locator('iframe[data-testid="cc_app_frame"]').first
            file_input = iframe.locator('input[type="file"]').first
        else:
            # Fallback direct locator
            file_input = page.locator('input[accept*="video"]').first

        file_input.set_input_files(args.file)

        print(f"[{args.brand}] Waiting for video processing and draft editor...")
        page.wait_for_timeout(5000)

        # Look for description / caption input editor
        try:
            editor = page.locator('.public-DraftEditor-editor, div[contenteditable="true"], textarea').first
            editor.wait_for(state="visible", timeout=60000)
            editor.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            editor.fill(args.caption)
        except Exception as e:
            print(f"[{args.brand}] Warning setting caption: {e}")

        print(f"[{args.brand}] Submitting post...")
        try:
            post_btn = page.locator('button:has-text("Post"), button:has-text("Upload")').first
            post_btn.click()
            page.wait_for_timeout(10000)
        except Exception as e:
            print(f"[{args.brand}] Warning clicking post button: {e}")

        # Save refreshed session cookies
        context.storage_state(path=str(cookie_path))
        print(f"[{args.brand}] SUCCESS! Video uploaded to TikTok and cookies refreshed.")
        browser.close()


if __name__ == "__main__":
    main()
