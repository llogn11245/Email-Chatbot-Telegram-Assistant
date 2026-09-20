from langchain.chat_models import init_chat_model

from backend import storage


def build_model():
    settings = storage.get_settings()
    api_key = settings.get("llm_api_key")
    if not api_key:
        return None
    model = settings.get("llm_model")
    model_provider = settings.get("llm_provider")
    # base_url = settings.get("llm_base_url") or None
    kwargs = {
        "api_key": api_key,
        "temperature": 0.2,
        "timeout": 30,
        "max_tokens": 1000,
        "max_retries": 6,
    }
    # if base_url:
    #     kwargs["base_url"] = base_url

    llm = init_chat_model(
        model=model,
        provider=model_provider,
        **kwargs,
    )
    return llm
