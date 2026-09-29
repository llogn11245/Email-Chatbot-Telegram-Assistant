from app.core import storage
from app.core.observability.errors import SetupError
from app.core.observability.events import record_event

SYSTEM_PROMPT = (
    "Bạn là trợ lý email cá nhân qua Telegram. User có thể có NHIỀU tài khoản Gmail đã kết nối. "
    "Hãy trả lời bằng ngôn ngữ mà bạn được hỏi. Bạn có trí nhớ ngắn hạn trong cuộc trò chuyện.\n"
    "- Dùng list_gmail_accounts để biết các tài khoản và nhãn của chúng.\n"
    "- Khi tìm email, mặc định chỉ tìm trong hộp thư chính (Primary). Nếu user muốn tìm ở nơi khác "
    "(quảng cáo, mạng xã hội, cập nhật, mọi nơi...) hãy nói rõ trong query (vd 'in:anywhere' hoặc 'category:social').\n"
    "- Khi user hỏi chung chung (vd 'email mới nhất'), tìm ở tài khoản MẶC ĐỊNH; chỉ đổi khi user nói rõ.\n"
    "- Khi đọc lại email, truyền đúng 'account' mà search_emails đã trả về.\n"
    "- Khi user muốn gửi email: tự soạn nội dung, nhưng nếu user KHÔNG nói rõ gửi từ tài khoản nào và có "
    "nhiều tài khoản thì PHẢI hỏi user chọn tài khoản trước, rồi mới gọi request_send_email kèm account. "
    "Email chỉ được gửi sau khi user bấm nút xác nhận trong Telegram.\n"
    "- Đừng bịa message_id: chỉ dùng id do tool search_emails trả về.\n"
    "- Khi trả lời user, đừng sử dụng markdown hay code block, chỉ trả về text thuần."
)


_memory = None


def _get_memory():
    global _memory
    if _memory is None:
        try:
            from langgraph.checkpoint.memory import InMemorySaver

            _memory = InMemorySaver()
        except Exception:
            from langgraph.checkpoint.memory import MemorySaver

            _memory = MemorySaver()
    return _memory


def reset_memory(conversation_id: str) -> None:
    """Xoá trí nhớ ngắn hạn của một hội thoại."""
    memory = _get_memory()
    func = getattr(memory, "delete_thread", None)
    if callable(func):
        try:
            func(conversation_id)
        except Exception:
            pass


def _missing_setup_message(missing: str) -> str:
    guide = {
        "llm": "Bạn chưa cấu hình API key LLM.",
        "gmail": "Bạn chưa kết nối Gmail.",
    }
    head = guide.get(missing, "Cấu hình chưa hoàn tất.")
    return f"{head} Mở ứng dụng Chatbot Gmail (Settings) để hoàn tất. Hoặc gõ /setup."


def run_agent(user_text: str, conversation_id: str | None = None):
    # Import nội bộ (lazy) để idle không tốn RAM cho langchain/langgraph.
    from langchain_core.messages import AIMessage

    from app.agent.llm import build_model

    settings = storage.get_settings()
    if not settings.get("llm_api_key"):
        raise SetupError("llm", _missing_setup_message("llm"))
    if storage.count_gmail_accounts() == 0:
        raise SetupError("gmail", _missing_setup_message("gmail"))

    model = build_model()
    if model is None:
        raise SetupError("llm", _missing_setup_message("llm"))

    from langgraph.prebuilt import create_react_agent

    from app.agent.tools import get_tools

    agent = create_react_agent(
        model, get_tools(), prompt=SYSTEM_PROMPT, checkpointer=_get_memory()
    )
    before = storage.latest_pending_id()
    messages = [("user", user_text)]
    config = {"configurable": {"thread_id": conversation_id or "default"}}
    try:
        response = agent.invoke({"messages": messages}, config=config)
    except Exception as exc:
        record_event("ERROR", "agent", f"run_agent lỗi: {exc}", exc=exc)
        raise

    final_text = ""
    for message in response["messages"]:
        if isinstance(message, AIMessage) and message.content:
            final_text = str(message.content)

    after = storage.latest_pending_id()
    pending_id = after if after > before else None

    record_event("INFO", "agent", "run xong", pending=pending_id)
    return final_text, pending_id
