from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from telegram_webhook import AppSettings, app, get_app_settings


def get_test_app_settings() -> AppSettings:
    """
    FastAPI dependency override that provides a mock `AppSettings` instance for tests.
    """
    return AppSettings(
        use_ngrok=False,
        telegram_bot_token="token123",
        telegram_bot_secret_token="secret123",
        disable_logfire=True,
    )


@pytest.fixture(scope="function")
def test_client():
    app.dependency_overrides[get_app_settings] = get_test_app_settings
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}


def test_application_reports_healthy_status(test_client):
    resp = test_client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_webhook_when_no_secret_token_then_request_fails_with_validation_error(
    test_client,
):
    resp = test_client.post("/webhook", json={"message": {"chat": {"id": 1}}})
    assert resp.status_code == 422


def test_webhook_when_invalid_secret_token_then_request_fails_with_unauthorized_error(
    test_client,
):
    resp = test_client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "WRONG"},
        json={"message": {"chat": {"id": 123}}},
    )
    assert resp.status_code == 401
    assert resp.json().get("detail") == "X-Telegram-Bot-Api-Secret-Token header invalid"


def test_webhook_when_correct_secret_token_then_it_responds_ok(test_client):
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
