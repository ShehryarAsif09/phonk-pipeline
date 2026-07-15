# Multi-Brand Social & RouteNote Publishing Engine Task Sheet

## Phase 1: Kaggle GPU Phonk Generation Pipeline (Completed & Live)
- [x] Fix Kaggle CLI authentication and pre-install `requirements.txt` build timeouts (`commit 3c6b06d`).
- [x] Fix `ModuleNotFoundError: No module named 'generate_music'` inside script kernel by inlining code via base64 (`commit 6763f5d`).
- [x] Verify Kernel Version 4 execution (`Running for 175.4s+`) rendering initial 20 unique Phonk tracks (`gym_phonk`, `drift_phonk`, `rage_phonk`).

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

## Phase 5: n8n Hierarchical Workflows (`n8n_workflows/`)
- [x] Create `n8n_workflows/caption_normalizer.js` Code Node script formatting `metadata.json` tailored for 5 platforms (`YouTube #shorts` in first 80 chars, `Instagram` spaced tags, `TikTok` hooks, `Facebook` clean prompts, `LinkedIn` professional summaries).
- [/] **In Progress:** Create importable JSON templates for Tier 1 (`master_ingestion.json`) and Tier 2 (`platform_dispatcher.json` with the **72-Minute Drip-Feed Wait Node**).
- [ ] Create 5 Platform Executor Sub-Workflows (`executor_youtube.json`, `executor_instagram.json`, `executor_facebook.json`, `executor_linkedin.json`, `executor_tiktok.json`).

---

## Phase 6: Package & Publish Phonk Batch (Workflow B) (Next Step)
- [/] **Waiting for Kaggle Version 4 Completion (`~12-15 mins`):** Await kernel render completion (`Output ~150+ MB`).
- [ ] Trigger **Package and Publish Phonk Batch (Workflow B)** on GitHub Actions to download `audio_out/*.wav` + `covers/*.png` and attach `phonk-batch-xxxxx.zip` to GitHub Releases.

---

## Phase 7: Oracle Cloud VM SSH Deployment & Live Dry-Run (Pending)
- [ ] SSH into Oracle Cloud VM (`ubuntu@your-oracle-vm-ip`).
- [ ] Clone repository (`git clone https://github.com/ShehryarAsif09/phonk-pipeline.git && cd phonk-pipeline/social-publishing-engine`).
- [ ] Run `./setup_oracle.sh` and verify instant `trycloudflare.com` HTTPS URL and `n8n` dashboard access.
- [ ] Connect brand OAuth credentials (`YouTube`, `LinkedIn`, `Instagram`, `Facebook`) in n8n UI and upload `<brand_id>_tiktok_cookies.json` to `/opt/cookies/`.
- [ ] Execute test release (`gym_phonk_0001`) through `routenote_uploader.py` and across all 5 social platforms.
