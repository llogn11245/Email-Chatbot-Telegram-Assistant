import json

from langchain_core.tools import tool

from backend import gmail_client, storage


def _dumps(data) -> str:
    return json.dumps(data, ensure_ascii=False)


@tool
def search_emails(query: str, max_results: int = 10) -> str:
    """Tìm email trong Gmail của user bằng cú pháp Gmail search (vd: 'from:x@gmail.com', 'is:unread', 'subject:invoice'). Trả về danh sách id, người gửi, tiêu đề và đoạn trích."""
    try:
        results = gmail_client.search_emails(query, max_results)
    except gmail_client.GmailError as e:
        return f"LỖI: {e}"
    return _dumps(results)


@tool
def read_email(message_id: str) -> str:
    """Đọc toàn bộ nội dung một email theo message_id (lấy từ search_emails)."""
    try:
        result = gmail_client.read_email(message_id)
    except gmail_client.GmailError as e:
        return f"LỖI: {e}"
    return _dumps(result)


@tool
def request_send_email(to: str, subject: str, body: str) -> str:
    """Chuẩn bị gửi email. Chỉ lưu lại dự thảo và YÊU CẦU user xác nhận trong Telegram, KHÔNG gửi ngay. to phải là địa chỉ email hợp lệ."""
    if not (to and subject and body):
        return "LỖI: cần đủ to, subject, body."
    pending_id = storage.create_pending_send(to, subject, body)
    return _dumps(
        {
            "pending_id": pending_id,
            "message": "Email đã sẵn sàng. Hãy báo cho user rằng họ cần bấm nút xác nhận trong Telegram để gửi.",
        }
    )


TOOLS = [search_emails, read_email, request_send_email]
