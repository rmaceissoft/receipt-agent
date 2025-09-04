# Receipt Agent

An AI-powered receipt processing system that extracts structured data from receipt images using GPT-4.1-mini. Process receipts via command line or chat with our Telegram bot!

## What It Does

This project automatically extracts key information from receipt photos and presents it in a clean, structured format. No more manual data entry!

**Extracted Data:**
- Issue date and time
- Vendor name and tax ID
- Total amount and tip
- Payment method
- Description/notes

## Architecture

The system consists of three main components:

- **AI Agent** (`agent.py`) - Core receipt processing using GPT-4.1-mini
- **CLI Tool** (`main.py`) - Command-line interface for local processing
- **Telegram Bot** (`telegram_webhook.py`) - User-friendly chat interface

## Quick Start

### Prerequisites
- Python 3.12+
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd receipt-agent
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   cp .env.copy .env
   # Edit .env with your actual values
   ```

## Usage

### Option 1: Command Line Interface

Process receipts directly from your computer:

```bash
python main.py path/to/receipt.jpg
```

**Example output:**
```
Receipt Details:
Issued At: December 15, 2024 at 2:30 PM
Issuer Name: Restaurant ABC
Total Amount: 45.50
Tip: 5.00
Payment Method: Credit Card
Note: Dinner for 2 people
```

### Option 2: Telegram Bot

1. **Start the webhook server**
   ```bash
   uvicorn telegram_webhook:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Expose your local server** (using ngrok)
   ```bash  
   ngrok http 8000
   ```

3. **Set the webhook URL**
   ```bash
   curl -F "url=https://<ngrok_url>/webhook" \
     https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
   ```

4. **Start chatting!** Send receipt photos to your bot

## Configuration

Create a `.env` file with:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

## Development

### Project Structure
```
receipt-agent/
├── agent.py              # AI receipt processing logic
├── main.py               # CLI interface
├── telegram_webhook.py   # Telegram bot webhook
├── pyproject.toml        # Project dependencies
└── README.md            # This file
```

### Key Dependencies
- **FastAPI** - Modern web framework for the webhook
- **pydantic-ai** - AI agent framework with GPT-4.1-mini
- **logfire** - Observability and logging
- **python-telegram-bot** - Telegram bot integration

## Features

- **AI-Powered**: Uses GPT-4.1-mini for accurate data extraction
- **Multi-Interface**: Both CLI and Telegram bot interfaces
- **Structured Output**: Consistent, validated data format
- **Payment Method Detection**: Supports credit cards, Yape, Plin, transfers
- **Scalable**: FastAPI backend handles multiple users
- **Detailed Logging**: Comprehensive observability with Logfire

## Troubleshooting

### Common Issues

1. **"Bad Request: can't parse entities"**
   - Switch to HTML parse mode in Telegram bot
   - Or properly escape special characters for MarkdownV2

2. **Webhook not receiving updates**
   - Verify webhook URL is accessible
   - Check bot token is correct
   - Ensure ngrok is running

3. **AI processing fails**
   - Check image quality and format
   - Verify API keys are set correctly
   - Check logs for detailed error messages

### Getting Help

- Check the logs for detailed error information
- Verify all environment variables are set correctly
- Ensure your bot has the necessary permissions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license here]

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [pydantic-ai](https://github.com/jxnl/pydantic-ai)
- AI models provided by [GitHub](https://github.com/features/copilot)

---

**Made with love for automating receipt processing!**
