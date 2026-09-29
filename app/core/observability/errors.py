class AppError(Exception):
    code = "APP_ERROR"
    public_key = "err_generic"

    def __init__(
        self,
        message: str = "",
        *,
        code: str | None = None,
        public_key: str | None = None,
        **context_data,
    ) -> None:
        super().__init__(message or self.code)
        self.message = message or self.code
        if code:
            self.code = code
        if public_key:
            self.public_key = public_key
        self.context = context_data


class ConfigError(AppError):
    code = "CONFIG_ERROR"
    public_key = "err_config"


class LLMError(AppError):
    code = "LLM_ERROR"
    public_key = "err_llm"


class GmailError(AppError):
    code = "GMAIL_ERROR"
    public_key = "err_gmail"


class OAuthError(AppError):
    code = "OAUTH_ERROR"
    public_key = "err_oauth"


class StorageError(AppError):
    code = "STORAGE_ERROR"
    public_key = "err_storage"


class AgentError(AppError):
    code = "AGENT_ERROR"
    public_key = "err_agent"


class SetupError(AppError):
    code = "SETUP_INCOMPLETE"
    public_key = "err_setup"

    def __init__(self, missing: str, message: str) -> None:
        super().__init__(message, missing=missing)
        self.missing = missing
