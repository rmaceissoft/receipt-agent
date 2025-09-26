from typing import Callable
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from telegram_webhook import AppSettings, app, get_app_settings


def _app_settings_factory(**kwargs) -> Callable[[], AppSettings]:
    """
    Factory function to create a callable that returns AppSettings with specific overrides.

    This allows tests to easily create AppSettings instances with different configurations
    without modifying the global dependency override directly.

    Args:
        **kwargs: Keyword arguments to override default AppSettings.

    Returns:
        Callable[[], AppSettings]: A callable that takes no arguments and returns
                                   an AppSettings instance with the specified overrides.
    """
    default_settings = {
        "use_ngrok": False,
        "telegram_bot_token": "token123",
        "telegram_bot_secret_token": "secret123",
        "disable_logfire": True,
    }
    # Merge default settings with any provided kwargs, giving precedence to kwargs
    final_settings = {**default_settings, **kwargs}

    def _get_app_settings_override() -> AppSettings:
        """
        Returns an AppSettings instance based on the settings captured by the factory.
        This is the callable that can be used as a FastAPI dependency override.
        """
        return AppSettings(**final_settings)

    return _get_app_settings_override


@pytest.fixture(scope="function")
def test_client(request):
    """Provides a FastAPI TestClient instance for testing.

    This fixture sets up the FastAPI application with overridden settings for testing
    purposes. It can be parametrized using `pytest.mark.parametrize` to provide
    different `AppSettings` configurations for individual tests.

    Args:
        request: The pytest `request` fixture, used to access parametrization
                 data (e.g., `request.param`) for overriding `AppSettings`.

    Yields:
        TestClient: An instance of `httpx.TestClient` configured with the FastAPI app.
    """
    override_settings = request.param if hasattr(request, "param") else {}
    get_test_app_settings = _app_settings_factory(**override_settings)
    app.dependency_overrides[get_app_settings] = get_test_app_settings
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}


def test_application_reports_healthy_status(test_client):
    resp = test_client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_webhook_when_secret_token_is_configured_but_missing_in_request_then_fails_with_validation_error(
    test_client,
):
    resp = test_client.post("/webhook", json={"message": {"chat": {"id": 1}}})
    assert resp.status_code == 401
    assert resp.json().get("detail") == "X-Telegram-Bot-Api-Secret-Token header missing"


def test_webhook_when_secret_token_is_configured_but_invalid_in_request_then_fails_with_unauthorized_error(
    test_client,
):
    resp = test_client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "WRONG"},
        json={"message": {"chat": {"id": 123}}},
    )
    assert resp.status_code == 401
    assert resp.json().get("detail") == "X-Telegram-Bot-Api-Secret-Token header invalid"


def test_webhook_when_secret_token_is_configured_and_correct_in_request_then_it_responds_ok(
    test_client,
):
    with patch(
        "telegram_webhook.BackgroundTasks.add_task", return_value=None
    ) as mock_add_task:
        test_message = {"chat": {"id": 123}}
        resp = test_client.post(
            "/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "secret123"},
            json={"message": test_message},
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        mock_add_task.assert_called_once()
        assert mock_add_task.call_args[0][1] == test_message


@pytest.mark.parametrize(
    "test_client", [{"telegram_bot_secret_token": None}], indirect=True
)
def test_webhook_when_secret_token_is_not_configured_and_missing_in_request_then_it_responds_ok(
    test_client,
):
    with patch(
        "telegram_webhook.BackgroundTasks.add_task", return_value=None
    ) as mock_add_task:
        test_message = {"chat": {"id": 123}}
        resp = test_client.post("/webhook", json={"message": test_message})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        mock_add_task.assert_called_once()
        assert mock_add_task.call_args[0][1] == test_message
