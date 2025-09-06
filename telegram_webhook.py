"""
Telegram Bot Webhook Implementation

This module provides a FastAPI-based webhook endpoint for handling Telegram bot updates.
The webhook receives incoming messages and automatically responds to users.

"""

import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Literal, Optional

import httpx
import logfire
from dotenv import load_dotenv


load_dotenv()
from fastapi import BackgroundTasks, FastAPI, Request

from agent import run_receipt_agent, ReceiptInfo


USE_NGROK = os.getenv("USE_NGROK")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


class TelegramBotClient:
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
        """
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.request(
                    method, f"{self.base_url}/{endpoint}", data=data, params=params
                )
                resp.raise_for_status()
                return resp.json().get("result", {})
            except httpx.HTTPStatusError as ex:
                print(f"HTTP error during Telegram API call to {endpoint}: {ex}")
                return None
            except Exception as ex:
                print(
                    f"An unexpected error occurred during Telegram API call to {endpoint}: {ex}"
                )
                return None

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[Literal["MarkdownV2", "HTML", "Markdown"]] = None,
    ):
        """
        Send a message to a specific chat ID.

        Args:
            chat_id (int): The Telegram chat ID to send the message to
            text (str): The message text to send
            parse_mode (Optional[Literal]): The parse mode for the message text.
        """
        data = {"chat_id": chat_id, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode
        return await self._make_request("POST", "sendMessage", data=data)

    async def get_file(self, file_id: str):
        """
        Get information about a file from Telegram.

        Args:
            file_id (str): The file_id of the file to get information about.

        Returns:
            dict: A dictionary containing file information, including 'file_path'.
        """
        params = {"file_id": file_id}
        return await self._make_request("GET", "getFile", params=params)

    async def get_photo_url(self, file_id: str) -> Optional[str]:
        """
        Get the direct download URL for a photo file.

        Args:
            file_id (str): The file_id of the photo to get the URL for.

        Returns:
            Optional[str]: The direct download URL for the photo, or None if failed.
        """
        file_info = await self.get_file(file_id)
        if file_info and "file_path" in file_info:
            return f"{self.file_base_url}/{file_info['file_path']}"
        return None

    async def set_webhook(self, webhook_url: str) -> Optional[dict]:
        """
        Set the webhook URL for the bot.
        
        This is equivalent to the curl command:
        curl -F "url=https://<ngrok_url>/webhook" \
          https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook

        Args:
            webhook_url (str): The webhook URL to set (e.g., "https://abc123.ngrok.io/webhook")

        Returns:
            Optional[dict]: The response from Telegram API, or None if failed.
        """
        data = {"url": webhook_url}
        return await self._make_request("POST", "setWebhook", data=data)

    async def delete_webhook(self, drop_pending_updates=True):
        """
        Remove the webhook URL for the bot.

        This is equivalent to the curl command:
        curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook
        """
        data = {"drop_pending_updates": drop_pending_updates}
        await self._make_request("POST", "deleteWebhook", data=data)

    async def get_webhook_info(self) -> Optional[dict]:
        """
        Get current webhook information.

        This is equivalent to the curl command:
        curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo

        Returns:
            Optional[dict]: The webhook information from Telegram API, or None if failed.
        """
        return await self._make_request("GET", "getWebhookInfo")


# Create Telegram client instance at module level
telegram_client = TelegramBotClient(bot_token=TELEGRAM_BOT_TOKEN)


@asynccontextmanager
async def lifespan(app: FastAPI):
    public_url = None
    if USE_NGROK:
        # open ngrok tunnel
        from pyngrok import ngrok

        # Get the dev server port (defaults to 8000 for Uvicorn, can be overridden with `--port`
        # when starting the server
        port = (
            sys.argv[sys.argv.index("--port") + 1] if "--port" in sys.argv else "8000"
        )
        public_url = ngrok.connect(port).public_url
        print(public_url)
        # set telegram bot webhook
        await telegram_client.set_webhook(f"{public_url}/webhook")
    yield
    if public_url:
        # delete telegram bot webhook
        await telegram_client.delete_webhook()
        # close ngrok tunnel
        ngrok.disconnect(public_url)


app = FastAPI(lifespan=lifespan)


logfire.configure(service_name="telegram-webhook")
logfire.instrument_fastapi(app)
logfire.instrument_pydantic_ai()


def _format_html_receipt_data_for_telegram(receipt_data: ReceiptInfo) -> str:
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
        photo_url = await telegram_client.get_photo_url(photo[-1]["file_id"])
    if photo_url:
        receipt_data = await run_receipt_agent(photo_url, text)
        if receipt_data:
            human_readable_text = _format_html_receipt_data_for_telegram(receipt_data)
            await telegram_client.send_message(
                chat_id=chat_id, text=human_readable_text, parse_mode="HTML"
            )
        else:
            await telegram_client.send_message(
                chat_id=chat_id,
                text="Sorry, I couldn't process the receipt. Please try again later.",
            )


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint that receives Telegram updates.

    This endpoint:
    1. Receives POST requests from Telegram with bot updates
    2. Extracts message information from the update
    3. Sends a response back to the user (processed in the background)

    Args:
        request (Request): FastAPI request object containing the Telegram update

    Returns:
        dict: Confirmation that the webhook was processed
    """
    body = await request.json()
    message = body.get("message", {})
    if message:
        background_tasks.add_task(handle_incoming_message, message)

    return {"ok": True}
