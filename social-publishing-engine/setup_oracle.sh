#!/usr/bin/env bash
set -e

echo "=== [1/5] Configuring OS Firewall & IPTables ==="
if command -v ufw &> /dev/null; then
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw allow 22/tcp
    sudo ufw --force enable
    sudo ufw reload
fi

# Ensure Oracle Linux / Ubuntu iptables accept inbound 80/443
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || true
sudo netfilter-persistent save 2>/dev/null || true

echo "=== [2/5] Creating Shared Storage & Cookie Directories ==="
sudo mkdir -p /opt/shared_videos/covers
sudo mkdir -p /opt/shared_videos/audio
sudo mkdir -p /opt/cookies
sudo chmod -R 777 /opt/shared_videos /opt/cookies

echo "=== [3/5] Installing Docker Engine & Docker Compose (if missing) ==="
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    sudo usermod -aG docker $USER || true
fi

echo "=== [4/5] Building Browser Automation Sidecar & Starting Engine ==="
if [ -z "$DOMAIN_NAME" ]; then
    echo "WARNING: DOMAIN_NAME not set. Using default hub.yourdomain.com in Caddyfile."
    echo "To set custom domain, run: export DOMAIN_NAME=yourdomain.com && ./setup_oracle.sh"
fi

sudo -E docker compose up --build -d

echo "=== [5/5] Deployment Complete ==="
echo "Waiting 5 seconds for Cloudflare Tunnel to assign public HTTPS URL..."
sleep 5
CF_URL=$(sudo docker compose logs cloudflared 2>&1 | grep -o 'https://[^ ]*\.trycloudflare\.com' | tail -n 1 || true)

echo "------------------------------------------------------------"
echo "Your Multi-Brand Social Publishing Engine is now LIVE!"
if [ -n "$CF_URL" ]; then
    echo "Instant Cloudflare Tunnel URL (No domain required): $CF_URL"
fi
echo "Custom Domain / Caddy URL: https://${DOMAIN_NAME:-hub.yourdomain.com}"
echo "------------------------------------------------------------"
