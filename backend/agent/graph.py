import json

from langchain_core.messages import AIMessage
from langgraph.prebuilt import create_react_agent

from backend.agent.llm import build_model
from backend.agent.tools import TOOLS
from backend import storage

SYSTEM_PROMPT = (
    "Bạn là trợ lý email cá nhân qua Telegram. Bạn có thể đọc và tìm email của user. "
    "Luôn trả lời bằng tiếng Việt, ngắn gọn. Khi user muốn gửi email, hãy tự soạn nội dung rồi "
    "dùng tool request_send_email — email sẽ chỉ được gửi sau khi user bấm xác nhận. "
    "Đừng bịa message_id: chỉ dùng id do tool search_emails trả về."
)


class SetupError(Exception):
    def __init__(self, missing: str, message: str) -> None:
        super().__init__(message)
        self.missing = missing
        self.message = message


def _missing_setup_message(missing: str) -> str:
    guide = {
        "llm": "Bạn chưa cấu hình API key LLM.",
        "gmail": "Bạn chưa kết nối Gmail.",
    }
    head = guide.get(missing, "Cấu hình chưa hoàn tất.")
    return (
        f"{head} Mở control panel để hoàn tất setup: http://localhost:8000\n"
        f"Hoặc gõ /setup để xem hướng dẫn."
    )


def run_agent(user_text: str):
    settings = storage.get_settings()
    if not settings.get("llm_api_key"):
        raise SetupError("llm", _missing_setup_message("llm"))
    if not settings.get("gmail_refresh_token"):
        raise SetupError("gmail", _missing_setup_message("gmail"))

    model = build_model()
    if model is None:
        raise SetupError("llm", _missing_setup_message("llm"))

    agent = create_react_agent(model, TOOLS, prompt=SYSTEM_PROMPT)
    response = agent.invoke({"messages": [("user", user_text)]})

    pending_id = None
    final_text = ""
    for message in response["messages"]:
        if isinstance(message, AIMessage):
            if message.tool_calls:
                for call in message.tool_calls:
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

    return final_text, pending_id
