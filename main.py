import argparse
import asyncio
import logging
import sys
from pathlib import Path

import logfire
from dotenv import load_dotenv

load_dotenv()  # take  env variables

from agent import run_receipt_agent, InvalidReceipt


def main():
    parser = argparse.ArgumentParser(
        prog="Receipt Agent",
        description="A tool to extract structured receipt data from receipts",
    )
    parser.add_argument("receipt_path", help="Path to the receipt file")
    args = parser.parse_args()
    receipt_filepath = Path(args.receipt_path)

    # check if the file exists
    if not receipt_filepath.exists():
        sys.exit(1)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logfire.configure(service_name="receipt-agent-cli")
    logfire.instrument_pydantic_ai()
    output = asyncio.run(run_receipt_agent(receipt_path=receipt_filepath))
    if isinstance(output, InvalidReceipt):
        logging.error("The provided image was not recognized as a valid receipt.")
    logging.info(output)


if __name__ == "__main__":
    main()
