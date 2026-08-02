import importlib
import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import simulator.server


@pytest.fixture(autouse=True)
def _reset_umami_env() -> Iterator[None]:
    """Ensure no UMAMI_* env leakage between tests or from the host shell."""
    for key in ("UMAMI_DOMAIN", "UMAMI_ID"):
        os.environ.pop(key, None)
    importlib.reload(simulator.server)
    yield
    for key in ("UMAMI_DOMAIN", "UMAMI_ID"):
        os.environ.pop(key, None)
    importlib.reload(simulator.server)


VALID_DOMAIN = "https://analytics.example.com"
VALID_ID = "123e4567-e89b-42d3-a456-426614174000"


def test_umami_config_unset_is_inert() -> None:
    assert simulator.server._umami_config() == ("", "")


def test_umami_config_domain_only_is_inert(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UMAMI_DOMAIN", VALID_DOMAIN)
    assert simulator.server._umami_config() == ("", "")


def test_umami_config_http_scheme_is_inert(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UMAMI_DOMAIN", "http://analytics.example.com")
    monkeypatch.setenv("UMAMI_ID", VALID_ID)
    assert simulator.server._umami_config() == ("", "")


def test_umami_config_whitespace_in_domain_is_inert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UMAMI_DOMAIN", "https://analytics example.com")
    monkeypatch.setenv("UMAMI_ID", VALID_ID)
    assert simulator.server._umami_config() == ("", "")


def test_umami_config_non_uuid_id_is_inert(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UMAMI_DOMAIN", VALID_DOMAIN)
    monkeypatch.setenv("UMAMI_ID", "not-a-uuid")
    assert simulator.server._umami_config() == ("", "")


def test_umami_config_valid_strips_trailing_slash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UMAMI_DOMAIN", "https://analytics.example.com/")
    monkeypatch.setenv("UMAMI_ID", VALID_ID)
    assert simulator.server._umami_config() == (VALID_DOMAIN, VALID_ID)


def test_umami_config_semicolon_in_domain_is_inert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UMAMI_DOMAIN", "https://analytics.example;connect-src")
    monkeypatch.setenv("UMAMI_ID", VALID_ID)
    assert simulator.server._umami_config() == ("", "")


def test_umami_config_path_in_domain_is_inert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UMAMI_DOMAIN", "https://analytics.example.com/analytics")
    monkeypatch.setenv("UMAMI_ID", VALID_ID)
    assert simulator.server._umami_config() == ("", "")


def test_umami_config_userinfo_in_domain_is_inert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UMAMI_DOMAIN", "https://user:@analytics.example.com")
    monkeypatch.setenv("UMAMI_ID", VALID_ID)
    assert simulator.server._umami_config() == ("", "")


def test_default_serve_is_inert() -> None:
    client = TestClient(simulator.server.app)
    response = client.get("/")
    assert response.status_code == 200
    assert 'data-website-id="' not in response.text
    csp = response.headers.get("content-security-policy", "")
    assert VALID_DOMAIN not in csp


def test_umami_tag_injected_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UMAMI_DOMAIN", VALID_DOMAIN)
    monkeypatch.setenv("UMAMI_ID", VALID_ID)
    module = importlib.reload(simulator.server)
    client = TestClient(module.app)

    response = client.get("/")
    assert response.status_code == 200
    expected_tag = (
        '<script defer src="https://analytics.example.com/script.js" '
        'data-website-id="123e4567-e89b-42d3-a456-426614174000"></script></body>'
    )
    assert expected_tag in response.text
    assert "etag" not in response.headers
    csp = response.headers.get("content-security-policy", "")
    assert f"{VALID_DOMAIN}" in csp
    # The origin must appear in both directives the tag uses.
    assert f"script-src 'self' https://cdn.plot.ly {VALID_DOMAIN}" in csp
    assert f"connect-src 'self' {VALID_DOMAIN}" in csp


def test_health_endpoint_untouched_when_umami_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UMAMI_DOMAIN", VALID_DOMAIN)
    monkeypatch.setenv("UMAMI_ID", VALID_ID)
    module = importlib.reload(simulator.server)
    client = TestClient(module.app)

    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert 'data-website-id="' not in response.text


def test_head_request_passes_through_without_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UMAMI_DOMAIN", VALID_DOMAIN)
    monkeypatch.setenv("UMAMI_ID", VALID_ID)
    module = importlib.reload(simulator.server)
    client = TestClient(module.app)

    response = client.head("/")
    assert response.status_code == 200
    assert response.content == b""


def test_malformed_env_is_inert(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UMAMI_DOMAIN", "http://analytics.example.com")
    monkeypatch.setenv("UMAMI_ID", "not-a-uuid")
    module = importlib.reload(simulator.server)
    client = TestClient(module.app)

    response = client.get("/")
    assert response.status_code == 200
    assert 'data-website-id="' not in response.text


def test_non_200_html_response_is_not_injected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UMAMI_DOMAIN", VALID_DOMAIN)
    monkeypatch.setenv("UMAMI_ID", VALID_ID)
    module = importlib.reload(simulator.server)
    client = TestClient(module.app)

    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert 'data-website-id="' not in response.text
