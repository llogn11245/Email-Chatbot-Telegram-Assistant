import os
import queue
import sys
import threading
import time

from app.core import config, paths
from app.core.observability import record_event, setup_logging
from app.desktop.runtime import Runtime


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
        self.runtime = Runtime()
        self._root = None
        self._tray = None
        self._tray_available = False
        self._queue: queue.Queue = queue.Queue()
        self._quitting = False

    # -- thread-safe commands ---------------------------------------------
    def post(self, func) -> None:
        self._queue.put(func)

    def _pump(self) -> None:
        try:
            while True:
                self._queue.get_nowait()()
        except queue.Empty:
            pass
        if self._root is not None and not self._quitting:
            self._root.after(100, self._pump)

    # -- tray callbacks ----------------------------------------------------
    def open_settings(self) -> None:
        if self._root is not None:
            self.post(self._show_window)

    def _show_window(self) -> None:
        try:
            self._root.deiconify()
            self._root.lift()
            self._root.focus_force()
        except Exception:
            pass

    def autostart_enabled(self) -> bool:
        from app.desktop import autostart

        return autostart.is_enabled()

    def toggle_autostart(self) -> None:
        from app.desktop import autostart

        autostart.set_enabled(not autostart.is_enabled())

    def quit(self) -> None:
        if self._root is not None:
            self.post(self._do_quit)
        else:
            self._do_quit()

    def _do_quit(self) -> None:
        self._quitting = True
        try:
            if self._root is not None:
                self._root.destroy()
        except Exception:
            pass

    # -- lifecycle ---------------------------------------------------------
    def _on_window_close(self) -> None:
        if self._tray_available:
            self._root.withdraw()
        else:
            self._do_quit()

    def _start_tray(self) -> None:
        if not (sys.platform.startswith("win") or sys.platform == "darwin"):
            if os.environ.get("CHATBOT_GMAIL_TRAY") != "1":
                record_event("INFO", "desktop", "tray disabled on this platform")
                return
        try:
            import logging as _logging

            _logging.getLogger("pystray").setLevel(_logging.CRITICAL)
            from app.desktop.tray import build_tray

            self._tray = build_tray(self)
            threading.Thread(target=self._tray.run, name="tray", daemon=True).start()
            self._tray_available = True
            record_event("INFO", "desktop", "tray started")
        except Exception as exc:
            record_event("WARNING", "desktop", f"tray unavailable: {exc}")

    def _gui_precheck(self) -> str | None:
        """Trả về thông báo nếu không thể mở GUI, ngược lại None."""
        try:
            import tkinter as tk
        except ImportError:
            return "Tkinter chưa được cài (Linux: 'sudo apt install python3-tk'; Windows: có sẵn)"
        try:
            probe = tk.Tk()
            probe.destroy()
        except tk.TclError as exc:
            return f"Không có display cho GUI ({exc})"
        return None

    def _run_gui(self) -> None:
        import tkinter as tk

        from app.desktop.gui import SettingsApp

        root = tk.Tk()
        self._root = root
        root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        SettingsApp(self, root, self.runtime)
        self._start_tray()
        root.after(100, self._pump)
        root.mainloop()

    def _run_headless(self) -> None:
        print("[Chatbot Gmail] Không có GUI/display — đang chạy nền (bot). Ctrl+C để thoát.")
        try:
            while not self._quitting:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def _shutdown(self) -> None:
        record_event("INFO", "desktop", "shutting down")
        try:
            if self._tray is not None:
                self._tray.stop()
        except Exception:
            pass
        self.runtime.stop()

    def run(self) -> None:
        instance = SingleInstance()
        if not instance.acquire():
            print("Chatbot Gmail đang chạy rồi.")
            return

        setup_logging()
        record_event("INFO", "desktop", f"start (data={config.DATA_DIR})")

        self.runtime.start()

        issue = self._gui_precheck()
        if issue:
            record_event("WARNING", "desktop", f"{issue} -> chạy nền (headless).")
            self._run_headless()
            self._shutdown()
            instance.release()
            return

        try:
            self._run_gui()
        except Exception as exc:
            record_event("ERROR", "desktop", f"GUI failed: {exc}", exc=exc)
            self._run_headless()
        finally:
            self._shutdown()
            instance.release()


def main() -> None:
    DesktopApp().run()
