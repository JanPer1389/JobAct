from jobact.shared.infrastructure.config import Settings


def test_default_ai_request_timeout_is_ten_minutes() -> None:
    settings = Settings(_env_file=None)

    assert settings.ai_request_timeout_seconds == 600.0


def test_qwen_uses_dashscope_key_and_international_endpoint_by_default(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-qwen")
    settings = Settings(_env_file=None)

    assert settings.dashscope_api_key == "sk-qwen"
    assert (
        settings.qwen_base_url
        == "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )
