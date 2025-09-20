"""
Receipt Agent CLI

This script provides a command-line interface for the Receipt Agent,
allowing users to extract structured data from receipt images.
It processes a given receipt file path, runs an AI agent to extract
information, and prints the result or an error message.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import logfire
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

from agent import InvalidReceipt, ReceiptInfo, ReceiptProcessingError, run_receipt_agent


def main():
    """
    Main function to parse arguments, process the receipt, and display results.

    This function:
    1. Parses the `receipt_path` argument from the command line.
    2. Validates if the provided receipt file exists.
    3. Configures logging and Logfire instrumentation.
    4. Runs the `run_receipt_agent` asynchronously to process the receipt.
    5. Prints the extracted `ReceiptInfo` or an `InvalidReceipt` message.
    6. Exits with status 0 on success or 1 on error.
    """
    parser = argparse.ArgumentParser(
        prog="Receipt Agent",
        description="A tool to extract structured receipt data from receipts",
    )
    parser.add_argument("receipt_path", help="Path to the receipt file")
    args = parser.parse_args()
    receipt_filepath = Path(args.receipt_path)

    # Check if the file exists
    if not receipt_filepath.exists():
        logging.error(f"Error: Receipt file not found at '{receipt_filepath}'")
        sys.exit(1)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logfire.configure(service_name="receipt-agent-cli")
    logfire.instrument_pydantic_ai()
    try:
        receipt_output = asyncio.run(run_receipt_agent(receipt_path=receipt_filepath))
        if isinstance(receipt_output, ReceiptInfo):
            logging.info("Receipt processed successfully:")
            logging.info(receipt_output.model_dump_json(indent=2))
        else:
            logging.info("The provided image was not recognized as a valid receipt.")
        sys.exit(0)
    except ReceiptProcessingError as ex:
        logging.error(f"Error during receipt processing: {ex}")
        sys.exit(1)


if __name__ == "__main__":
    main()
