#!/bin/bash
# =============================================================
# setup-vps.sh — Setup lengkap di VPS untuk backend-tafsir.ift.my.id
# Jalankan: bash setup-vps.sh
# =============================================================
set -e

DOMAIN="backend-tafsir.ift.my.id"
APP_DIR="/root/chatbot-tafsir"
NGINX_CONF="/etc/nginx/sites-available/${DOMAIN}"

echo "=================================================="
echo "  Setup Chatbot Tafsir Backend — ${DOMAIN}"
echo "=================================================="

# ── 1. Buat direktori app ──────────────────────────────────
echo ""
echo "[1/6] Menyiapkan direktori: ${APP_DIR}"
mkdir -p "${APP_DIR}"
cd "${APP_DIR}"

# ── 2. Salin file (jalankan dari lokal atau git clone) ─────
echo "[2/6] Cek file wajib..."
for f in docker-compose.yml backend/Dockerfile backend/requirements.txt; do
    [ -f "$f" ] || { echo "ERROR: ${f} tidak ditemukan! Upload file dulu."; exit 1; }
done

# ── 3. Setup .env ──────────────────────────────────────────
echo "[3/6] Setup .env..."
if [ ! -f .env ]; then
    if [ -f .env.production ]; then
        cp .env.production .env
        echo "  → .env.production disalin ke .env"
        echo "  ⚠️  EDIT .env sebelum lanjut!"
        echo ""
        echo "  Wajib diisi:"
        echo "    DATABASE_URL — koneksi MySQL"
        echo "    QDRANT_URL   — URL Qdrant server"
        echo "    CORS_ORIGINS — https://backend-tafsir.ift.my.id"
        echo ""
        read -p "  Sudah edit .env? (y/n): " confirm
        [ "$confirm" = "y" ] || { echo "Edit .env dulu, lalu jalankan ulang."; exit 0; }
    else
        echo "ERROR: .env atau .env.production tidak ditemukan!"
        exit 1
    fi
fi

# ── 4. Setup Nginx ─────────────────────────────────────────
echo "[4/6] Setup Nginx config..."
if [ ! -f "nginx-backend-tafsir.conf" ]; then
    echo "ERROR: nginx-backend-tafsir.conf tidak ditemukan!"
    exit 1
fi

# Salin config (HTTP only dulu, sebelum certbot)
cat > "${NGINX_CONF}" << 'NGINX_HTTP'
server {
    listen 80;
    listen [::]:80;
    server_name backend-tafsir.ift.my.id;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }

    location /api/v1/chat/stream {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        add_header X-Accel-Buffering "no";
    }
}
NGINX_HTTP

ln -sf "${NGINX_CONF}" "/etc/nginx/sites-enabled/${DOMAIN}" 2>/dev/null || true
nginx -t && systemctl reload nginx
echo "  → Nginx config aktif (HTTP)"

# ── 5. SSL dengan Certbot ──────────────────────────────────
echo "[5/6] Minta SSL Certificate..."
mkdir -p /var/www/certbot
certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos \
    --email admin@ift.my.id --redirect || {
    echo "  ⚠️  Certbot gagal. Coba manual: certbot --nginx -d ${DOMAIN}"
    echo "  Lanjut tanpa SSL..."
}

# Ganti dengan config HTTPS lengkap jika certbot berhasil
if [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    cp nginx-backend-tafsir.conf "${NGINX_CONF}"
    nginx -t && systemctl reload nginx
    echo "  → SSL aktif!"
fi

# ── 6. Jalankan Docker ────────────────────────────────────
echo "[6/6] Build & jalankan Docker container..."
docker compose build --no-cache
docker compose up -d

echo ""
echo "=================================================="
echo "  ✅ Deploy selesai!"
echo ""
echo "  URL  : https://${DOMAIN}"
echo "  Docs : https://${DOMAIN}/docs"
echo "  Health: https://${DOMAIN}/health"
echo ""
echo "  Lihat log: docker compose logs -f backend"
echo "  Model BGE-M3 butuh ~2-5 menit untuk load..."
echo "=================================================="
