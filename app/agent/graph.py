import json

from app.core import storage
from app.core.observability.errors import SetupError
from app.core.observability.events import record_event

SYSTEM_PROMPT = (
    "Bạn là trợ lý email cá nhân qua Telegram. User có thể có NHIỀU tài khoản Gmail đã kết nối. "
    "Luôn trả lời bằng tiếng Việt, ngắn gọn.\n"
    "- Dùng list_gmail_accounts để biết các tài khoản và nhãn của chúng.\n"
    "- Khi user hỏi chung chung (vd 'email mới nhất'), tìm ở tài khoản MẶC ĐỊNH; chỉ đổi khi user nói rõ.\n"
    "- Khi đọc lại email, truyền đúng 'account' mà search_emails đã trả về.\n"
    "- Khi user muốn gửi email: tự soạn nội dung, nhưng nếu user KHÔNG nói rõ gửi từ tài khoản nào và có "
    "nhiều tài khoản thì PHẢI hỏi user chọn tài khoản trước, rồi mới gọi request_send_email kèm account. "
    "Email chỉ được gửi sau khi user bấm nút xác nhận trong Telegram.\n"
    "- Đừng bịa message_id: chỉ dùng id do tool search_emails trả về."
)


def _missing_setup_message(missing: str) -> str:
    guide = {
        "llm": "Bạn chưa cấu hình API key LLM.",
        "gmail": "Bạn chưa kết nối Gmail.",
    }
    head = guide.get(missing, "Cấu hình chưa hoàn tất.")
    return f"{head} Mở ứng dụng Chatbot Gmail (Settings) để hoàn tất. Hoặc gõ /setup."


def run_agent(user_text: str):
    # Import nội bộ (lazy) để idle không tốn RAM cho langchain/langgraph.
    from langchain_core.messages import AIMessage

    from app.agent.llm import build_model
    from app.agent.pipeline.builder import build_agent, build_context_messages

    settings = storage.get_settings()
    if not settings.get("llm_api_key"):
        raise SetupError("llm", _missing_setup_message("llm"))
    if storage.count_gmail_accounts() == 0:
        raise SetupError("gmail", _missing_setup_message("gmail"))

    model = build_model()
    if model is None:
        raise SetupError("llm", _missing_setup_message("llm"))

    agent = build_agent(model, SYSTEM_PROMPT)
    messages = build_context_messages(settings, user_text)
    messages.append(("user", user_text))
    try:
        response = agent.invoke({"messages": messages})
    except Exception as exc:
        record_event("ERROR", "agent", f"run_agent lỗi: {exc}", exc=exc)
        raise

    pending_id = None
    final_text = ""
    tool_names: list[str] = []
    for message in response["messages"]:
        if isinstance(message, AIMessage):
            if message.tool_calls:
                for call in message.tool_calls:
                    tool_names.append(call["name"])
                    if call["name"] == "request_send_email":
                        args = call.get("args", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except ValueError:
                                args = {}
                        pending_id = args.get("pending_id")
            if message.content:
                final_text = str(message.content)

    record_event(
        "INFO",
        "agent",
        "run xong",
        tools=",".join(tool_names) or "-",
        pending=pending_id,
    )
    return final_text, pending_id
