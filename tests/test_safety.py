"""Tests for the safety / permission pipeline and structured logging."""

from __future__ import annotations

import json

import pytest

from jarvis.core.logging_setup import EventLogger
from jarvis.core.safety import (
    Decision,
    RiskLevel,
    SafetyManager,
    SafetyRequest,
)


@pytest.fixture
def logger(tmp_path):
    return EventLogger(log_path=tmp_path / "events.log")


def req(category="app_control", risk=RiskLevel.MEDIUM, reversible=True, action="do thing"):
    return SafetyRequest(agent="test", action=action, category=category, risk=risk, reversible=reversible)


def test_low_risk_is_allowed(logger):
    mgr = SafetyManager(logger=logger)
    verdict = mgr.evaluate(req(category="web", risk=RiskLevel.LOW))
    assert verdict.decision is Decision.ALLOW


def test_blocked_category_is_denied(logger):
    mgr = SafetyManager(blocked={"shell"}, logger=logger)
    verdict = mgr.evaluate(req(category="shell", risk=RiskLevel.HIGH))
    assert verdict.decision is Decision.DENY


def test_medium_risk_requires_confirmation_by_default(logger):
    mgr = SafetyManager(logger=logger)
    verdict = mgr.evaluate(req(category="system_settings", risk=RiskLevel.MEDIUM))
    assert verdict.decision is Decision.CONFIRM


def test_pre_authorized_category_skips_confirmation(logger):
    mgr = SafetyManager(granted={"app_control"}, logger=logger)
    verdict = mgr.evaluate(req(category="app_control", risk=RiskLevel.MEDIUM))
    assert verdict.decision is Decision.ALLOW


def test_high_risk_always_confirms_even_if_granted(logger):
    mgr = SafetyManager(granted={"file_write"}, logger=logger)
    verdict = mgr.evaluate(req(category="file_write", risk=RiskLevel.HIGH))
    assert verdict.decision is Decision.CONFIRM


def test_irreversible_always_confirms(logger):
    mgr = SafetyManager(granted={"file_write"}, logger=logger)
    verdict = mgr.evaluate(
        req(category="file_write", risk=RiskLevel.MEDIUM, reversible=False)
    )
    assert verdict.decision is Decision.CONFIRM


def test_gate_returns_allow_when_user_confirms(logger):
    mgr = SafetyManager(logger=logger)
    decision = mgr.gate(req(category="system_settings"), confirm=lambda r: True)
    assert decision is Decision.ALLOW


def test_gate_returns_confirm_when_user_declines(logger):
    mgr = SafetyManager(logger=logger)
    decision = mgr.gate(req(category="system_settings"), confirm=lambda r: False)
    assert decision is Decision.CONFIRM  # declined != policy DENY


def test_gate_without_callback_declines(logger):
    mgr = SafetyManager(logger=logger)
    assert mgr.authorize(req(category="system_settings")) is False


def test_auto_confirm_mode(logger):
    mgr = SafetyManager(auto_confirm=True, logger=logger)
    assert mgr.authorize(req(category="system_settings")) is True


def test_confirm_medium_disabled_allows(logger):
    mgr = SafetyManager(confirm_medium=False, logger=logger)
    verdict = mgr.evaluate(req(category="system_settings", risk=RiskLevel.MEDIUM))
    assert verdict.decision is Decision.ALLOW


def test_from_config():
    mgr = SafetyManager.from_config(
        {"granted_permissions": ["WEB"], "blocked_permissions": ["Shell"]}
    )
    assert "web" in mgr.granted
    assert "shell" in mgr.blocked


# -- logging -----------------------------------------------------------
def test_logger_writes_jsonl(tmp_path):
    path = tmp_path / "events.log"
    log = EventLogger(log_path=path)
    log.info(agent="x", action="do", result="ok", foo="bar")
    log.error(agent="y", action="boom", error="kaboom")
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["agent"] == "x" and first["detail"]["foo"] == "bar"
    assert "timestamp" in first


def test_logger_scrubs_secrets(tmp_path):
    path = tmp_path / "events.log"
    log = EventLogger(log_path=path)
    log.info(agent="x", action="auth", api_key="sk-secret", token="abc")
    event = json.loads(path.read_text(encoding="utf-8").strip())
    assert event["detail"]["api_key"] == "***redacted***"
    assert event["detail"]["token"] == "***redacted***"


def test_logger_never_raises_on_bad_path(tmp_path):
    # A directory path is not writable as a file; logger must degrade, not raise.
    log = EventLogger(log_path=tmp_path)  # tmp_path is a directory
    log.info(agent="x", action="do")  # should not raise
