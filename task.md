# Multi-Brand Social & RouteNote Publishing Engine Task Sheet

## Phase 1: Kaggle GPU Phonk Generation Pipeline (Completed & Live)
- [x] Fix Kaggle CLI authentication and pre-install `requirements.txt` build timeouts (`commit 3c6b06d`).
- [x] Fix `ModuleNotFoundError: No module named 'generate_music'` inside script kernel by inlining code via base64 (`commit 6763f5d`).
- [x] Verify Kernel execution (`Running on P100 / T4`) and successfully generate 20 unique Phonk tracks (`gym_phonk`, `drift_phonk`, `rage_phonk`).

---

## Phase 2: Core Infrastructure Architecture (`social-publishing-engine/`) (Completed)
- [x] Create `social-publishing-engine/` workspace folder inside unified `phonk-pipeline/` repository (`commit ce6113a`).
- [x] Create `docker-compose.yml` configuring `n8n`, `Caddy` reverse proxy, `browser-automation` Playwright sidecar, and `cloudflared` Quick Tunnel (`trycloudflare.com`) for $0 domain-less HTTPS.
- [x] Create `Caddyfile` for automated Let's Encrypt `HTTPS` termination when using custom domains (`hub.yourdomain.com`).
- [x] Create 1-click `setup_oracle.sh` script (`ufw`/`iptables` firewall rules, Docker installation, `/opt/shared_videos` and `/opt/cookies` volume permission setup, instant tunnel URL output).
- [x] Create `config/brands_config.json` Central Brand Registry controlling multi-brand toggles for `phonk_pipeline`, `publixion`, `myfitnessleap`, and `neurostackos`.

---

## Phase 3: RouteNote Automated Uploader Bot (`routenote_bot/`) (Completed)
- [x] Create `bot_engine/routenote_uploader.py` using Playwright headless Chromium to auto-login via `ROUTENOTE_EMAIL` and `ROUTENOTE_PASSWORD`.
- [x] Implement DOM navigation for **Create New Release**, auto-filling metadata (`Track Title`, `Artist Name`, `Genre: Electronic/Phonk`, `Instrumental: Yes`).
- [x] Wire up DOM file input attachments for `.wav` audio track and `.png` cover art from `/data/videos/`.

---

## Phase 4: Multi-Brand TikTok Uploader Bot (`tiktok_bot/`) (Completed)
- [x] Create `bot_engine/tiktok_uploader.py` with multi-brand routing (`--brand <id>` argument loads `/data/cookies/<id>_tiktok_cookies.json`).
- [x] Implement `storage_state()` cookie persistence, Creator Center DOM iframe uploader fallback, caption filling, and post verification.

---

## Phase 5: Serverless Video Generation (`make_reel.sh`) (Completed)
- [x] Create `social-publishing-engine/bot_engine/make_reel.sh` wrapping `ffmpeg`.
- [x] Configure `ffmpeg` to stitch `audio.wav` and `cover.png` into a 1080x1920 `.mp4`.
- [x] Ensure output `.mp4` meets Instagram/TikTok specifications (H.264, AAC).

---

## Phase 6: Official API Uploaders (`ig_api_uploader.py`, `yt_api_uploader.py`, `fb_api_uploader.py`) (Completed)
- [x] Write `yt_api_uploader.py` using `google-api-python-client` with OAuth2 Refresh Token injection.
- [x] Write `ig_api_uploader.py` using Facebook Graph API (`/media` and `/media_publish` endpoints) for Instagram Reels.
- [x] Write `fb_api_uploader.py` using Facebook Graph API for Facebook Page Reels.

---

## Phase 7: Serverless Dispatcher Workflow & State Management (Completed)
- [x] Create `publish_state.json` to act as a database tracking the `last_published_index`.
- [x] Create `.github/workflows/serverless-publisher.yml`.
- [x] Configure `schedule` trigger for every 6 hours (`0 */6 * * *`) and `workflow_dispatch`.
- [x] Build out the Actions steps: download latest Kaggle release, extract `.wav` and `.png`, run `make_reel.sh`, execute the API upload scripts, and commit the updated `last_published_index` back to the repository.
- [x] Debug and verify final run!
