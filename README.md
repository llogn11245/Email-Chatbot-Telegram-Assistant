# Chatbot Gmail — AI Agent trợ lý email qua Telegram

Agent AI tự-host giúp bạn làm việc với Gmail qua **Telegram**: tìm và đọc email, tóm tắt hộp thư, soạn & gửi email (luôn có bước xác nhận của con người).

- **Chat front:** Telegram bot
- **Control panel:** Web (FastAPI + React) để nhập **bot token**, **API key LLM**, và kết nối Gmail — không cần cấu hình gì trong `.env` cho các phần này
- **Agent core:** LangGraph + tool-calling, dùng model qua 4 nhà cung cấp: **OpenAI**, **DeepSeek**, **Claude** (Anthropic), **Gemini** (Google)
- **Storage:** PostgreSQL, dữ liệu nhạy cảm mã hoá Fernet
- **Đa ngôn ngữ:** Tiếng Việt / English (đổi trên web hoặc `/language` trong bot)

```
Telegram (aiogram) ──┐
                     ├── Agent (LangGraph + tools) ── email_services (Gmail API)
Web UI (React) ── FastAPI ─┘         │
                                     ▼
                     PostgreSQL (bot token / key / token mã hoá Fernet)
```

## Tính năng

- Đọc/tìm email bằng câu hỏi tự nhiên
- Agent tự soạn nội dung trả lời
- Email chỉ được gửi sau khi bấm nút **Gửi** xác nhận trong Telegram (human-in-the-loop)
- Setup một lần qua web wizard; bot tự khởi động lại khi lưu token
- Không expose cổng public: bot dùng long-polling

## Yêu cầu

- Docker & Docker Compose (đã gồm PostgreSQL)
- Tài khoản Telegram (tạo bot với @BotFather)
- Một model của OpenAI / DeepSeek / Anthropic / Google Gemini (kèm API key tương ứng)
- Tài khoản Google + OAuth Client ID loại **Desktop app** (tạo một lần, ~10 phút)

## Quickstart (Docker)

```bash
cp .env.example .env
# sửa .env: đổi SECRET_KEY (bắt buộc nên đổi)
docker compose up -d --build
```

Mở `http://localhost:8000`, làm 4 bước:

1. **Bot Telegram** — tạo bot với @BotFather, dán token. Hệ thống kiểm tra token rồi tự khởi động bot.
2. **Cấu hình mô hình AI** — chọn provider (OpenAI / DeepSeek / Claude / Gemini), model và dán API key; tuỳ chỉnh temperature, timeout, max_tokens, max_retries trong mục nâng cao.
3. **Google OAuth client** — dán nội dung `client_secret.json`.
4. **Connect Gmail** — đăng nhập Google, cho phép.

Rồi mở Telegram, nhắn bot: *"Tóm tắt 5 email mới nhất của tôi"*, hoặc `/status`, `/language`.

## Lưu ý về lưu trữ (bot token & API key)

Bot token và API key LLM **được lưu trong PostgreSQL**, mã hoá bằng Fernet với khoá dẫn xuất từ `SECRET_KEY`. Lý do:

- Bot token không còn nằm trong `.env`, nên user tự-host chỉ cần thao tác trên web.
- Khi lưu bot token, backend validate qua Telegram (`get_me`) rồi khởi động lại bot ngay trong tiến trình đang chạy.
- `SECRET_KEY` **phải giữ cố định**; đổi nó sẽ không giải mã được dữ liệu cũ.

## Hướng dẫn tạo Google OAuth client (làm 1 lần)

1. Vào [Google Cloud Console](https://console.cloud.google.com/) → tạo project (không cần billing).
2. **APIs & Services → Library** → **Gmail API** → **Enable**.
3. **OAuth consent screen**: User type **External**, điền tên app; thêm email của bạn vào **Test users**.
   - **Quan trọng:** bấm **Publish app** (In production). Nếu để *Testing*, refresh token **hết hạn sau 7 ngày**.
   - Cảnh báo *"Google hasn't verified this app"* là bình thường với scope Gmail.
4. **Credentials → Create Credentials → OAuth client ID** → type **Desktop app** → **Download JSON**.
5. Dán nội dung JSON vào bước 3 của web wizard.

Scope dùng: `gmail.readonly` + `gmail.send`.

## Biến môi trường

| Biến | Bắt buộc | Mô tả |
|---|---|---|
| `SECRET_KEY` | Có | Khoá mã hoá dữ liệu. Tạo: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `DATABASE_URL` | Có | Mặc định `postgresql+psycopg://chatbot:chatbot@localhost:5432/chatbot` (Docker tự trỏ vào service `db`) |
| `TELEGRAM_ADMIN_ID` | Không | Nếu set, chỉ chat_id này được dùng bot |
| `WEB_HOST` / `WEB_PORT` | Không | Mặc định `0.0.0.0` / `8000` |
| `WEB_URL` | Không | URL control panel hiển thị cho user |
| `RUN_MODE` | Không | `both` (mặc định), `bot`, `web` |
| `ADMIN_PASSWORD` | Không | Nếu set, API setup cần header `X-Admin-Token` |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Không | Đặt qua env để bỏ qua bước 3 |

> `BOT_TOKEN` và `LLM_*` trong `.env` **không còn được dùng** — nhập qua web.

## Chạy không cần Docker (dev)

Cần một PostgreSQL (local hoặc container), rồi:

```bash
cp .env.example .env            # đổi SECRET_KEY, trỏ DATABASE_URL tới DB của bạn
venv/bin/pip install -r requirements.txt
venv/bin/python -m backend.main # web http://localhost:8000 + bot

cd frontend && npm install && npm run dev   # http://localhost:5173, proxy /api -> :8000
```

## Cấu trúc thư mục

```
backend/
  config.py              # env config
  storage.py             # PostgreSQL (SQLAlchemy) + Fernet
  i18n.py                # chuỗi vi/en cho bot
  main.py                # chạy đồng thời web + bot (RUN_MODE)
  email_services/        # dịch vụ email
    gmail_client.py      # Gmail API: search/read/send/profile + scopes
  web/                   # giao diện web + luồng OAuth
    __init__.py          # export app/create_app/set_bot_manager
    webapp.py            # FastAPI: /api/status, /api/setup/*
    oauth.py             # consent URL, đổi code, callback Gmail
  bot/
    manager.py           # start/stop/restart bot khi token thay đổi
    handlers.py          # Telegram: /setup /status /language, chat, xác nhận gửi
  agent/
    llm.py               # init_chat_model (OpenAI/DeepSeek/Anthropic/Gemini) + tham số
    tools.py             # search_emails, read_email, request_send_email
    graph.py             # create_react_agent (LangGraph)
frontend/                # React (Vite) control panel + i18n
docker-compose.yml       # app + PostgreSQL
Dockerfile
```

## Bảo mật

- Bot token, API key LLM, client secret Google, refresh token Gmail đều **mã hoá Fernet** trong PostgreSQL.
- Telegram bot giới hạn theo `TELEGRAM_ADMIN_ID`.
- Agent **không thể tự gửi email** — mọi lượt gửi phải bấm xác nhận trong Telegram.
- Scopes Gmail tối thiểu (readonly + send).
- Không cần mở cổng ra Internet.

## Hạn chế đã biết

- Hỗ trợ 4 nhà cung cấp: OpenAI, DeepSeek, Claude (Anthropic), Gemini (Google).
- App Google chưa verify nên consent screen có cảnh báo (không ảnh hưởng hoạt động).
- Không lưu lịch sử hội thoại giữa các lần khởi động.
