# -*- mode: python ; coding: utf-8 -*-
import importlib.util
import os
import sys

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))


def _has_module(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


# Các package BẮT BUỘC phải được cài trong đúng interpreter đang chạy PyInstaller.
_required = [
    "aiogram",
    "sqlalchemy",
    "pydantic",
    "langchain",
    "langchain_core",
    "langgraph",
    "langchain_openai",
    "langchain_anthropic",
    "langchain_google_genai",
    "langchain_deepseek",
    "googleapiclient",
    "google_auth_oauthlib",
]
if sys.platform.startswith("win"):
    _required += ["pystray", "PIL"]

_missing = [name for name in _required if not _has_module(name)]
if _missing:
    raise SystemExit(
        "Thieu package trong moi truong build: "
        + ", ".join(_missing)
        + "\nHay cai dung interpreter nay:\n"
        + "  python -m pip install -r requirements.txt\n"
        + "(Dam bao pip va PyInstaller dung CUNG mot Python; khuyen nghi dung venv rieng)"
    )


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
    "pystray",
    "PIL",
    "tkinter",
]

hiddenimports = []
for pkg in packages:
    hiddenimports += safe_submodules(pkg)

hiddenimports += [
    "app",
    "app.desktop.app",
    "sqlalchemy.dialects.sqlite",
]

datas = [
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
    excludes=["matplotlib", "numpy", "pandas"],
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
