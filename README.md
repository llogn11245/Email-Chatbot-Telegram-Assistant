# Chatbot Gmail

Ứng dụng **desktop** (Windows-first) chạy nền: trợ lý email AI qua **Telegram**. User cài một lần, mở **Settings (native GUI - Tkinter)** để cấu hình bot token, model AI và kết nối Gmail; sau đó chat với bot để tìm/đọc/tóm tắt email và soạn & gửi email (luôn có xác nhận).

- **Chạy nền dạng tray** — không cần Docker, không cần hosting, không cần URL public.
- **Native GUI (Tkinter/ttk)** — không dùng webview, không có front-end web.
- **Nhiều tài khoản Gmail** với nhãn tùy chỉnh và một tài khoản mặc định.
- **4 nhà cung cấp model:** OpenAI, DeepSeek, Claude (Anthropic), Gemini (Google) — kèm tham số (temperature, timeout, max_tokens, max_retries).
- **SQLite** trong thư mục dữ liệu người dùng; secrets mã hoá Fernet.
- **Log ra file** (30 ngày) + tab **Logs** trong Settings.
- Vi/EN.

```
Desktop app (resident)
  ├── Runtime (thread nền): BotManager — long-poll Telegram
  ├── Settings — native GUI (Tkinter/ttk); đóng → thu về tray, click tray mở lại
  ├── OAuth loopback server (stdlib) — chỉ chạy khi thêm tài khoản Gmail
  └── SQLite + Fernet trong thư mục dữ liệu người dùng
```

## Cài đặt & chạy (dev)

Yêu cầu: Python 3.12 (Tkinter có sẵn trong bản Python chính thức). Không cần Node.js.

- Windows/macOS: Tkinter có sẵn.
- Linux/WSL: cần `sudo apt install python3-tk` và một display (Windows 11 có WSLg).

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt     # Windows: venv\Scripts\pip
python -m app                                # chạy app desktop (native GUI + tray)
```

App mở cửa sổ Settings; đóng cửa sổ thì chạy nền ở khay hệ thống. Nhấn icon khay để mở lại, bật/tắt "Khởi động cùng máy", hoặc thoát.

> Nếu môi trường không có display (vd dev trong WSL/Linux headless), app tự chuyển sang chế độ nền chỉ chạy bot (in hướng dẫn ra console).

## Cấu hình (trong Settings)

1. **Telegram** — tạo bot với @BotFather, dán token, bấm Lưu & khởi động. Bật "Khởi động cùng máy" nếu muốn.
2. **AI model** — chọn provider (OpenAI / DeepSeek / Claude / Gemini), model, API key; chỉnh temperature/timeout/max_tokens/max_retries.
3. **Google / Gmail** — dán nội dung `client_secret.json` (hoặc Client ID/Secret). Bấm **Add account** để mở trình duyệt đăng nhập Google; thêm nhiều tài khoản, đặt nhãn và tài khoản mặc định.
4. **Logs** — xem log gần đây, lọc theo mức.

## Google OAuth client (làm 1 lần)

1. [Google Cloud Console](https://console.cloud.google.com/) → tạo project (không cần billing).
2. **APIs & Services → Library** → bật **Gmail API**.
3. **OAuth consent screen**: User type **External**; thêm email của bạn vào **Test users**.
   - **Quan trọng:** bấm **Publish app** (In production). Nếu để *Testing*, refresh token hết hạn sau 7 ngày.
   - Cảnh báo "chưa verified" là bình thường với scope Gmail.
4. **Credentials → Create Credentials → OAuth client ID** → type **Desktop app** → tải JSON.
5. Dán JSON vào tab "Google / Gmail" của Settings.

Scope dùng: `gmail.readonly` + `gmail.send`. Redirect dùng loopback `http://localhost:<port>/` (port ngẫu nhiên do app tự mở khi thêm tài khoản — Desktop client cho phép mọi port loopback).

## Hành vi nhiều tài khoản

- **Tìm kiếm:** mặc định ở **tài khoản mặc định**; chỉ tìm ở tài khoản khác khi bạn nói rõ.
- **Đọc email:** agent dùng đúng tài khoản đã tìm ra email.
- **Gửi email:** nếu bạn nói rõ gửi từ tài khoản nào thì dùng tài khoản đó; nếu chưa rõ và có nhiều tài khoản, bot **hỏi lại** trước khi gửi.
- Email chỉ được gửi sau khi bạn bấm nút **Gửi** xác nhận trong Telegram.

## Dữ liệu & bảo mật

