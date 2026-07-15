# Self-Hosted Multi-Brand Social & RouteNote Publishing Engine

A production-grade, containerized orchestration suite designed to run on a self-hosted Oracle Cloud instance (`n8n` + `Caddy` automated HTTPS + `Playwright` headless Chromium sidecar).

## 1. Supported Brands (`brands_config.json`)
- `phonk_pipeline` (Antigravity Phonk Factory)
- `publixion` (Publixion Media)
- `myfitnessleap` (My Fitness Leap)
- `neurostackos` (NeuroStack OS)

## 2. Supported Platforms
- **YouTube Shorts:** Native n8n OAuth2 node (`1-click login`).
- **Instagram Reels & Facebook Reels:** Native n8n Meta Graph API (`Page Access Token`).
- **LinkedIn Video:** Native n8n LinkedIn OAuth2 node (`1-click login`).
- **TikTok Reels:** Headless Playwright Chromium (`tiktok_uploader.py`) bypassing 8-week API audits.
- **RouteNote ($0 Music Distribution):** Headless Playwright Chromium (`routenote_uploader.py`).

---

## 3. Deployment on Oracle Cloud VM (3-Step Bootstrap)

### Step 1: Copy Engine to Oracle Server
```bash
scp -r social-publishing-engine/ ubuntu@your-oracle-vm-ip:~/social-publishing-engine/
ssh ubuntu@your-oracle-vm-ip
cd ~/social-publishing-engine/
```

### Step 2: Set Subdomain & Run Bootstrap
```bash
export DOMAIN_NAME="hub.yourdomain.com"
chmod +x setup_oracle.sh
./setup_oracle.sh
```
*This automatically opens ports 80/443 in `ufw`/`iptables`, installs Docker & Docker Compose if needed, creates shared `/opt/shared_videos` and `/opt/cookies` volumes, and launches Caddy with automatic Let's Encrypt SSL certificates.*

### Step 3: Access n8n Interface
Open your browser to: `https://hub.yourdomain.com`
Create your initial admin credentials and import the workflows inside `n8n_workflows/`.

---

## 4. Multi-Brand Onboarding Guide

### A. For Native OAuth Platforms (YouTube, LinkedIn, Instagram, Facebook)
1. Inside n8n, go to **Credentials -> Add Credential**.
2. For each brand, click **Connect my account** (`e.g., YouTube OAuth - Publixion` or `LinkedIn OAuth - MyFitnessLeap`).
3. Your 1-click logins are securely saved inside n8n's encrypted volume.

### B. For TikTok (Playwright Cookies)
For each active brand:
1. Log into that brand's TikTok account on your local PC.
2. Export session cookies as `<brand_id>_tiktok_cookies.json` (`phonk_pipeline_tiktok_cookies.json`, `myfitnessleap_tiktok_cookies.json`).
3. SCP them directly to the Oracle server's shared cookie folder:
```bash
scp *_tiktok_cookies.json ubuntu@your-oracle-vm-ip:/opt/cookies/
```

### C. For RouteNote ($0 Music Distribution)
In your Oracle VM's environment or inside n8n's `.env`, set:
```bash
export ROUTENOTE_EMAIL="your_verified_routenote_email@domain.com"
export ROUTENOTE_PASSWORD="your_secure_password"
```

---

## 5. Adding New Brands (In 60 Seconds)
To add a new brand (`e.g., brand_five`):
1. Add one entry inside `config/brands_config.json`.
2. Connect `brand_five`'s YouTube/LinkedIn inside n8n `Credentials`.
3. Drop `brand_five_tiktok_cookies.json` into `/opt/cookies/`.
*No workflow wiring or line changes required!*
