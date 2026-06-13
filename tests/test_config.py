"""Tests for configuration loading and environment overrides."""

from __future__ import annotations

import json

from jarvis.brain.router import ProviderRouter
from jarvis.config import Config


def test_defaults_present_without_file(tmp_path):
    cfg = Config.load(base_dir=tmp_path)  # no config.json or example here
    assert cfg.get("language") == "en"
    assert cfg.section("safety")["confirm_medium_risk"] is True
    assert "logging" in cfg.data


def test_env_overrides_language_and_wake(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_LANGUAGE", "ru")
    monkeypatch.setenv("JARVIS_WAKE_WORD", "friday")
    cfg = Config.load(base_dir=tmp_path)
    assert cfg.get("language") == "ru"
    assert cfg.get("wake_word") == "friday"


def test_env_api_key_reaches_provider(monkeypatch, tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "llm": {
                    "providers": [
                        {"type": "anthropic", "name": "claude", "model": "c", "api_key": ""},
                        {"type": "openai", "name": "openai", "model": "m", "api_key": ""},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("JARVIS_API_KEY", "sk-from-env")
    cfg = Config.load(base_dir=tmp_path)
    router = ProviderRouter.from_config(cfg.section("llm"))
    openai = next(p for p in router.providers if p.name == "openai")
    assert openai.api_key == "sk-from-env"
    assert openai.available is True


def test_deep_merge_preserves_unset_defaults(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"language": "de"}), encoding="utf-8")
    cfg = Config.load(base_dir=tmp_path)
    assert cfg.get("language") == "de"
    # A nested default the user didn't override should still be present.
    assert cfg.section("voice")["rate"] == 175
