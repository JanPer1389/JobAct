from pathlib import Path

import yaml

from jobact.shared.infrastructure.config import Settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = BACKEND_ROOT.parent


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


def test_openrouter_visual_auditor_uses_qwen_vision_model() -> None:
    config = yaml.safe_load((BACKEND_ROOT / "litellm_config.yaml").read_text())
    visual_model = next(
        model
        for model in config["model_list"]
        if model["model_name"] == "visual-auditor"
    )

    assert (
        visual_model["litellm_params"]["model"]
        == "openrouter/qwen/qwen3-vl-32b-instruct"
    )


def test_openrouter_report_drafter_uses_supported_model() -> None:
    config = yaml.safe_load((BACKEND_ROOT / "litellm_config.yaml").read_text())
    drafting_model = next(
        model
        for model in config["model_list"]
        if model["model_name"] == "report-drafter"
    )

    assert drafting_model["litellm_params"]["model"] == "openrouter/openai/gpt-4.1-mini"


def test_root_compose_injects_backend_env_into_litellm() -> None:
    compose = yaml.safe_load((REPOSITORY_ROOT / "docker-compose.yml").read_text())
    litellm = compose["services"]["litellm"]

    assert "./backend/.env" in litellm["env_file"]
    assert "OPENROUTER_API_KEY" not in litellm.get("environment", {})


def test_all_compose_variants_force_httpx_for_litellm() -> None:
    for filename in ("docker-compose.yml", "docker-compose.dokploy.yml"):
        compose = yaml.safe_load((REPOSITORY_ROOT / filename).read_text())

        assert (
            compose["services"]["litellm"]["environment"]["DISABLE_AIOHTTP_TRANSPORT"]
            == "true"
        )
