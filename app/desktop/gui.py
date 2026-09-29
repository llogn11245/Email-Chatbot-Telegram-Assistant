import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

from app.core import config, storage
from app.desktop import autostart
from app.email import gmail_client
from app.auth import oauth

PROVIDERS = {
    "openai": ("OpenAI", ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "gpt-4.1-nano"]),
    "deepseek": ("DeepSeek", ["deepseek-chat", "deepseek-reasoner"]),
    "anthropic": (
        "Claude",
        [
            "claude-3-7-sonnet-latest",
            "claude-3-5-sonnet-latest",
            "claude-3-5-haiku-latest",
            "claude-3-opus-latest",
        ],
    ),
    "google_genai": (
        "Gemini",
        ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
    ),
}

STRINGS = {
    "vi": {
        "title": "Chatbot Gmail",
        "tab_bot": "Telegram",
        "tab_model": "Mô hình AI",
        "tab_gmail": "Google / Gmail",
        "tab_logs": "Nhật ký",
        "bot_token": "Bot token",
        "save_start": "Lưu & khởi động",
        "bot_running": "Bot đang chạy: @{u}",
        "bot_stopped": "Bot đang dừng",
        "autostart": "Khởi động cùng máy",
        "provider": "Nhà cung cấp",
        "model": "Mô hình",
        "api_key": "API key",
        "temperature": "Temperature",
        "timeout": "Timeout (giây)",
        "max_tokens": "Max tokens",
        "max_retries": "Max retries",
        "save": "Lưu",
        "saved": "Đã lưu.",
        "model_current": "Đang dùng: {provider} · {model} · key {key} · temp {temperature} · timeout {timeout} · max_tokens {max_tokens} · retries {max_retries}",
        "gcp_current": "Đang dùng OAuth client: {client_id}",
        "gcp_hint": "Dán client_secret.json hoặc nhập Client ID/Secret (OAuth client type: Desktop app).",
        "paste_json": "Nội dung client_secret.json",
        "client_id": "Client ID",
        "client_secret": "Client Secret",
        "accounts": "Tài khoản Gmail",
        "add_account": "Thêm tài khoản",
        "set_default": "Đặt mặc định",
        "rename": "Đổi nhãn",
        "remove": "Xoá",
        "is_default": "mặc định",
        "col_label": "Nhãn",
        "col_email": "Email",
        "col_default": "Mặc định",
        "refresh": "Tải lại",
        "level_all": "Tất cả",
        "need_gcp": "Cần lưu OAuth client trước.",
        "opened_browser": "Đã mở trình duyệt Google. Hoàn tất đăng nhập rồi quay lại đây.",
        "label_prompt": "Nhãn cho tài khoản:",
        "confirm_remove": "Xoá tài khoản này?",
        "error": "Lỗi",
        "info": "Thông báo",
        "language": "Ngôn ngữ",
        "quit": "Thoát",
        "logs_hint": "Log gần đây (giữ 30 ngày).",
    },
    "en": {
        "title": "Chatbot Gmail",
        "tab_bot": "Telegram",
        "tab_model": "AI model",
        "tab_gmail": "Google / Gmail",
        "tab_logs": "Logs",
        "bot_token": "Bot token",
        "save_start": "Save & start",
        "bot_running": "Bot running: @{u}",
        "bot_stopped": "Bot stopped",
        "autostart": "Start with system",
        "provider": "Provider",
        "model": "Model",
        "api_key": "API key",
        "temperature": "Temperature",
        "timeout": "Timeout (s)",
        "max_tokens": "Max tokens",
        "max_retries": "Max retries",
        "save": "Save",
        "saved": "Saved.",
        "model_current": "Active: {provider} · {model} · key {key} · temp {temperature} · timeout {timeout} · max_tokens {max_tokens} · retries {max_retries}",
        "gcp_current": "Active OAuth client: {client_id}",
        "gcp_hint": "Paste client_secret.json or enter Client ID/Secret (OAuth client type: Desktop app).",
        "paste_json": "client_secret.json content",
        "client_id": "Client ID",
        "client_secret": "Client Secret",
        "accounts": "Gmail accounts",
        "add_account": "Add account",
        "set_default": "Set default",
        "rename": "Rename",
        "remove": "Remove",
        "is_default": "default",
        "col_label": "Label",
        "col_email": "Email",
        "col_default": "Default",
        "refresh": "Refresh",
        "level_all": "All",
        "need_gcp": "Save the OAuth client first.",
        "opened_browser": "Opened Google in your browser. Finish signing in, then come back.",
        "label_prompt": "Label for this account:",
        "confirm_remove": "Remove this account?",
        "error": "Error",
        "info": "Info",
        "language": "Language",
        "quit": "Quit",
        "logs_hint": "Recent log entries (kept 30 days).",
    },
}


