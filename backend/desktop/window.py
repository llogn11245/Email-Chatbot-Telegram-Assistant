class SettingsWindow:
    """Bọc pywebview: cửa sổ Settings; đóng thì ẩn, không thoát app."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.window = None
        self._webview = None

    def start(self) -> None:
        import webview

        self._webview = webview
        self.window = webview.create_window(
            "Chatbot Gmail",
            self.url,
            width=940,
            height=780,
            min_size=(720, 560),
        )
        self.window.events.closing += self._on_closing
        webview.start()

    def _on_closing(self):
        try:
            self.window.hide()
        except Exception:
            pass
        return False

    def show(self) -> None:
        try:
            self.window.show()
        except Exception:
            pass
