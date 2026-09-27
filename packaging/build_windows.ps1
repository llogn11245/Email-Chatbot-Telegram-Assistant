# Build Windows onedir + installer (chạy trên Windows, tại thư mục gốc repo)
#   powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "==> Cài dependencies"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

Write-Host "==> Build frontend"
Push-Location frontend
if (-not (Test-Path node_modules)) { npm install --no-audit --no-fund }
npm run build
Pop-Location

Write-Host "==> PyInstaller"
python -m PyInstaller --noconfirm --clean packaging\pyinstaller\chatbot-gmail.spec

Write-Host "==> Xong: dist\ChatbotGmail\ChatbotGmail.exe"
Write-Host "    (Tuỳ chọn) Tạo installer: iscc packaging\windows\installer.iss"
