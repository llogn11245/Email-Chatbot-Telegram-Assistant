import sys
import threading
import time

from backend import config, paths
from backend.desktop.services import ServiceRunner
from backend.observability import record_event, setup_logging


class SingleInstance:
    def __init__(self) -> None:
        self._fh = None
        self._path = paths.data_dir() / "app.lock"

    def acquire(self) -> bool:
        self._fh = open(self._path, "a+")
        try:
            if sys.platform.startswith("win"):
                import msvcrt

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            self._fh.close()
            self._fh = None
            return False

    def release(self) -> None:
        if self._fh is None:
            return
        try:
            if sys.platform.startswith("win"):
                import msvcrt

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fh, fcntl.LOCK_UN)
        except Exception:
            pass
        finally:
            self._fh.close()
            self._fh = None


class DesktopApp:
    def __init__(self) -> None:
        self.services = ServiceRunner()
        self._tray = None
        self._window = None
        self._window_thread = None
        self._quitting = False

    def open_settings(self) -> None:
        self.services.start(wait=False)
        self.services.wait_until_ready(timeout=15)
        if self._window is not None:
            self._window.show()
            return
        self._start_window()

    def _start_window(self) -> None:
        from backend.desktop.window import SettingsWindow

        self._window = SettingsWindow(self.services.url)
        self._window_thread = threading.Thread(
            target=self._window.start, name="settings-window", daemon=True
        )
        self._window_thread.start()

    def autostart_enabled(self) -> bool:
        from backend.desktop import autostart

        return autostart.is_enabled()

    def toggle_autostart(self) -> None:
        from backend.desktop import autostart

        autostart.set_enabled(not autostart.is_enabled())

    def quit(self) -> None:
        if self._quitting:
            return
        self._quitting = True
        record_event("INFO", "desktop", "shutting down")
        try:
            if self._tray is not None:
                self._tray.stop()
        except Exception:
            pass
        try:
            if self._window is not None and self._window.window is not None:
                import webview

                webview.destroy_window(self._window.window)
        except Exception:
            pass
        self.services.stop()

    def _run_headless(self) -> None:
        import webbrowser

        self.services.start()
        self.services.wait_until_ready(timeout=30)
        webbrowser.open(self.services.url)
        record_event("INFO", "desktop", "headless mode (no tray). Ctrl+C to quit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.quit()

    def run(self) -> None:
        instance = SingleInstance()
        if not instance.acquire():
            record_event("WARNING", "desktop", "another instance is already running")
            print("Chatbot Gmail đang chạy rồi.")
            return

        setup_logging()
        record_event("INFO", "desktop", f"start (data={config.DATA_DIR})")

        try:
            from backend.desktop.tray import build_tray
        except Exception as exc:
            record_event("ERROR", "desktop", f"tray unavailable: {exc}", exc=exc)
            self._run_headless()
            instance.release()
            return

        self.services.start()
        self.services.wait_until_ready(timeout=30)
        self._start_window()
        try:
            self._tray = build_tray(self)
            self._tray.run()
        except Exception as exc:
            record_event("ERROR", "desktop", f"tray failed: {exc}", exc=exc)
            self._run_headless()
        finally:
            self.quit()
            instance.release()


def main() -> None:
    DesktopApp().run()
