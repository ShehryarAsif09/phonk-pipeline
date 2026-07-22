#!/usr/bin/env python3
"""
Multi-Brand TikTok Uploader using Headless Playwright Chromium.
Accepts: --brand <id> --file <path_to_mp4> --caption <caption_text>
Loads: /data/cookies/<brand_id>_tiktok_cookies.json
"""

import argparse
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description="Multi-Brand TikTok Uploader")
    parser.add_argument("--brand", required=True, help="Brand ID (e.g. phonk_pipeline, myfitnessleap)")
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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        print(f"[{args.brand}] Navigating to TikTok Creator Center Upload Page...")
        page.goto("https://www.tiktok.com/creator-center/upload?lang=en", timeout=60000)
        page.wait_for_load_state("networkidle")

        # Handle TikTok iframe uploader if embedded
        iframe = page.frame_locator('iframe[data-testid="cc_app_frame"]').first
        uploader = iframe if iframe else page

        print(f"[{args.brand}] Attaching MP4 file: {args.file}...")
        file_input = uploader.locator('input[type="file"]').first
        file_input.set_input_files(args.file)

        print(f"[{args.brand}] Waiting for video processing and draft editor...")
        editor = uploader.locator('.public-DraftEditor-editor').first
        editor.wait_for(state="visible", timeout=90000)
        
        # Clear default or auto-generated filename from description and fill caption
        editor.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        editor.fill(args.caption)

        print(f"[{args.brand}] Submitting post...")
        post_btn = uploader.locator('button:has-text("Post"), button:has-text("Upload")').first
        post_btn.click()

        # Wait for confirmation modal or redirect
        page.wait_for_timeout(10000)
        
        # Save refreshed session cookies
        context.storage_state(path=str(cookie_path))
        print(f"[{args.brand}] SUCCESS! Video uploaded and cookies refreshed.")
        browser.close()


if __name__ == "__main__":
    main()
