from app.core import storage

PROVIDER_KEYS = {"openai", "deepseek", "anthropic", "google_genai"}

# Client HTTP dùng chung, chỉ nhận gzip/deflate để tránh lỗi giải mã brotli của httpx2.
_http_client = None


def _get_http_client():
    global _http_client
    if _http_client is None:
        try:
            import httpx2

            _http_client = httpx2.Client(headers={"Accept-Encoding": "gzip, deflate"})
        except Exception:
            _http_client = False
    return _http_client or None


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

    # OpenAI/DeepSeek đi qua openai SDK (httpx2); tránh brotli để không dính lỗi decode.
    if provider in ("openai", "deepseek"):
        client = _get_http_client()
        if client is not None:
            kwargs["http_client"] = client

    return init_chat_model(model=model, model_provider=provider, **kwargs)
