import json

from langchain_core.tools import tool

from app.core import storage
from app.core.observability import record_event
from app.email import gmail_client


def _dumps(data) -> str:
    return json.dumps(data, ensure_ascii=False)


def _primary_query(query: str) -> str:
    """Mặc định chỉ tìm trong hộp thư chính (Primary), trừ khi user chỉ định rõ."""
    q = (query or "").strip()
    low = q.lower()
    if any(token in low for token in ("category:", "label:", "in:")):
        return q
    return f"category:primary {q}".strip()


def _resolve_account(account):
    accounts = storage.list_gmail_accounts()
    if not accounts:
        return None, accounts
    if account is None or str(account).strip() == "":
        for item in accounts:
            if item["is_default"]:
                return item, accounts
        return accounts[0], accounts
    key = str(account).strip().lower()
    for item in accounts:
        identifiers = {
            str(item["id"]).lower(),
            (item["email"] or "").lower(),
            (item["label"] or "").lower(),
        }
        if key in identifiers:
            return item, accounts
    return None, accounts


@tool
def list_gmail_accounts() -> str:
    """
    Liệt kê các tài khoản Gmail đã kết nối (id, email, nhãn, tài khoản mặc định).
    """
    return _dumps(storage.list_gmail_accounts())


@tool
def search_emails(query: str, max_results: int = 10, account: str | None = None) -> str:
    """
    Tìm email bằng cú pháp Gmail search (vd: 'from:x@gmail.com', 'is:unread', 'subject:invoice').
    Mặc định CHỈ tìm trong hộp thư chính (Primary) để tránh nhiễu từ Updates/Social/Promotions.
    Muốn tìm nơi khác, user phải nói rõ (vd 'in:anywhere', 'category:social').
    account = nhãn/email/id tài khoản Gmail; để trống sẽ dùng tài khoản mặc định.
    """
    acct, _ = _resolve_account(account)
    if acct is None:
        return "LỖI: chưa có tài khoản Gmail nào được kết nối."
    try:
        results = gmail_client.search_emails(
            _primary_query(query), max_results, account_id=acct["id"]
        )
    except gmail_client.GmailError as e:
        return f"LỖI: {e}"
    return _dumps(results)


@tool
def read_email(message_id: str, account: str | None = None) -> str:
    """
    Đọc toàn bộ nội dung một email theo message_id (lấy từ search_emails).
    account = tài khoản chứa email đó (nên truyền đúng tài khoản đã tìm ra email).
    """
    acct, _ = _resolve_account(account)
    if acct is None:
        return "LỖI: chưa có tài khoản Gmail nào được kết nối."
    try:
        result = gmail_client.read_email(message_id, account_id=acct["id"])
    except gmail_client.GmailError as e:
        return f"LỖI: {e}"
    return _dumps(result)


@tool
def request_send_email(to: str, subject: str, body: str, account: str | None = None) -> str:
    """
    Chuẩn bị gửi email (lưu dự thảo, KHÔNG gửi ngay). User sẽ bấm xác nhận trong Telegram.
    to = địa chỉ người nhận. account = nhãn/email tài khoản gửi.
    Quan trọng: nếu user KHÔNG nói rõ gửi từ tài khoản nào và có nhiều tài khoản, ĐỪNG gọi tool này —
    hãy hỏi user chọn tài khoản trước.
    """
    if not (to and subject and body):
        return "LỖI: cần đủ to, subject, body."
    acct, accounts = _resolve_account(account)
    if acct is None:
        labels = ", ".join((a["label"] or a["email"]) for a in accounts) or "(trống)"
        return (
            "CẦN HỎI USER: có nhiều tài khoản Gmail ("
            f"{labels}). Hãy hỏi user muốn gửi từ tài khoản nào, "
            "rồi gọi lại request_send_email kèm tham số account."
        )
    draft_id = ""
    try:
        draft_id = gmail_client.create_draft(to, subject, body, account_id=acct["id"])
    except Exception as exc:
        # Có thể do tài khoản chưa cấp scope gmail.compose; vẫn cho xác nhận gửi trực tiếp.
        record_event("WARNING", "agent", f"create_draft lỗi (bỏ qua draft): {exc}")

    pending_id = storage.create_pending_send(
        to, subject, body, account_id=acct["id"], draft_id=draft_id
    )
    return _dumps(
        {
            "pending_id": pending_id,
            "from_account": acct["label"] or acct["email"],
            "draft_created": bool(draft_id),
            "message": "Đã lưu dự thảo. Hãy báo user bấm nút xác nhận trong Telegram để gửi.",
        }
    )


TOOLS = [list_gmail_accounts, search_emails, read_email, request_send_email]


def get_tools():
    """Danh sách tools cho agent."""
    return list(TOOLS)