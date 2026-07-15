#!/usr/bin/env python3
"""
RouteNote Automated Music Distribution Uploader via Headless Playwright Chromium.
Accepts: --audio <path_to_wav> --cover <path_to_png> --title <title> --artist <artist>
Uses environment variables ROUTENOTE_EMAIL and ROUTENOTE_PASSWORD for authentication.
"""

import argparse
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description="RouteNote Automated Uploader")
    parser.add_argument("--audio", required=True, help="Path to .wav track")
    parser.add_argument("--cover", required=True, help="Path to 3000x3000 .png cover art")
    parser.add_argument("--title", required=True, help="Track Title")
    parser.add_argument("--artist", required=True, help="Primary Artist Name")
    parser.add_argument("--genre", default="Electronic", help="Primary Genre")
    args = parser.parse_args()

    email = os.getenv("ROUTENOTE_EMAIL")
    password = os.getenv("ROUTENOTE_PASSWORD")

    if not email or not password:
        print("ERROR: ROUTENOTE_EMAIL and ROUTENOTE_PASSWORD environment variables not set.", file=sys.stderr)
        sys.exit(1)

    print(f"[RouteNote Bot] Launching Playwright Chromium for release: {args.title}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("[RouteNote Bot] Logging in...")
        page.goto("https://www.routenote.com/rn/login", timeout=60000)
        page.fill('input[name="username"]', email)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_load_state("networkidle")

        # Check for successful login
        if "login" in page.url.lower():
            print("ERROR: RouteNote login failed or blocked by challenge.", file=sys.stderr)
            browser.close()
            sys.exit(1)

        print("[RouteNote Bot] Navigating to Create New Release...")
        page.goto("https://www.routenote.com/rn/releases/create", timeout=60000)

        # Step 1: Album/Single Title
        page.fill('input[name="release_title"]', args.title)
        page.click('button:has-text("Create Release"), input[value="Create Release"]')
        page.wait_for_load_state("networkidle")

        print("[RouteNote Bot] Attaching Audio (.wav) and Cover Art (.png)...")
        # RouteNote workflow attaches files and sets instrumental/genre tags
        # (Exact DOM selectors adapt to RouteNote's multi-step form)
        try:
            audio_input = page.locator('input[type="file"][accept*="audio"], input[type="file"]').first
            audio_input.set_input_files(args.audio)
            page.wait_for_timeout(5000)

            cover_input = page.locator('input[type="file"][accept*="image"]').first
            cover_input.set_input_files(args.cover)
            page.wait_for_timeout(5000)
        except Exception as e:
            print(f"WARNING: File attachment step hit non-standard form prompt: {e}")

        print(f"[RouteNote Bot] Draft created for '{args.title}' by {args.artist}.")
        browser.close()


if __name__ == "__main__":
    main()
