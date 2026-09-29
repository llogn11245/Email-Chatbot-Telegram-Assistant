from app.core import storage

MESSAGES = {
    "vi": {
        "start": (
            "Chào bạn! Đây là trợ lý Gmail cá nhân.\n\n"
            "Hãy hoàn tất thiết lập 1 lần trên web control panel, sau đó chat tự nhiên "
            "với tôi để: tìm email, tóm tắt hộp thư, soạn & gửi mail.\n\n"
            "Gõ /setup để xem hướng dẫn, /status để kiểm tra kết nối."
        ),
        "setup_title": "Các bước thiết lập:",
        "step_bot": "1. Bot token",
        "step_llm": "2. Cấu hình LLM (API key)",
        "step_gcp": "3. Google OAuth client",
        "step_gmail": "4. Kết nối Gmail",
        "open_panel": "Mở Settings",
        "open_panel_hint": "Mở ứng dụng Chatbot Gmail trên máy tính (cửa sổ Settings) để hoàn tất.",
        "status_title": "Trạng thái:",
        "status_bot": "Bot",
        "status_llm": "LLM",
        "status_oauth": "OAuth client",
        "status_gmail": "Gmail",
        "all_ready": "Tất cả đã sẵn sàng! Chat với tôi để bắt đầu.",
        "not_ready": "Còn bước chưa xong. Mở:",
        "missing_llm": "Bạn chưa cấu hình API key LLM.",
        "missing_gmail": "Bạn chưa kết nối Gmail.",
        "setup_incomplete": "Cấu hình chưa hoàn tất.",
        "ai_error": "Lỗi khi gọi AI:",
        "error_with_ref": "Đã xảy ra lỗi khi xử lý (mã {ref}). Xem tab Nhật ký trong Settings.",
        "sent_ok": "Đã gửi email thành công!",
        "sent_to": "Đã gửi tới",
        "subject": "chủ đề",
        "send_failed": "Gửi thất bại, xem log.",
        "send_failed_detail": "Gửi thất bại:",
        "cancelled": "Đã huỷ, không gửi email.",
        "cancelled_note": "Đã huỷ gửi.",
        "no_permission": "Không có quyền",
        "already_processed": "Yêu cầu này đã được xử lý trước đó.",
        "button_send": "Gửi",
        "button_cancel": "Huỷ",
        "oauth_ok_title": "Kết nối thành công",
        "oauth_fail_title": "Kết nối thất bại",
        "oauth_connected": "Đã kết nối Gmail",
        "oauth_close": "Đóng tab này và quay lại Telegram.",
        "oauth_missing_code": "Không nhận được mã xác nhận từ Google.",
        "oauth_google_error": "Google trả lỗi:",
        "oauth_exchange_error": "Đổi mã lỗi:",
        "oauth_profile_error": "Không lấy được thông tin tài khoản Gmail:",
        "accounts_title": "Tài khoản Gmail đã kết nối:",
        "accounts_none": "Chưa có tài khoản Gmail nào. Mở Settings và bấm 'Add account'.",
        "account_default": "mặc định",
        "back_to_panel": "Quay lại control panel",
        "not_set": "(chưa cấu hình)",
        "not_connected": "(chưa kết nối)",
    },
    "en": {
        "start": (
            "Hi! This is your personal Gmail assistant.\n\n"
            "Complete the one-time setup on the web control panel, then chat naturally "
            "with me to search email, summarize your inbox, draft & send mail.\n\n"
            "Type /setup for instructions, /status to check connections."
        ),
        "setup_title": "Setup steps:",
        "step_bot": "1. Bot token",
        "step_llm": "2. LLM configuration (API key)",
        "step_gcp": "3. Google OAuth client",
        "step_gmail": "4. Connect Gmail",
        "open_panel": "Open Settings",
        "open_panel_hint": "Open the Chatbot Gmail app on your computer (Settings window) to finish.",
        "status_title": "Status:",
        "status_bot": "Bot",
        "status_llm": "LLM",
        "status_oauth": "OAuth client",
        "status_gmail": "Gmail",
        "all_ready": "Everything is ready! Chat with me to get started.",
        "not_ready": "Some steps are incomplete. Open:",
        "missing_llm": "You haven't configured an LLM API key.",
        "missing_gmail": "You haven't connected Gmail.",
        "setup_incomplete": "Setup is not complete.",
        "ai_error": "AI call failed:",
        "error_with_ref": "Something went wrong (ref {ref}). See the Logs tab in Settings.",
        "sent_ok": "Email sent successfully!",
        "sent_to": "Sent to",
        "subject": "subject",
        "send_failed": "Sending failed, check logs.",
        "send_failed_detail": "Sending failed:",
        "cancelled": "Cancelled, email not sent.",
        "cancelled_note": "Cancelled sending.",
        "no_permission": "No permission",
        "already_processed": "This request was already handled.",
        "button_send": "Send",
        "button_cancel": "Cancel",
        "oauth_ok_title": "Connected successfully",
        "oauth_fail_title": "Connection failed",
        "oauth_connected": "Connected Gmail",
        "oauth_close": "Close this tab and return to Telegram.",
        "oauth_missing_code": "No authorization code received from Google.",
        "oauth_google_error": "Google returned an error:",
        "oauth_exchange_error": "Code exchange failed:",
        "oauth_profile_error": "Could not read the Gmail account profile:",
        "accounts_title": "Connected Gmail accounts:",
        "accounts_none": "No Gmail account yet. Open Settings and click 'Add account'.",
        "account_default": "default",
        "back_to_panel": "Back to control panel",
        "not_set": "(not set)",
        "not_connected": "(not connected)",
    },
}


def current_language() -> str:
    try:
        lang = storage.get_settings().get("ui_language") or "vi"
    except Exception:
        lang = "vi"
    return lang if lang in MESSAGES else "vi"


def t(key: str, lang: str | None = None) -> str:
    lang = lang if lang in MESSAGES else current_language()
    return MESSAGES[lang].get(key, key)
