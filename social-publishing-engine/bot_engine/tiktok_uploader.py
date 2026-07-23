#!/usr/bin/env python3
"""
Multi-Brand TikTok Uploader using Headless Playwright + Google Chrome + Free Anti-Detect Stealth Evasions.

CRITICAL: Uses channel="chrome" and injects client-side anti-detection overrides
to bypass TikTok's 0-view shadowban caused by headless bot detection flags.
100% Free - Requires no paid proxies or commercial anti-detect browser services.

Accepts: --brand <id> --file <path_to_mp4> --caption <caption_text>
Loads: cookies/<brand_id>_tiktok_cookies.json or TIKTOK_COOKIES_JSON env var.
"""

import argparse
import json
import os
import sys
import random
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

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


def inject_free_stealth_evasions(context):
    """Injects 100% free client-side JavaScript overrides to remove headless bot markers."""
    stealth_js = """
    // 1. Remove navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // 2. Mock plugins array
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });

    // 3. Mock languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });

    // 4. Mock window.chrome object
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };

    // 5. Mock WebGL Vendor & Renderer (NVIDIA GeForce RTX 3060)
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Google Inc. (NVIDIA)';
        if (parameter === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)';
        return getParameter.apply(this, arguments);
    };

    // 6. Mock Notification permissions
    if (window.Notification) {
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
    }
    """
    context.add_init_script(stealth_js)


def main():
    parser = argparse.ArgumentParser(description="Multi-Brand TikTok Uploader (Stealth Free)")
    parser.add_argument("--brand", required=True, help="Brand ID (e.g. phonk_pipeline)")
    parser.add_argument("--file", required=True, help="Absolute path to .mp4 file")
    parser.add_argument("--caption", required=True, help="Caption text including hashtags")
    parser.add_argument("--proxy", required=False, default=None, help="Proxy server URL (e.g. http://ip:port or socks5://ip:port)")
    args = parser.parse_args()

    cookie_path = Path(f"./cookies/{args.brand}_tiktok_cookies.json")
    env_cookies = os.getenv("TIKTOK_COOKIES_JSON")
    if env_cookies:
        os.makedirs("./cookies", exist_ok=True)
        cookie_path.write_text(env_cookies, encoding="utf-8")
    elif not cookie_path.exists():
        fallback_cookie = Path(f"/data/cookies/{args.brand}_tiktok_cookies.json")
        if fallback_cookie.exists():
            cookie_path = fallback_cookie
        else:
            print(f"ERROR: Cookie file not found for brand '{args.brand}' at {cookie_path}", file=sys.stderr)
            sys.exit(1)

    video_file = Path(args.file).resolve()
    if not video_file.exists():
        print(f"ERROR: Video file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    storage_state_file = prepare_playwright_storage_state(cookie_path)

    # Check for proxy from CLI arg or environment variable
    proxy_url = args.proxy or os.getenv("TIKTOK_PROXY") or os.getenv("PROXY_URL")
    proxy_config = {"server": proxy_url} if proxy_url else None
    if proxy_config:
        print(f"[{args.brand}] 🌐 Routing traffic through proxy: {proxy_url}")

    print(f"[{args.brand}] Launching Stealth Google Chrome for TikTok Upload...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--window-size=1280,800",
            ]
        )
        context = browser.new_context(
            storage_state=storage_state_file,
            proxy=proxy_config,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/New_York",
        )

        inject_free_stealth_evasions(context)
        page = context.new_page()

        try:
            print(f"[{args.brand}] Initializing session on TikTok homepage...")
            try:
                page.goto("https://www.tiktok.com/", timeout=30000)
                page.wait_for_timeout(random.randint(2000, 4000))
            except Exception:
                pass

            print(f"[{args.brand}] Navigating to TikTok Studio Upload Page...")
            page.goto("https://www.tiktok.com/tiktokstudio/upload?lang=en", timeout=60000)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception:
                pass

            screenshot(page, "01_upload_page_loaded", args.brand)

            if "login" in page.url.lower():
                screenshot(page, "FAIL_redirected_to_login", args.brand)
                print(f"[{args.brand}] ERROR: TikTok session cookies expired or invalid.", file=sys.stderr)
                sys.exit(1)

            print(f"[{args.brand}] Attaching MP4 file: {video_file}...")
            file_input = None
            if page.locator('input[type="file"]').count() > 0:
                file_input = page.locator('input[type="file"]').first
            elif page.locator('iframe[data-testid="cc_app_frame"]').count() > 0:
                iframe = page.frame_locator('iframe[data-testid="cc_app_frame"]').first
                file_input = iframe.locator('input[type="file"]').first
            else:
                file_input = page.locator('input[accept*="video"]').first

            file_input.set_input_files(str(video_file))
            print(f"[{args.brand}] File attached. Waiting for video processing...")
            page.wait_for_timeout(10000)
            screenshot(page, "02_after_file_attached", args.brand)

            for attempt in range(3):
                try:
                    for sel in ['button:has-text("Turn on")', 'button:has-text("Got it")', 'button:has-text("Allow")', 'button:has-text("OK")', '.TUXModal-close-icon']:
                        if page.locator(sel).count() > 0:
                            page.locator(sel).first.click(force=True)
                            page.wait_for_timeout(1000)
                except Exception:
                    pass

            screenshot(page, "03_after_modal_dismiss", args.brand)

            print(f"[{args.brand}] Setting caption with human-like typing delay...")
            try:
                editor = page.locator('.public-DraftEditor-content, div[contenteditable="true"]').first
                editor.wait_for(state="visible", timeout=15000)
                editor.click(force=True)
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.type(args.caption, delay=random.randint(15, 45))
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
                page.mouse.click(640, 100)
                page.wait_for_timeout(500)
            except Exception as e:
                print(f"[{args.brand}] Warning setting caption: {e}")

            screenshot(page, "04_after_caption_set", args.brand)

            print(f"[{args.brand}] Waiting 15s for video transcoding...")
            page.wait_for_timeout(15000)

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

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
                        btn.scroll_into_view_if_needed(timeout=5000)
                        btn.click(force=True)
                        posted = True
                        print(f"[{args.brand}] ✅ Post button CLICKED!")
                        break
            except Exception as e:
                print(f"[{args.brand}] ❌ Error clicking post button: {e}")

            if posted:
                page.wait_for_timeout(3000)
                try:
                    post_now_btn = page.locator('button:has-text("Post now")')
                    if post_now_btn.count() > 0:
                        post_now_btn.first.click(force=True)
                        page.wait_for_timeout(2000)
                except Exception:
                    pass

                print(f"[{args.brand}] Waiting 25s for upload to complete...")
                page.wait_for_timeout(25000)

            screenshot(page, "06_final_state", args.brand)
            context.storage_state(path=str(cookie_path))

            if posted:
                print(f"[{args.brand}] ✅ TikTok upload sequence completed successfully.")
            else:
                print(f"[{args.brand}] ❌ FAILED: Post button was never clicked.")

        except Exception as e:
            print(f"[{args.brand}] ❌ Fatal Error during TikTok upload: {e}", file=sys.stderr)
            try:
                screenshot(page, "error_fatal", args.brand)
            except Exception:
                pass
            sys.exit(1)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
