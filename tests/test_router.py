"""Tests for the multi-provider AI router and provider selection."""

from __future__ import annotations

from jarvis.brain.providers import build_provider
from jarvis.brain.providers.base import BaseProvider, ProviderError
from jarvis.brain.router import ProviderRouter, RouteRequirements, TaskType


class _StubProvider(BaseProvider):
    """In-memory provider for tests: replies or fails on demand."""

    def __init__(self, name, *, fail=False, reply="ok", **kw):
        super().__init__(name=name, model="stub-model", api_key="key", **kw)
        self._fail = fail
        self._reply = reply

    def _complete(self, messages, *, system, temperature, max_tokens):
        if self._fail:
            raise ProviderError(f"{self.name} failed")
        return f"{self._reply}:{self.name}"


def _cfg(**kw):
    base = {"type": "openai", "model": "m", "api_key": "k"}
    base.update(kw)
    return base


def test_build_provider_unknown_type_returns_none():
    assert build_provider({"type": "nonsense"}) is None
    assert build_provider({"type": "openai", "enabled": False, "model": "m"}) is None


def test_local_provider_available_without_key():
    provider = build_provider({"type": "local", "model": "llama", "base_url": "http://x"})
    assert provider is not None
    assert provider.available is True
    assert provider.capabilities.local is True


def test_cloud_provider_unavailable_without_key():
    provider = build_provider({"type": "openai", "model": "gpt", "api_key": ""})
    assert provider.available is False


def test_router_orders_by_capability_for_coding():
    weak = _StubProvider("weak")
    weak.capabilities.coding = 2
    strong = _StubProvider("strong")
    strong.capabilities.coding = 5
    router = ProviderRouter([weak, strong])
    order = router.candidates(RouteRequirements(task=TaskType.CODING))
    assert [p.name for p in order] == ["strong", "weak"]


def test_router_privacy_filters_to_local_only():
    cloud = _StubProvider("cloud")
    local = _StubProvider("local")
    local.capabilities.local = True
    router = ProviderRouter([cloud, local])
    order = router.candidates(RouteRequirements(private=True))
    assert [p.name for p in order] == ["local"]


def test_router_language_filter():
    en_only = _StubProvider("en-only")
    en_only.capabilities.languages = {"en"}
    multi = _StubProvider("multi")
    router = ProviderRouter([en_only, multi])
    order = router.candidates(RouteRequirements(language="ru"))
    assert [p.name for p in order] == ["multi"]


def test_router_falls_back_on_failure():
    failer = _StubProvider("failer", fail=True, priority=1)
    good = _StubProvider("good", reply="hi", priority=2)
    router = ProviderRouter([failer, good])
    result = router.complete([{"role": "user", "content": "hi"}])
    assert result is not None
    assert result.provider == "good"


def test_router_returns_none_when_all_fail():
    a = _StubProvider("a", fail=True)
    b = _StubProvider("b", fail=True)
    router = ProviderRouter([a, b])
    assert router.complete([{"role": "user", "content": "x"}]) is None


def test_router_returns_none_when_no_provider():
    router = ProviderRouter([])
    assert router.complete([{"role": "user", "content": "x"}]) is None


def test_from_config_legacy_flat_shape():
    router = ProviderRouter.from_config(
        {"model": "gpt-4o-mini", "api_key": "k", "base_url": "https://api.openai.com/v1"}
    )
    assert len(router.providers) == 1
    assert router.providers[0].name == "openai"


def test_from_config_new_providers_list():
    router = ProviderRouter.from_config(
        {
            "providers": [
                _cfg(type="anthropic", name="claude", api_key="k"),
                _cfg(type="local", name="ollama", api_key=""),
            ]
        }
    )
    names = {p.name for p in router.providers}
    assert names == {"claude", "ollama"}
