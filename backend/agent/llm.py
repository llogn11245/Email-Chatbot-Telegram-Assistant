from langchain_openai import ChatOpenAI

from backend import storage


def build_model():
    settings = storage.get_settings()
    api_key = settings.get("llm_api_key")
    if not api_key:
        return None
    model = settings.get("llm_model") or "gpt-4o-mini"
    base_url = settings.get("llm_base_url") or None
    kwargs = {
        "model": model,
        "api_key": api_key,
        "temperature": 0.2,
    }
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)
