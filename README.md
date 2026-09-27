# Chatbot Gmail

Ứng dụng desktop (Windows-first) chạy nền: trợ lý email AI qua **Telegram**. User cài một lần, mở **Settings (native GUI)** để cấu hình bot token, model AI và kết nối Gmail; sau đó chat với bot để tìm/đọc/tóm tắt email và soạn & gửi email (luôn có xác nhận).

- **Chạy nền dạng tray** — không cần Docker, không cần hosting, không cần URL public.
- **Native GUI (Tkinter/ttk)** — cửa sổ Settings thật, không dùng webview.
- **Nhiều tài khoản Gmail** với nhãn tùy chỉnh và một tài khoản mặc định.
- **4 nhà cung cấp model:** OpenAI, DeepSeek, Claude (Anthropic), Gemini (Google) — kèm tham số (temperature, timeout, max_tokens, max_retries).
- **SQLite** trong thư mục dữ liệu người dùng; secrets mã hoá Fernet.
- **Log ra file** (30 ngày) + tab **Logs** trong Settings để xem sự cố.
- Vi/EN.

```
Tray app (resident)
  ├── asyncio loop: BotManager (long-poll Telegram) + Web server 127.0.0.1 (OAuth callback)
  ├── Cửa sổ Settings — native GUI (Tkinter/ttk) ← đóng thì thu về tray, click tray mở lại
  └── SQLite + Fernet trong thư mục dữ liệu người dùng
```

## Cài đặt & chạy (dev)

Yêu cầu: Python 3.12 (Tkinter có sẵn trong bản Python chính thức). Node.js chỉ cần nếu bạn muốn dùng **UI web cho chế độ headless**.

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt     # Windows: venv\Scripts\pip
# chạy app desktop (native GUI + tray)
python -m backend
```

App mở cửa sổ Settings; đóng cửa sổ thì chạy nền ở khay hệ thống. Nhấn icon khay để mở lại, bật/tắt "Khởi động cùng máy", hoặc thoát.

> Nếu môi trường không có GUI/display (vd dev trong WSL), app tự chuyển sang chế độ headless: chạy web server và mở trình duyệt (UI web React). Chế độ này cần build `frontend/dist`:
> `cd frontend && npm install && npm run build`.

## Cấu hình (trong Settings)

1. **Bot Telegram** — tạo bot với @BotFather, dán token. Bot tự khởi động lại khi lưu.
2. **Model AI** — chọn provider (OpenAI / DeepSeek / Claude / Gemini), model, API key; mở "Tham số nâng cao" để chỉnh temperature/timeout/max_tokens/max_retries.
3. **Google OAuth client** — dán nội dung `client_secret.json`.
4. **Tài khoản Gmail** — bấm **Add account** (mở trình duyệt để đăng nhập Google), thêm nhiều tài khoản, đặt nhãn và tài khoản mặc định.

## Google OAuth client (làm 1 lần)

1. [Google Cloud Console](https://console.cloud.google.com/) → tạo project (không cần billing).
2. **APIs & Services → Library** → bật **Gmail API**.
3. **OAuth consent screen**: User type **External**; thêm email của bạn vào **Test users**.
   - **Quan trọng:** bấm **Publish app** (In production). Nếu để *Testing*, refresh token hết hạn sau 7 ngày.
   - Cảnh báo "chưa verified" là bình thường với scope Gmail.
4. **Credentials → Create Credentials → OAuth client ID** → type **Desktop app** → tải JSON.
5. Dán JSON vào bước 3 của Settings.

Scope dùng: `gmail.readonly` + `gmail.send`.

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

Cần: Python 3.12. Node.js **không bắt buộc** (repo đã kèm sẵn `frontend/dist`).

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
# -> dist\ChatbotGmail\ChatbotGmail.exe   (onedir)

# tuỳ chọn
#   -SkipFrontend   : không build lại UI
#   -SkipInstaller  : không tạo installer
```

Script sẽ: cài deps Python + PyInstaller → (build frontend nếu cần) → chạy PyInstaller → (tạo installer nếu có Inno Setup 6).

Nếu muốn chạy PyInstaller trực tiếp (đảm bảo `frontend/dist` đã có):

```powershell
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --clean packaging\pyinstaller\chatbot-gmail.spec
```

Lưu ý:
- PyInstaller **không cross-compile** — build Windows trên Windows, macOS/Linux cần build riêng.
- `frontend/dist` được commit sẵn trong repo. Nếu bạn sửa UI, chạy `cd frontend && npm install && npm run build` rồi commit lại `frontend/dist`.
- Build ở đường dẫn ổ đĩa Windows bình thường (tránh thư mục UNC kiểu `\\wsl.localhost\...`).

## Cấu trúc thư mục

```
backend/
  config.py             # env + paths (SQLite, SECRET_KEY, resource path)
  paths.py              # platformdirs, secret key, resource path khi đóng gói
  storage.py            # SQLAlchemy (SQLite) + Fernet, migration
  i18n.py               # chuỗi vi/en cho bot
  main.py               # entry dev headless (web + bot)
  __main__.py           # entry desktop: python -m backend
  observability/        # logging file, AppError, event_ref, context
  desktop/              # tray, native GUI (Tkinter/ttk), autostart, service runner
  email_services/       # gmail_client (nhiều tài khoản)
  web/                  # FastAPI: setup API, OAuth callback, /api/logs
  bot/                  # aiogram handlers + manager
  agent/
    llm.py              # init_chat_model (4 provider) — lazy import
    tools.py            # registry tools Gmail
    graph.py            # run_agent (lazy import langchain/langgraph)
    pipeline/           # state + builder (seam RAG)
    retriever.py        # Retriever protocol + NullRetriever
    embeddings.py       # seam embeddings
frontend/               # React (Vite) — UI web chỉ cho chế độ headless (tuỳ chọn)
packaging/              # PyInstaller spec + Inno Setup + entry
assets/                 # icon
docs/RAG_DESIGN.md      # thiết kế mở rộng RAG
```

## Hạn chế đã biết

- Bot chỉ online khi app đang chạy (máy bật). Tin nhắn trong ~24h sẽ được xử lý khi app bật lại.
- Windows-first; macOS/Linux cần `pystray` backend tương ứng (Tkinter có sẵn trong Python).
- RAG chưa hiện thực — đã chừa seam (xem `docs/RAG_DESIGN.md`).
