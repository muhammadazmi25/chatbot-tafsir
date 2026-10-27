#!/bin/bash
# =============================================================
# deploy.sh — Deploy Chatbot Tafsir Backend ke VPS
# Jalankan di VPS: bash deploy.sh
# =============================================================
set -e

echo "=================================================="
echo "  Deploy Chatbot Tafsir Ath-Thabari Backend"
echo "=================================================="

# --- Cek docker & docker-compose ---
command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker belum terinstall."; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "ERROR: Docker Compose belum terinstall."; exit 1; }

# --- Cek .env ada ---
if [ ! -f .env ]; then
    echo "ERROR: File .env tidak ditemukan!"
    echo "Salin .env.production ke .env dan isi nilainya terlebih dahulu."
    exit 1
fi

echo ""
echo "[1/4] Pull / update kode terbaru..."
# Uncomment jika pakai git:
# git pull origin main

echo "[2/4] Build Docker image..."
docker compose build --no-cache

echo "[3/4] Stop container lama (jika ada)..."
docker compose down --remove-orphans || true

echo "[4/4] Jalankan container..."
docker compose up -d

echo ""
echo "=================================================="
echo "  Backend berjalan di http://VPS_IP:8001"
echo "  Cek health: curl http://localhost:8001/health"
echo "  Lihat log:  docker compose logs -f backend"
echo "=================================================="

# Tunggu health check
echo ""
echo "Menunggu backend siap (model BGE-M3 loading ~2-5 menit)..."
for i in $(seq 1 24); do
    sleep 10
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health 2>/dev/null || echo "000")
    echo "  [$((i*10))s] Status: $STATUS"
    if [ "$STATUS" = "200" ]; then
        echo ""
        echo "✅ Backend SIAP!"
        break
    fi
done
