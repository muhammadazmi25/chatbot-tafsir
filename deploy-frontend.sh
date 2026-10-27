#!/bin/bash
# ============================================================
# deploy-frontend.sh
# Deploy / update container frontend ke VPS
# Usage: bash deploy-frontend.sh
# ============================================================
set -euo pipefail

VPS_HOST="root@72.60.196.223"
APP_DIR="/app/chatbot"
FRONTEND_CONF="nginx-frontend-tafsir.conf"
DOMAIN="chatbot-tafsir.ift.myid"

echo "========================================"
echo " Deploy Frontend Chatbot Tafsir"
echo " Domain : $DOMAIN"
echo " VPS    : $VPS_HOST"
echo "========================================"

# ---- 1. Upload file terbaru ----
echo ""
echo "[1/5] Upload source files ke VPS..."
scp -r \
  frontend/Dockerfile \
  frontend/nginx-spa.conf \
  frontend/.dockerignore \
  frontend/package.json \
  frontend/package-lock.json \
  frontend/vite.config.js \
  frontend/dist \
  frontend/src \
  "$VPS_HOST:$APP_DIR/frontend/"

scp docker-compose.yml         "$VPS_HOST:$APP_DIR/docker-compose.yml"
scp "$FRONTEND_CONF"           "$VPS_HOST:$APP_DIR/$FRONTEND_CONF"

# ---- 2. Setup nginx config di VPS ----
echo ""
echo "[2/5] Setup nginx config..."
ssh "$VPS_HOST" bash <<EOF
  set -e
  cp $APP_DIR/$FRONTEND_CONF /etc/nginx/sites-available/$DOMAIN

  # Enable site (symlink)
  ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/$DOMAIN

  # Test nginx config
  nginx -t
  echo "Nginx config OK"
EOF

# ---- 3. Build & jalankan container frontend ----
echo ""
echo "[3/5] Build & start container frontend..."
ssh "$VPS_HOST" bash <<EOF
  set -e
  cd $APP_DIR

  # Build image baru
  docker compose build frontend

  # Start container
  docker compose up -d frontend

  # Cek status
  sleep 5
  docker compose ps frontend
EOF

# ---- 4. SSL dengan Certbot ----
echo ""
echo "[4/5] Ambil SSL certificate untuk $DOMAIN..."
ssh "$VPS_HOST" bash <<EOF
  set -e

  # Pastikan certbot dan plugin nginx tersedia
  if ! command -v certbot &>/dev/null; then
    apt-get install -y certbot python3-certbot-nginx
  fi

  # Minta certificate (HTTP-01 challenge via nginx)
  # Catatan: nginx harus sudah jalan dan port 80 terbuka
  certbot --nginx \
    -d $DOMAIN \
    --non-interactive \
    --agree-tos \
    --email admin@ift.myid \
    --redirect

  echo "SSL OK"
EOF

# ---- 5. Reload nginx ----
echo ""
echo "[5/5] Reload nginx..."
ssh "$VPS_HOST" "systemctl reload nginx"

echo ""
echo "========================================"
echo " DEPLOY SELESAI!"
echo " URL: https://$DOMAIN"
echo "========================================"
