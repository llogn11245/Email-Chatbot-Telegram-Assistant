import sys
from pathlib import Path

from app.core import paths

APP_KEY = "ChatbotGmail"


def _command_args() -> list[str]:
    if paths.is_frozen():
        return [sys.executable]
    return [sys.executable, "-m", "app"]


def _command_string() -> str:
    return " ".join(f'"{part}"' for part in _command_args())


# --- Windows -----------------------------------------------------------------
def _win_registry():
    import winreg

    return winreg


def _win_enable() -> None:
    winreg = _win_registry()
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    )
    with key:
        winreg.SetValueEx(key, APP_KEY, 0, winreg.REG_SZ, _command_string())


def _win_disable() -> None:
    winreg = _win_registry()
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        with key:
            winreg.DeleteValue(key, APP_KEY)
    except FileNotFoundError:
        pass


def _win_is_enabled() -> bool:
    winreg = _win_registry()
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
        with key:
            winreg.QueryValueEx(key, APP_KEY)
            return True
    except FileNotFoundError:
        return False


# --- macOS -------------------------------------------------------------------
def _mac_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / "com.chatbotgmail.plist"


def _mac_enable() -> None:
    args = "".join(f"    <string>{part}</string>\n" for part in _command_args())
    plist = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>\n'
        "  <key>Label</key><string>com.chatbotgmail</string>\n"
        f"  <key>ProgramArguments</key><array>\n{args}  </array>\n"
        "  <key>RunAtLoad</key><true/>\n"
        "</dict></plist>\n"
    )
    path = _mac_plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plist, encoding="utf-8")


def _mac_disable() -> None:
    _mac_plist_path().unlink(missing_ok=True)


def _mac_is_enabled() -> bool:
    return _mac_plist_path().is_file()


# --- Linux -------------------------------------------------------------------
def _linux_desktop_path() -> Path:
    return Path.home() / ".config" / "autostart" / "chatbot-gmail.desktop"


def _linux_enable() -> None:
    exec_cmd = " ".join(_command_args())
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Chatbot Gmail\n"
        f"Exec={exec_cmd}\n"
        "X-GNOME-Autostart-enabled=true\n"
        "Terminal=false\n"
    )
    path = _linux_desktop_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _linux_disable() -> None:
    _linux_desktop_path().unlink(missing_ok=True)


def _linux_is_enabled() -> bool:
    return _linux_desktop_path().is_file()


def enable() -> None:
    if sys.platform.startswith("win"):
        _win_enable()
    elif sys.platform == "darwin":
        _mac_enable()
    else:
        _linux_enable()


def disable() -> None:
    if sys.platform.startswith("win"):
        _win_disable()
    elif sys.platform == "darwin":
        _mac_disable()
    else:
        _linux_disable()


def is_enabled() -> bool:
    try:
        if sys.platform.startswith("win"):
            return _win_is_enabled()
        if sys.platform == "darwin":
            return _mac_is_enabled()
        return _linux_is_enabled()
    except Exception:
        return False


def set_enabled(value: bool) -> bool:
    try:
        enable() if value else disable()
    except Exception:
        pass
    return is_enabled()
