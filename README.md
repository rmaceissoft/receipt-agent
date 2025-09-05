# Receipt Agent

An AI-powered receipt processing system that extracts structured data from receipt images using OpenAI's [GPT-4.1 mini](https://platform.openai.com/docs/models/gpt-4.1-mini) model via the [GitHub Models API](https://docs.github.com/en/github-models). Receipts can be processed through the command line interface or a Telegram bot.

## Quick Start

### Prerequisites
- Python 3.12+
- Github Account with a [personal access token (PAT)](https://github.com/settings/tokens)
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))

### Installation

1. **Clone the repository**
   ```bash
   git clone git@github.com:rmaceissoft/receipt-agent.git
   cd receipt-agent
   ```

2. **Install dependencies**
   ```bash
   uv sync

   # Install dev dependencies (if planning to use ngrok from local environment)
   uv sync --group dev
   ```

3. **Set up environment variables**
   ```bash
   cp .env.copy .env
   # Edit .env with your actual values
   ```

4. **Start telegram webhook server with automatic ngrok setup**
   ```bash
   USE_NGROK=true uvicorn telegram_webhook:app --reload
   ```
   This automatically:
   - Create an ngrok tunnel
   - Sets up the Telegram webhook
   - Clean up when you stop the server 

## Usage

### Option 1: Command Line Interface

Process receipts directly from your computer:

```bash
python main.py path/to/receipt.jpg
```

### Option 2: Telegram Bot

Send receipt photos to your bot


## Key Dependencies
- **[pydantic-ai](https://ai.pydantic.dev/)** - AI agent framework
- **[logfire](https://pydantic.dev/logfire)** - Observability and logging
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern web framework (for telegram webhook)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Made with love for automating receipt processing!**
