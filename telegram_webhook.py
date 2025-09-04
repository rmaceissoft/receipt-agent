"""
Telegram Bot Webhook Implementation

This module provides a FastAPI-based webhook endpoint for handling Telegram bot updates.
The webhook receives incoming messages and automatically responds to users.

SETUP INSTRUCTIONS:
==================

1. Environment Variables:
   Create a .env file with your bot token:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

2. Start the FastAPI server:
   ```bash
   uvicorn telegram_webhook:app --reload --host 0.0.0.0 --port 8000
   ```

3. Expose your local server to the internet using ngrok:
   ```bash
   ngrok http 8000
   ```

4. Set the webhook URL using the curl command below:
   Replace <ngrok_url> with your actual ngrok URL and <YOUR_BOT_TOKEN> with your bot token.

   ```bash
   curl -F "url=https://<ngrok_url>/webhook" \
     https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
   ```

   Example:
   ```bash
   curl -F "url=https://abc123.ngrok.io/webhook" \
     https://api.telegram.org/bot1234567890:ABCdefGHIjklMNOpqrsTUVwxyz/setWebhook
   ```

5. Verify webhook is set:
   ```bash
   curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
   ```

6. Test your bot by sending a message in Telegram!

For more information on the `setWebhook` API method, visit: https://core.telegram.org/bots/api#setwebhook
"""

import os
from typing import Literal, Optional

import httpx
import logfire
from dotenv import load_dotenv


load_dotenv()
from fastapi import FastAPI, Request

from agent import run_receipt_agent, ReceiptInfo


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TELEGRAM_FILE_BASE_URL = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}"


app = FastAPI()


logfire.configure(service_name="telegram-webhook")
logfire.instrument_fastapi(app)
logfire.instrument_pydantic_ai()


async def send_message(
    chat_id: int,
    text: str,
    parse_mode: Optional[Literal["MarkdownV2", "HTML", "Markdown"]] = None,
):
    """
    Send a message to a specific chat ID.

    Args:
        chat_id (int): The Telegram chat ID to send the message to
        text (str): The message text to send
    """
    async with httpx.AsyncClient() as client:
        try:
            data = {"chat_id": chat_id, "text": text}
            if parse_mode:
                data["parse_mode"] = parse_mode
            resp = await client.post(
                f"{TELEGRAM_BASE_URL}/sendMessage",
                data=data,
            )
            resp.raise_for_status()
            return resp.json().get("result", {})
        except httpx.HTTPStatusError as ex:
            print(ex)


async def get_file(file_id: str):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{TELEGRAM_BASE_URL}/getFile", params={"file_id": file_id}
            )
            resp.raise_for_status()
            return resp.json().get("result", {})
        except httpx.HTTPStatusError as ex:
            print(ex)


def _format_html_receipt_data_for_telegram(receipt_data: ReceiptInfo) -> str:
    payment_method_display = receipt_data.payment_method.replace("_", " ").title()
    _html = f"""
    🧾 <b>Receipt Details:</b>    
    📅 <b>Issued At:</b> {receipt_data.issued_at.strftime("%B %d, %Y at %I:%M %p")}
    🏢 <b>Vendor Name:</b> {receipt_data.vendor_name}
    🆔 <b>Vendor RUC:</b> {receipt_data.vendor_ruc}
    💰 <b>Total Amount:</b> {receipt_data.total_amount:.2f}
    💸 <b>Tip:</b> {receipt_data.tip:.2f}
    💳 <b>Payment Method:</b> {payment_method_display}
    📝 <b>Note:</b> {receipt_data.note}
    """
    return _html


@app.post("/webhook")
async def webhook(request: Request):
    """
    Webhook endpoint that receives Telegram updates.

    This endpoint:
    1. Receives POST requests from Telegram with bot updates
    2. Extracts message information from the update
    3. Sends a response back to the user

    Args:
        request (Request): FastAPI request object containing the Telegram update

    Returns:
        dict: Confirmation that the webhook was processed
    """
    body = await request.json()
    message = body.get("message", {})
    if message:
        chat_id = message["chat"]["id"]

        text = message.get("text") or message.get("caption")

        photo, photo_url = message.get("photo"), None
        if photo:
            file_info = await get_file(photo[-1]["file_id"])
            photo_url = f"{TELEGRAM_FILE_BASE_URL}/{file_info['file_path']}"
        if photo_url:
            receipt_data = await run_receipt_agent(photo_url, text)
            if receipt_data:
                human_readable_text = _format_html_receipt_data_for_telegram(
                    receipt_data
                )
                await send_message(
                    chat_id=chat_id, text=human_readable_text, parse_mode="HTML"
                )
            else:
                await send_message(
                    chat_id=chat_id,
                    text="Sorry, I couldn't process the receipt. Please try again later.",
                )

    return {"ok": True}
