from app.core import storage

PROVIDER_KEYS = {"openai", "deepseek", "anthropic", "google_genai"}


def _to_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_model():
    # Import nội bộ để giảm RAM lúc idle (chỉ nạp langchain khi thực sự gọi model).
    from langchain.chat_models import init_chat_model

    settings = storage.get_settings()
    api_key = settings.get("llm_api_key")
    if not api_key:
        return None

    provider = settings.get("llm_provider") or "openai"
    if provider not in PROVIDER_KEYS:
        provider = "openai"
    model = settings.get("llm_model") or ""

    kwargs = {
        "api_key": api_key,
        "temperature": _to_float(settings.get("llm_temperature"), 0.2),
        "timeout": _to_int(settings.get("llm_timeout"), 30),
        "max_tokens": _to_int(settings.get("llm_max_tokens"), 1000),
        "max_retries": _to_int(settings.get("llm_max_retries"), 2),
    }

    return init_chat_model(model=model, model_provider=provider, **kwargs)