class SettingsApp:
    def __init__(self, app, root: tk.Tk, runtime) -> None:
        self.app = app
        self.root = root
        self.runtime = runtime
        self._oauth_server = None
        self.lang = (storage.get_settings().get("ui_language") or "vi")
        if self.lang not in STRINGS:
            self.lang = "vi"

        settings = storage.get_settings()
        self.bot_token_var = tk.StringVar()
        self.bot_status_var = tk.StringVar()
        self.autostart_var = tk.BooleanVar(value=autostart.is_enabled())
        self.provider_var = tk.StringVar()
        self.model_var = tk.StringVar(value=settings.get("llm_model") or "")
        self.api_key_var = tk.StringVar(value=settings.get("llm_api_key") or "")
        self.temperature_var = tk.StringVar(value=settings.get("llm_temperature") or "0.2")
        self.timeout_var = tk.StringVar(value=settings.get("llm_timeout") or "30")
        self.max_tokens_var = tk.StringVar(value=settings.get("llm_max_tokens") or "1000")
        self.max_retries_var = tk.StringVar(value=settings.get("llm_max_retries") or "2")
        self.gcp_json_var = tk.StringVar()
        self.client_id_var = tk.StringVar(value=settings.get("gcp_client_id") or "")
        self.client_secret_var = tk.StringVar(value=settings.get("gcp_client_secret") or "")
        self.model_summary_var = tk.StringVar()
        self.gcp_summary_var = tk.StringVar()
        self.level_vars = {lvl: tk.BooleanVar(value=True) for lvl in ("INFO", "WARNING", "ERROR")}
        self.level_all_var = tk.BooleanVar(value=True)
        self._provider_labels = {label: key for key, (label, _) in PROVIDERS.items()}
        self._pending_polls = 0

        self._build()
        self._refresh_bot_status()
        self._refresh_accounts()
        self._refresh_model_summary()
        self._refresh_gcp_summary()

    # -- helpers -----------------------------------------------------------
    def t(self, key: str) -> str:
        return STRINGS[self.lang].get(key, key)

    def _err(self, message: str) -> None:
        messagebox.showerror(self.t("error"), message)

    def _info(self, message: str) -> None:
        messagebox.showinfo(self.t("info"), message)

    # -- build -------------------------------------------------------------
    def _build(self) -> None:
        self.root.geometry("860x640")
        self.root.minsize(760, 560)

        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("TNotebook.Tab", padding=(14, 8))

        for child in self.root.winfo_children():
            child.destroy()

        header = ttk.Frame(self.root, padding=(16, 12, 16, 6))
        header.pack(fill="x")
        ttk.Label(header, text=self.t("title"), font=("Segoe UI", 16, "bold")).pack(side="left")
        lang_frame = ttk.Frame(header)
        lang_frame.pack(side="right")
        ttk.Label(lang_frame, text=self.t("language")).pack(side="left", padx=(0, 6))
        self.lang_var = tk.StringVar(value="Tiếng Việt" if self.lang == "vi" else "English")
        lang_box = ttk.Combobox(
            lang_frame, values=["Tiếng Việt", "English"], state="readonly", width=11, textvariable=self.lang_var
        )
        lang_box.pack(side="left")
        lang_box.bind("<<ComboboxSelected>>", self._on_lang)
        ttk.Button(header, text=self.t("quit"), command=self.app.quit).pack(side="right", padx=(0, 12))

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=16, pady=6)

        notebook.add(self._tab_bot(), text=self.t("tab_bot"))
        notebook.add(self._tab_model(), text=self.t("tab_model"))
        notebook.add(self._tab_gmail(), text=self.t("tab_gmail"))
        notebook.add(self._tab_logs(), text=self.t("tab_logs"))

        self.status_bar = ttk.Label(self.root, anchor="w", padding=(16, 6), foreground="#475569")
        self.status_bar.pack(fill="x")

    def _on_lang(self, _event=None) -> None:
        new_lang = "vi" if self.lang_var.get() == "Tiếng Việt" else "en"
        if new_lang != self.lang:
            self.lang = new_lang
            storage.update_settings(ui_language=new_lang)
            self._build()
            self._refresh_bot_status()
            self._refresh_accounts()

    # -- Telegram tab ------------------------------------------------------
    def _tab_bot(self) -> ttk.Frame:
        frame = ttk.Frame(self.root, padding=16)
        ttk.Label(frame, text=self.t("bot_token")).pack(anchor="w")
        entry = ttk.Entry(frame, textvariable=self.bot_token_var, show="*", width=60)
        entry.pack(anchor="w", pady=(4, 10))
        ttk.Button(frame, text=self.t("save_start"), command=self._save_bot).pack(anchor="w")
        ttk.Label(frame, textvariable=self.bot_status_var, foreground="#16a34a").pack(anchor="w", pady=(14, 0))
        ttk.Checkbutton(
            frame,
            text=self.t("autostart"),
            variable=self.autostart_var,
            command=self._toggle_autostart,
        ).pack(anchor="w", pady=(16, 0))
        return frame

    def _save_bot(self) -> None:
        token = self.bot_token_var.get().strip()
        if not token:
            self._err("Bot token trống.")
            return
        self.bot_status_var.set("...")
        threading.Thread(target=self._save_bot_worker, args=(token,), daemon=True).start()

    def _save_bot_worker(self, token: str) -> None:
        try:
            result = self.runtime.set_bot_token(token)
            self.app.post(lambda: self._after_save_bot(result, None))
        except Exception as exc:
            self.app.post(lambda: self._after_save_bot(None, exc))

    def _after_save_bot(self, result, error) -> None:
        if error is not None:
            self._err(str(error))
            self._refresh_bot_status()
            return
        self.bot_token_var.set("")
        if result.get("warning"):
            self._err(result["warning"])
        else:
            self._info(f"{self.t('saved')} @{result.get('username', '')}")
        self._refresh_bot_status()

    def _refresh_bot_status(self) -> None:
        settings = storage.get_settings()
        username = settings.get("bot_username")
        if self.runtime.is_bot_running() and username:
            self.bot_status_var.set(self.t("bot_running").format(u=username))
        elif username:
            self.bot_status_var.set(self.t("bot_running").format(u=username))
        else:
            self.bot_status_var.set(self.t("bot_stopped"))

    def _toggle_autostart(self) -> None:
        autostart.set_enabled(self.autostart_var.get())
        self.autostart_var.set(autostart.is_enabled())

    # -- AI model tab ------------------------------------------------------
    def _tab_model(self) -> ttk.Frame:
        frame = ttk.Frame(self.root, padding=16)
        settings = storage.get_settings()

        top = ttk.Frame(frame)
        top.pack(fill="x")
        ttk.Label(top, text=self.t("provider")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=6)
        labels = [PROVIDERS[k][0] for k in PROVIDERS]
        current_key = settings.get("llm_provider") or "openai"
        if current_key not in PROVIDERS:
            current_key = "openai"
        self.provider_var.set(PROVIDERS[current_key][0])
        self.provider_box = ttk.Combobox(top, values=labels, state="readonly", width=22, textvariable=self.provider_var)
        self.provider_box.grid(row=0, column=1, sticky="w", pady=6)
        self.provider_box.bind("<<ComboboxSelected>>", self._on_provider)

        ttk.Label(top, text=self.t("model")).grid(row=1, column=0, sticky="w", padx=(0, 8), pady=6)
        self.model_box = ttk.Combobox(top, width=32, textvariable=self.model_var)
        self.model_box.grid(row=1, column=1, sticky="w", pady=6)
        self._update_model_values(current_key)

        ttk.Label(top, text=self.t("api_key")).grid(row=2, column=0, sticky="w", padx=(0, 8), pady=6)
        ttk.Entry(top, textvariable=self.api_key_var, show="*", width=48).grid(row=2, column=1, sticky="w", pady=6)

        params = ttk.LabelFrame(frame, text="Parameters", padding=12)
        params.pack(fill="x", pady=(16, 0))
        for idx, (label, var) in enumerate(
            [
                (self.t("temperature"), self.temperature_var),
                (self.t("timeout"), self.timeout_var),
                (self.t("max_tokens"), self.max_tokens_var),
                (self.t("max_retries"), self.max_retries_var),
            ]
        ):
            row, col = divmod(idx, 2)
            ttk.Label(params, text=label).grid(row=row, column=col * 2, sticky="w", padx=(0, 8), pady=6)
            ttk.Entry(params, textvariable=var, width=14).grid(
                row=row, column=col * 2 + 1, sticky="w", padx=(0, 24), pady=6
            )

        ttk.Button(frame, text=self.t("save"), command=self._save_model).pack(anchor="w", pady=(16, 0))
        ttk.Label(
            frame,
            textvariable=self.model_summary_var,
            foreground="#0f172a",
            wraplength=780,
            justify="left",
        ).pack(anchor="w", pady=(12, 0))
        return frame

    def _on_provider(self, _event=None) -> None:
        key = self._provider_labels.get(self.provider_var.get(), "openai")
        self._update_model_values(key, reset=True)

    def _update_model_values(self, provider_key: str, reset: bool = False) -> None:
        models = PROVIDERS.get(provider_key, ("", []))[1]
        self.model_box.configure(values=models)
        if reset or self.model_var.get() not in models:
            if models:
                self.model_var.set(models[0])

    def _save_model(self) -> None:
        def as_float(value, default):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        def as_int(value, default):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        provider = self._provider_labels.get(self.provider_var.get(), "openai")
        storage.update_settings(
            llm_provider=provider,
            llm_model=self.model_var.get().strip(),
            llm_api_key=self.api_key_var.get().strip(),
            llm_temperature=str(as_float(self.temperature_var.get(), 0.2)),
            llm_timeout=str(as_int(self.timeout_var.get(), 30)),
            llm_max_tokens=str(as_int(self.max_tokens_var.get(), 1000)),
            llm_max_retries=str(as_int(self.max_retries_var.get(), 2)),
        )
        # Reset form để tránh rối, đồng thời hiện thông tin mô hình đang áp dụng.
        self.provider_var.set("")
        self.model_var.set("")
        self.api_key_var.set("")
        self.temperature_var.set("")
        self.timeout_var.set("")
        self.max_tokens_var.set("")
        self.max_retries_var.set("")
        self._refresh_model_summary()
        self._info(self.t("saved"))

    def _refresh_model_summary(self) -> None:
        s = storage.get_settings()
        provider = s.get("llm_provider")
        model = s.get("llm_model")
        if not (provider and model):
            self.model_summary_var.set("")
            return
        label = PROVIDERS.get(provider, (provider, []))[0]
        key = s.get("llm_api_key") or ""
        masked = f"…{key[-4:]}" if len(key) >= 4 else "(chưa có)"
        self.model_summary_var.set(
            self.t("model_current").format(
                provider=label,
                model=model,
                key=masked,
                temperature=s.get("llm_temperature") or "-",
                timeout=s.get("llm_timeout") or "-",
                max_tokens=s.get("llm_max_tokens") or "-",
                max_retries=s.get("llm_max_retries") or "-",
            )
        )

    # -- Google / Gmail tab ------------------------------------------------
    def _tab_gmail(self) -> ttk.Frame:
        frame = ttk.Frame(self.root, padding=16)
        ttk.Label(frame, text=self.t("gcp_hint"), wraplength=780, foreground="#475569").pack(anchor="w")
        ttk.Label(frame, text=self.t("paste_json")).pack(anchor="w", pady=(10, 2))
        ttk.Entry(frame, textvariable=self.gcp_json_var, width=90).pack(anchor="w")
        row = ttk.Frame(frame)
        row.pack(anchor="w", pady=(8, 0))
        ttk.Label(row, text=self.t("client_id")).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        ttk.Entry(row, textvariable=self.client_id_var, width=52).grid(row=0, column=1, sticky="w", pady=4)
        ttk.Label(row, text=self.t("client_secret")).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)
        ttk.Entry(row, textvariable=self.client_secret_var, show="*", width=52).grid(
            row=1, column=1, sticky="w", pady=4
        )
        ttk.Button(frame, text=self.t("save"), command=self._save_gcp).pack(anchor="w", pady=(8, 4))
        ttk.Label(
            frame,
            textvariable=self.gcp_summary_var,
            foreground="#0f172a",
            wraplength=780,
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(frame, text=self.t("accounts"), font=("Segoe UI", 10, "bold")).pack(anchor="w")
        columns = ("label", "email", "default")
        self.accounts_tree = ttk.Treeview(frame, columns=columns, show="headings", height=6)
        self.accounts_tree.heading("label", text=self.t("col_label"))
        self.accounts_tree.heading("email", text=self.t("col_email"))
        self.accounts_tree.heading("default", text=self.t("col_default"))
        self.accounts_tree.column("label", width=150)
        self.accounts_tree.column("email", width=340)
        self.accounts_tree.column("default", width=100, anchor="center")
        self.accounts_tree.pack(fill="x", pady=(6, 8))

        buttons = ttk.Frame(frame)
        buttons.pack(anchor="w")
        self.add_btn = ttk.Button(buttons, text=self.t("add_account"), command=self._add_account)
        self.add_btn.pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text=self.t("set_default"), command=self._set_default_account).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(buttons, text=self.t("rename"), command=self._rename_account).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text=self.t("remove"), command=self._remove_account).pack(side="left")
        return frame

    def _gcp_configured(self) -> bool:
        try:
            oauth.get_gcp_credentials()
            return True
        except Exception:
            return False

    def _save_gcp(self) -> None:
        client_id = self.client_id_var.get().strip()
        client_secret = self.client_secret_var.get().strip()
        raw = self.gcp_json_var.get().strip()
        if raw:
            try:
                parsed = gmail_client.parse_client_secret_json(raw)
                client_id, client_secret = parsed["client_id"], parsed["client_secret"]
            except Exception as exc:
                self._err(str(exc))
                return
        if not (client_id and client_secret):
            self._err("Thiếu client_id / client_secret.")
            return
        storage.update_settings(gcp_client_id=client_id, gcp_client_secret=client_secret)
        # Reset ô nhập sau khi lưu để tránh rối.
        self.client_id_var.set("")
        self.client_secret_var.set("")
        self.gcp_json_var.set("")
        self._refresh_gcp_summary()
        self._info(self.t("saved"))

    def _refresh_gcp_summary(self) -> None:
        client_id = storage.get_settings().get("gcp_client_id")
        if not client_id:
            self.gcp_summary_var.set("")
            return
        self.gcp_summary_var.set(self.t("gcp_current").format(client_id=client_id))

    def _selected_account_id(self):
        selection = self.accounts_tree.selection()
        if not selection:
            return None
        return int(selection[0])

    def _refresh_accounts(self) -> None:
        if not hasattr(self, "accounts_tree"):
            return
        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)
        for account in storage.list_gmail_accounts():
            self.accounts_tree.insert(
                "",
                "end",
                iid=str(account["id"]),
                values=(
                    account["label"] or "",
                    account["email"],
                    self.t("is_default") if account["is_default"] else "",
                ),
            )

    def _add_account(self) -> None:
        if not self._gcp_configured():
            self._err(self.t("need_gcp"))
            return
        try:
            server, url = oauth.start_callback_flow()
            webbrowser.open(url)
        except Exception as exc:
            self._err(str(exc))
            return
        self._oauth_server = server
        before = len(storage.list_gmail_accounts())
        self._pending_polls = 60
        self._info(self.t("opened_browser"))
        self._poll_accounts(before)

    def _stop_oauth_server(self) -> None:
        server = getattr(self, "_oauth_server", None)
        if server is not None:
            try:
                server.stop()
            except Exception:
                pass
            self._oauth_server = None

    def _poll_accounts(self, before: int) -> None:
        if self._pending_polls <= 0:
            self._stop_oauth_server()
            return
        self._pending_polls -= 1
        if len(storage.list_gmail_accounts()) > before:
            self._stop_oauth_server()
            self._refresh_accounts()
            self._info(self.t("saved"))
            return
        self.root.after(2000, lambda: self._poll_accounts(before))

    def _set_default_account(self) -> None:
        account_id = self._selected_account_id()
        if account_id is None:
            return
        storage.set_default_gmail_account(account_id)
        self._refresh_accounts()

    def _rename_account(self) -> None:
        account_id = self._selected_account_id()
        if account_id is None:
            return
        current = next(
            (a["label"] for a in storage.list_gmail_accounts() if a["id"] == account_id), ""
        )
        label = simpledialog.askstring(self.t("rename"), self.t("label_prompt"), initialvalue=current)
        if label is not None:
            storage.update_gmail_account(account_id, label=label.strip())
            self._refresh_accounts()

    def _remove_account(self) -> None:
        account_id = self._selected_account_id()
        if account_id is None:
            return
        if not messagebox.askyesno(self.t("remove"), self.t("confirm_remove")):
            return
        storage.remove_gmail_account(account_id)
        gmail_client.clear_cache()
        self._refresh_accounts()

    # -- Logs tab ----------------------------------------------------------
    def _tab_logs(self) -> ttk.Frame:
        frame = ttk.Frame(self.root, padding=16)
        controls = ttk.Frame(frame)
        controls.pack(fill="x")
        ttk.Label(controls, text=self.t("logs_hint"), foreground="#475569").pack(side="left")
        ttk.Label(controls, text="  Level:").pack(side="left", padx=(12, 4))
        ttk.Checkbutton(
            controls,
            text=self.t("level_all"),
            variable=self.level_all_var,
            command=self._toggle_all_levels,
        ).pack(side="left")
        for level in ("INFO", "WARNING", "ERROR"):
            ttk.Checkbutton(
                controls,
                text=level,
                variable=self.level_vars[level],
                command=self._on_level_change,
            ).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text=self.t("refresh"), command=self._refresh_logs).pack(side="left", padx=8)

        # Kích thước cố định; văn bản dài sẽ tự xuống dòng (wrap).
        self.logs_text = ScrolledText(frame, height=26, wrap="word", font=("Consolas", 9))
        self.logs_text.pack(fill="x", expand=False, pady=(8, 0))
        self._refresh_logs()
        return frame

    def _toggle_all_levels(self) -> None:
        value = self.level_all_var.get()
        for var in self.level_vars.values():
            var.set(value)
        self._refresh_logs()

    def _on_level_change(self) -> None:
        self.level_all_var.set(all(var.get() for var in self.level_vars.values()))
        self._refresh_logs()

    def _refresh_logs(self) -> None:
        selected = {lvl for lvl, var in self.level_vars.items() if var.get()}
        if not selected:
            lines: list[str] = []
        else:
            path = config.LOG_DIR / "app.log"
            if not path.is_file():
                lines = ["(no log yet)"]
            else:
                try:
                    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                except OSError as exc:
                    lines = [f"error reading log: {exc}"]
                if len(selected) < len(self.level_vars):
                    lines = [
                        line for line in lines if any(f"| {lvl} |" in line for lvl in selected)
                    ]
        self.logs_text.configure(state="normal")
        self.logs_text.delete("1.0", "end")
        self.logs_text.insert("end", "\n".join(lines[-400:]))
        self.logs_text.see("end")
        self.logs_text.configure(state="disabled")
