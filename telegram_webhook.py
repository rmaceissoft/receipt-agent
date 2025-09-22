"""
Telegram Bot Webhook Implementation

This module provides a FastAPI-based webhook endpoint for handling Telegram bot updates.
The webhook receives incoming messages and automatically responds to users.

"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal, Optional

import httpx
import logfire
from dotenv import load_dotenv


load_dotenv()
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request

from agent import InvalidReceipt, run_receipt_agent, ReceiptInfo, ReceiptProcessingError


USE_NGROK = os.getenv("USE_NGROK")
USE_RENDER = os.getenv("RENDER")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_SECRET_TOKEN = os.getenv("TELEGRAM_BOT_SECRET_TOKEN")

# Configure logging
logger = logging.getLogger(__name__)


class TelegramBotAPIError(Exception):
    """Base exception for Telegram Bot API related errors."""

    pass


class TelegramBotClient:
    """Client for interacting with the Telegram Bot API.

    This class provides methods to send messages, retrieve file information,
    and manage webhooks for a Telegram bot.

    Attributes:
        _bot_token (str): The Telegram bot token.
        base_url (str): The base URL for Telegram Bot API requests.
        file_base_url (str): The base URL for downloading Telegram files.
    """

    def __init__(self, bot_token: str):
        self._bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{self._bot_token}"
        self.file_base_url = f"https://api.telegram.org/file/bot{self._bot_token}"

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
    ):
        """
        Helper to make HTTP requests to the Telegram API, handling client lifecycle and errors.

        Args:
            method (str): The HTTP method (e.g., "GET", "POST").
            endpoint (str): The API endpoint to call (e.g., "sendMessage").
            params (Optional[dict]): Dictionary of query parameters.
            data (Optional[dict]): Dictionary of form data or JSON payload.

        Returns:
            dict: The JSON result from the Telegram API response.

        Raises:
            TelegramBotAPIError: If an HTTP error occurs during the request.
        """
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.request(
                    method, f"{self.base_url}/{endpoint}", data=data, params=params
                )
                resp.raise_for_status()
                return resp.json().get("result", {})
            except httpx.HTTPError as ex:
                raise TelegramBotAPIError(f"HTTP Exception for {ex.request.url}: {ex}")

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[Literal["MarkdownV2", "HTML", "Markdown"]] = None,
    ):
        """
        Send a message to a specific chat ID.

        Args:
            chat_id (int): The Telegram chat ID to send the message to.
            text (str): The message text to send.
            parse_mode (Optional[Literal]): The parse mode for the message text.
                Can be "MarkdownV2", "HTML", or "Markdown".

        Returns:
            dict: The response from the Telegram API.
        """
        data = {"chat_id": chat_id, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode
        return await self._make_request("POST", "sendMessage", data=data)

    async def get_file(self, file_id: str) -> dict[str, Any]:
        """
        Get information about a file from Telegram.

        Args:
            file_id (str): The file_id of the file to get information about.

        Returns:
            dict[str, Any]: A dictionary containing file information, including 'file_path'.
        """
        params = {"file_id": file_id}
        return await self._make_request("GET", "getFile", params=params)

    async def get_photo_url(self, file_id: str) -> Optional[str]:
        """
        Get the direct download URL for a photo file.

        Args:
            file_id (str): The file_id of the photo to get the URL for.

        Returns:
            Optional[str]: The direct download URL for the photo.
        """
        file_info = await self.get_file(file_id)
        if file_info and "file_path" in file_info:
            return f"{self.file_base_url}/{file_info['file_path']}"
        return None

    async def set_webhook(
        self, webhook_url: str, secret_token: Optional[str] = None
    ) -> None:
        """
        Set the webhook URL for the bot.
        
        This is equivalent to the curl command:
        curl -F "url=https://<ngrok_url>/webhook" \
          https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook

        Args:
            webhook_url (str): The webhook URL to set (e.g., "https://abc123.ngrok.io/webhook").
            secret_token (Optional[str]): A secret token to be sent with every webhook request.
                If set, Telegram will send an X-Telegram-Bot-Api-Secret-Token header.
        """
        data = {"url": webhook_url}
        if secret_token:
            data["secret_token"] = secret_token
        await self._make_request("POST", "setWebhook", data=data)

    async def delete_webhook(self, drop_pending_updates=True) -> None:
        """
        Remove the webhook URL for the bot.

        This is equivalent to the curl command:
        curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook

        Args:
            drop_pending_updates (bool): If True, pending updates will be dropped.
                Defaults to True.
        """
        data = {"drop_pending_updates": drop_pending_updates}
        await self._make_request("POST", "deleteWebhook", data=data)

    async def get_webhook_info(self) -> dict[str, Any]:
        """
        Get current webhook information.

        This is equivalent to the curl command:
        curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo

        Returns:
            dict[str, Any]: The webhook information from Telegram API.
        """
        return await self._make_request("GET", "getWebhookInfo")


# Create Telegram client instance at module level
telegram_client = TelegramBotClient(bot_token=TELEGRAM_BOT_TOKEN)


def _get_public_url() -> tuple[str | None, bool]:
    """
    Get the public URL for the service and whether it needs cleanup.

    Returns:
        tuple: (public_url, needs_cleanup)
    """
    _public_url = None
    _needs_ngrok_cleanup = False

    # Check if running on Render.com
    if USE_RENDER:
        _public_url = os.getenv("RENDER_EXTERNAL_URL")
        logger.info(f"Using Render URL: {_public_url}")
    elif USE_NGROK:
        # open ngrok tunnel
        from pyngrok import ngrok
        from pyngrok.exception import PyngrokError

        # Get the dev server port (defaults to 8000 for Uvicorn, can be overridden with `--port`
        # when starting the server
        port = (
            sys.argv[sys.argv.index("--port") + 1] if "--port" in sys.argv else "8000"
        )
        try:
            # Establish tunnel
            _public_url = ngrok.connect(port).public_url
            _needs_ngrok_cleanup = True
            logger.info(f"Ngrok tunnel established: {_public_url}")
        except PyngrokError as ex:
            logger.error(f"Failed to setup ngrok: {ex}")

    return _public_url, _needs_ngrok_cleanup


def _cleanup_ngrok(public_url: str) -> None:
    """Safely disconnect ngrok tunnel."""
    try:
        from pyngrok import ngrok
        from pyngrok.exception import PyngrokError

        ngrok.disconnect(public_url)
        logger.info("Ngrok tunnel disconnected")
    except PyngrokError:
        pass  # Suppress cleanup errors


async def _setup_webhook(public_url: str) -> bool:
    """Set up Telegram webhook."""
    try:
        webhook_url = f"{public_url}/webhook"
        await telegram_client.set_webhook(
            webhook_url, secret_token=TELEGRAM_BOT_SECRET_TOKEN
        )
        logger.info(f"Telegram webhook set to: {webhook_url}")
        return True
    except TelegramBotAPIError as ex:
        logger.error(f"Failed to setup telegram webhook: {ex}")
        return False


async def _cleanup_webhook() -> None:
    """Remove Telegram webhook."""
    try:
        await telegram_client.delete_webhook()
        logger.info("Telegram webhook deleted")
    except TelegramBotAPIError as ex:
        logger.error(f"Failed to delete telegram webhook: {ex}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for managing ngrok tunnel and Telegram webhook.

    This context manager handles the setup and teardown of an ngrok tunnel
    and the Telegram bot webhook. If USE_NGROK is enabled, it establishes
    a tunnel, sets the webhook, and cleans them up on exit.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None
    """
    public_url, needs_ngrok_cleanup = _get_public_url()
    if public_url:
        # set telegram bot webhook
        is_webhook_setup_successful = await _setup_webhook(public_url)
        if not is_webhook_setup_successful and needs_ngrok_cleanup:
            _cleanup_ngrok(public_url)
            public_url = None
    yield
    if public_url:
        await _cleanup_webhook()
        if needs_ngrok_cleanup:
            _cleanup_ngrok(public_url)


