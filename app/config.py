from functools import lru_cache
from typing import Any, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Application settings for the Telegram webhook.

    Attributes:
        use_ngrok (bool): Whether to use ngrok for local development. Defaults to False.
        on_render (bool): Indicates if the application is running on Render.com.
            Defaults to False, aliased from "render" environment variable.
        render_external_url (Optional[str]): The external URL provided by Render.com
            when deployed. Required if `on_render` is True.
        telegram_bot_token (str): The secret token for the Telegram bot API.
        telegram_bot_secret_token (Optional[str]): An optional secret token for
            webhook validation, used to secure the webhook.
        disable_logfire (bool): Whether to disable Logfire instrumentation. Defaults to False.
        database_url (str): The URL for the database connection.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )

    use_ngrok: bool = False
    on_render: bool = Field(alias="render", default=False)
    render_external_url: Optional[str] = None
    telegram_bot_token: str
    telegram_bot_secret_token: Optional[str] = None
    disable_logfire: bool = False
    database_url: str
    database_options: Optional[dict[str, Any]] = None


@lru_cache
def get_app_settings() -> AppSettings:
    """Retrieves the application settings.

    This function is cached to ensure that `AppSettings` are loaded only once
    from environment variables.

    Returns:
        AppSettings: An instance of the application settings.
    """
    return AppSettings()
