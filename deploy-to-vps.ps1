# ============================================================
# deploy-to-vps.ps1
# Deploy revisi Backend & Frontend Chatbot Tafsir ke VPS
# Usage di PowerShell: .\deploy-to-vps.ps1
# ============================================================

$VPS_HOST = "root@72.60.196.223"
$APP_DIR  = "/app/chatbot"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "   DEPLOY REVISI CHATBOT TAFSIR KE VPS" -ForegroundColor Cyan
Write-Host "   Host: $VPS_HOST" -ForegroundColor Cyan
Write-Host "   Path: $APP_DIR" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Upload Backend
Write-Host "`n[1/3] Uploading backend/app (RAG Service & Reranker fixes)..." -ForegroundColor Yellow
scp -r backend/app "${VPS_HOST}:${APP_DIR}/backend/"

# 2. Upload Frontend (dist yang sudah dibuild + src)
Write-Host "`n[2/3] Uploading frontend/dist (Production Build) & src..." -ForegroundColor Yellow
scp -r frontend/dist "${VPS_HOST}:${APP_DIR}/frontend/"
scp -r frontend/src "${VPS_HOST}:${APP_DIR}/frontend/"

# 3. Build & Restart Docker Containers di VPS dengan --no-cache
Write-Host "`n[3/3] Rebuilding (no-cache) & restarting Docker containers di VPS..." -ForegroundColor Yellow
ssh -t $VPS_HOST "cd $APP_DIR && docker compose build --no-cache backend frontend && docker compose up -d --force-recreate backend frontend && sleep 3 && docker compose ps"

Write-Host "`n==================================================" -ForegroundColor Green
Write-Host "   DEPLOYMENT SELESAI!" -ForegroundColor Green
Write-Host "   Frontend: https://chatbot-tafsir.ift.myid" -ForegroundColor Green
Write-Host "   Backend : https://backend-tafsir.ift.my.id" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