app = FastAPI(lifespan=lifespan)


logfire.configure(service_name="telegram-webhook", send_to_logfire="if-token-present")
logfire.instrument_fastapi(app)
logfire.instrument_pydantic_ai()


def _format_html_receipt_data_for_telegram(receipt_data: ReceiptInfo) -> str:
    """
    Formats extracted receipt data into an HTML string suitable for Telegram messages.

    Args:
        receipt_data (ReceiptInfo): An instance of ReceiptInfo containing the
            structured data extracted from a receipt.

    Returns:
        str: An HTML formatted string with receipt details.
    """
    payment_method_display = receipt_data.payment_method.replace("_", " ").title()
    _html = f"""
    🧾 <b>Receipt Details:</b>    
    📅 <b>Issued At:</b> {receipt_data.issued_at.strftime("%B %d, %Y at %I:%M %p")}
    🏢 <b>Vendor Name:</b> {receipt_data.vendor_name}
    🆔 <b>Vendor RUC:</b> {receipt_data.vendor_ruc}
    🪙 <b>Currency:</b> {receipt_data.currency}
    💰 <b>Total Amount:</b> {receipt_data.total_amount:.2f}
    💸 <b>Tip:</b> {receipt_data.tip:.2f}
    💳 <b>Payment Method:</b> {payment_method_display}
    📝 <b>Note:</b> {receipt_data.note}
    """
    return _html


