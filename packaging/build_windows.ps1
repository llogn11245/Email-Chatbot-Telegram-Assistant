<#
Build Windows onedir (+ installer) — chạy trên Windows tại thư mục gốc repo.

  powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
  powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1 -SkipFrontend
  powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1 -SkipInstaller

Thứ tự: cài deps Python -> (build frontend nếu cần/có npm) -> PyInstaller -> (Inno Setup nếu có).
#>
param(
    [switch]$SkipFrontend,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

$python = if ($env:VIRTUAL_ENV) { Join-Path $env:VIRTUAL_ENV "Scripts\python.exe" } else { "python" }
Write-Host "==> Python: $python"

Write-Host "==> Cai dependencies"
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt
& $python -m pip install pyinstaller

$indexHtml = Join-Path $root "frontend\dist\index.html"
$hasNpm = [bool](Get-Command npm -ErrorAction SilentlyContinue)

if (-not $SkipFrontend) {
    if ($hasNpm) {
        Write-Host "==> Build frontend"
        Push-Location (Join-Path $root "frontend")
        try {
            if (-not (Test-Path node_modules)) { npm install --no-audit --no-fund }
            npm run build
        }
        finally {
            Pop-Location
        }
    }
    elseif (-not (Test-Path $indexHtml)) {
        throw "frontend/dist chua co va khong tim thay npm. Cai Node.js hoac commit frontend/dist."
    }
    else {
        Write-Host "==> Bo qua build frontend (khong co npm, dung dist san co)"
    }
}

if (-not (Test-Path $indexHtml)) {
    throw "frontend/dist/index.html khong ton tai. Khong the dong goi."
}

Write-Host "==> PyInstaller"
& $python -m PyInstaller --noconfirm --clean packaging\pyinstaller\chatbot-gmail.spec

$exe = Join-Path $root "dist\ChatbotGmail\ChatbotGmail.exe"
Write-Host "==> Xong: $exe"

if (-not $SkipInstaller) {
    $iscc = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    if ($iscc) {
        Write-Host "==> Tao installer (Inno Setup)"
        & $iscc "packaging\windows\installer.iss"
        Write-Host "==> Installer: dist\installer\ChatbotGmail-Setup.exe"
    }
    else {
        Write-Host "==> Bo qua installer (chua cai Inno Setup 6). Tai: https://jrsoftware.org/isdl.php"
    }
}
