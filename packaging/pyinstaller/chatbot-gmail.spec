# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))


def safe_submodules(name):
    try:
        return collect_submodules(name)
    except Exception:
        return []


def safe_metadata(name):
    try:
        return copy_metadata(name)
    except Exception:
        return []


packages = [
    "langchain",
    "langchain_core",
    "langchain_openai",
    "langchain_anthropic",
    "langchain_google_genai",
    "langchain_deepseek",
    "langgraph",
    "tiktoken",
    "tiktoken_ext",
    "openai",
    "anthropic",
    "google",
    "googleapiclient",
    "google_auth_oauthlib",
    "google_genai",
    "sqlalchemy",
    "aiogram",
    "aiohttp",
    "uvicorn",
    "webview",
    "pystray",
    "PIL",
    "clr",
]

hiddenimports = []
for pkg in packages:
    hiddenimports += safe_submodules(pkg)

hiddenimports += [
    "backend",
    "backend.desktop.app",
    "sqlalchemy.dialects.sqlite",
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
]

datas = [
    (os.path.join(ROOT, "frontend", "dist"), "frontend/dist"),
    (os.path.join(ROOT, "assets", "icon.ico"), "assets"),
]
for meta in ("tiktoken", "langchain", "langchain-core", "langchain-openai", "langgraph", "openai"):
    datas += safe_metadata(meta)

a = Analysis(
    [os.path.join(ROOT, "packaging", "run_desktop.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[os.path.join(ROOT, "packaging", "pyinstaller", "runtime_hook.py")],
    excludes=["tkinter", "matplotlib", "numpy", "pandas"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ChatbotGmail",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(ROOT, "assets", "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ChatbotGmail",
)