async def handle_incoming_message(message: dict[str, Any]) -> None:
    """
    Process incoming Telegram message containing receipt photos

    The function specifically looks for photos in messages and uses the highest
    resolution version available. If a photo is found, it runs the receipt
    processing agent and send formatted results back to the user via Telegram.

    Args:
        message (dict[str, Any]): Telegram message object

    Returns:
        None: This function performs side effects (sending messages)
    """
    chat_id = message["chat"]["id"]

    text = message.get("text") or message.get("caption")

    photo, photo_url = message.get("photo"), None
    if photo:
        try:
            photo_url = await telegram_client.get_photo_url(photo[-1]["file_id"])
        except TelegramBotAPIError as ex:
            logger.error(f"Telegram Error getting the photo url: {ex}")
    if photo_url:
        text, parse_mode = None, None
        try:
            receipt_output = await run_receipt_agent(photo_url, text)
            if isinstance(receipt_output, ReceiptInfo):
                text = _format_html_receipt_data_for_telegram(receipt_output)
                parse_mode = "HTML"
            elif isinstance(receipt_output, InvalidReceipt):
                text = "The provided image was not recognized as a valid receipt."
        except ReceiptProcessingError as ex:
            text = "Sorry, I couldn't process the receipt. Please try again later."

        # send telegram message back to user
        try:
            await telegram_client.send_message(
                chat_id=chat_id, text=text, parse_mode=parse_mode
            )
        except TelegramBotAPIError as ex:
            logger.error(f"Telegram Error sending message: {ex}")


async def require_valid_api_secret_token(
    x_telegram_bot_api_secret_token: Annotated[str, Header()],
):
    """Validates the X-Telegram-Bot-Api-Secret-Token header.

    This function checks if the provided secret token matches the expected
    environment variable `TELEGRAM_BOT_SECRET_TOKEN`. If they do not match,
    it raises an HTTPException with a 401 status code.

    Args:
        x_telegram_bot_api_secret_token (str): The secret token provided in the
            'X-Telegram-Bot-Api-Secret-Token' header of the incoming request.

    Raises:
        HTTPException: If the provided token does not match the expected secret.

    Returns:
        str: The validated secret token if it is valid.
    """
    if x_telegram_bot_api_secret_token != TELEGRAM_BOT_SECRET_TOKEN:
        raise HTTPException(
            status_code=401, detail="X-Telegram-Bot-Api-Secret-Token header invalid"
        )
    return x_telegram_bot_api_secret_token


@app.post("/webhook", dependencies=[Depends(require_valid_api_secret_token)])
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint that receives Telegram updates.

    This endpoint:
    1. Receives POST requests from Telegram with bot updates
    2. Extracts message information from the update
    3. Sends a response back to the user (processed in the background)

    Args:
        request (Request): FastAPI request object containing the Telegram update.
        background_tasks (BackgroundTasks): FastAPI dependency for running tasks in the background.

    Returns:
        dict: Confirmation that the webhook was processed.
    """
    body = await request.json()
    message = body.get("message", {})
    if message:
        background_tasks.add_task(handle_incoming_message, message)

    return {"ok": True}


@app.get("/healthz")
async def health_check():
    """Health check endpoint to verify service is running."""
    return {"status": "healthy"}
