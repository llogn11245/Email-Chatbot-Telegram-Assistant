import os

# Tắt telemetry/tracing (privacy + tránh gọi mạng khi không cần).
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGCHAIN_TRACING_ENABLED", "false")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