- Dữ liệu lưu ở thư mục người dùng (`platformdirs`):
  - Windows: `%LOCALAPPDATA%\ChatbotGmail\`
  - macOS: `~/Library/Application Support/ChatbotGmail/`
  - Linux: `~/.local/share/ChatbotGmail/`
- `app.db` (SQLite) + `secret.key` (khoá mã hoá) + `app.lock` (single instance).
- **Mã hoá Fernet**: `bot_token`, `llm_api_key`, `gcp_client_secret`, `refresh_token` của từng tài khoản Gmail.
- Không lưu nội dung email hay lịch sử hội thoại; không dùng mật khẩu Gmail (chỉ OAuth refresh token).
- Log ở `.../ChatbotGmail/log/app.log` (và `error.log`), tự xoay vòng theo ngày, giữ 30 ngày.

## Build bản Windows (.exe)

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
# -> dist\ChatbotGmail\ChatbotGmail.exe   (onedir)
```

Script sẽ: cài deps Python + PyInstaller → chạy PyInstaller → (tạo installer nếu có Inno Setup 6).

Chạy PyInstaller trực tiếp:

```powershell
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --clean packaging\pyinstaller\chatbot-gmail.spec
```

Lưu ý:
- Dùng **venv riêng**; đảm bảo `pip` và `PyInstaller` dùng **cùng một Python** (không dùng conda base). Spec sẽ **báo lỗi rõ** nếu thiếu package.
- PyInstaller **không cross-compile** — build Windows trên Windows, macOS/Linux cần build riêng.
- Build ở đường dẫn ổ đĩa bình thường (tránh thư mục UNC kiểu `\\wsl.localhost\...`).

## Cấu trúc thư mục

```
app/
  __main__.py            # entry: python -m app
  core/                  # nền tảng dùng chung
    config.py            # env + paths
    paths.py             # platformdirs, secret key, resource path
    storage.py           # SQLAlchemy (SQLite) + Fernet, migration
    i18n.py              # chuỗi vi/en cho bot
    observability/       # logging file, AppError, event_ref, context
  auth/
    oauth.py             # Google OAuth: consent URL, loopback callback server
  email/
    gmail_client.py      # Gmail API: search/read/send/profile (nhiều tài khoản)
  agent/
    llm.py               # init_chat_model (4 provider) — lazy import
    tools.py             # registry tools Gmail
    graph.py             # run_agent (lazy import langchain/langgraph)
    retriever.py         # Retriever protocol + NullRetriever (seam RAG)
    embeddings.py        # seam embeddings
    pipeline/            # state + builder
  telegram/
    manager.py           # start/stop/restart bot
    handlers.py          # /start /setup /status /accounts /language, chat, xác nhận gửi
  desktop/               # native GUI + tray + lifecycle
    app.py               # DesktopApp: single-instance, tray, GUI main loop
    gui.py               # Settings (Tkinter/ttk), 4 tab
    runtime.py           # runtime bot (asyncio loop trong thread nền)
    tray.py              # pystray
    autostart.py         # Windows/macOS/Linux
packaging/               # PyInstaller spec + Inno Setup + entry
assets/                  # icon
docs/RAG_DESIGN.md       # thiết kế mở rộng RAG
```

## Hạn chế đã biết

- Bot chỉ online khi app đang chạy (máy bật). Tin nhắn trong ~24h sẽ được xử lý khi app bật lại.
- Windows-first; macOS/Linux cần `pystray` backend tương ứng (Tkinter có sẵn trong Python).
- RAG chưa hiện thực — đã chừa seam (xem `docs/RAG_DESIGN.md`).

## Khắc phục sự cố

- **Chat bot báo `OpenAIConnectionError: Connection error` (kèm `TypeError: process() takes no keyword arguments` trong `httpx2/_decoders.py`):** đây là lỗi giải mã **brotli** của `httpx2` (thư viện HTTP mà `openai` dùng) khi server trả `Content-Encoding: br`. Bản mới đã tự gửi `Accept-Encoding: gzip, deflate` nên không còn gặp. Nếu vẫn gặp, gỡ brotli trong đúng môi trường chạy:
  ```bash
  pip uninstall -y brotli brotlicffi
  ```
  Nguyên nhân thường gặp: chạy bằng **conda base** (có sẵn `brotli`). Khuyến nghị dùng **venv riêng**.
- **`ModuleNotFoundError: No module named 'tkinter'` (Linux/WSL):** cài `sudo apt install python3-tk` (Windows/macOS có sẵn).
