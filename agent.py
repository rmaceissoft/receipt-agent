from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal, Optional, TypeAlias

from pydantic import BaseModel, Field
from pydantic_ai import Agent, BinaryContent, ImageUrl
from pydantic_ai.exceptions import AgentRunError
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.github import GitHubProvider


class ReceiptInfo(BaseModel):
    """Represents structured data extracted from a valid receipt image."""

    issued_at: datetime = Field(description="Date and time when the receipt was issued")
    vendor_name: Optional[str] = Field(description="Receipt Vendor Name")
    vendor_ruc: Optional[str] = Field(
        description="Receipt Vendor RUC. Ignore for Yape and Plin"
    )
    currency: str = Field(
        description="Currency code of the receipt (e.g., 'PEN' for Peruvian Sol, 'USD' for US Dollar). Use ISO 4217 standard currency codes when possible."
    )
    total_amount: Decimal = Field(
        max_digits=10, decimal_places=2, description="Total Amount"
    )
    tip: Decimal = Field(
        max_digits=5,
        decimal_places=2,
        description="The tip amount. Set to 0 if not present.",
    )
    payment_method: Literal["credit_card", "debit_card", "transfer", "yape", "plin"] = (
        Field(description="Payment method used. Classify IZIPAY as 'credit_card'.")
    )
    note: str = Field(
        description="What the receipt is about. This information is usually provided in the user query. For Yape and Plin receipt, a small description might be present in the receipt itself, but the user query is predominant if provided."
    )
    """
    payment_method_reasoning: str = Field(
        description="A detailed explanation of the reasoning used to determine the payment method from the receipt."
    )
    """


class InvalidReceipt(BaseModel):
    """
    Represents the response when an image is not recognized as a valid receipt.
    This includes cases where:
    - The image is not a receipt at all.
    - The image quality is too poor to extract meaningful data.
    - The image contains a receipt-like document but lacks essentual information.
    """

    pass


# use github models provider
model = OpenAIChatModel(
    "openai/gpt-4.1-mini",
    provider=GitHubProvider(),
    # setting temperature equal to 0 to minimize randomness
    # in order to obtain consistent, predictable, and repeatable outputs
    settings=OpenAIChatModelSettings(temperature=0.0),
)


ReceiptAgentOutput: TypeAlias = ReceiptInfo | InvalidReceipt


receipt_agent = Agent(
    model=model,
    output_type=ReceiptAgentOutput,
    instructions="You are an expert in reading receipts provided as images. Your goal is to extract key fields accurately and return them in strict JSON format",
)


async def run_receipt_agent(
    receipt_path: Path | str, text: Optional[str] = None
) -> ReceiptAgentOutput | None:
    image = (
        ImageUrl(url=receipt_path)
        if isinstance(receipt_path, str)
        else BinaryContent(data=receipt_path.read_bytes(), media_type="image/png")
    )

    user_content = (text, image) if text else (image,)

    try:
        result = await receipt_agent.run(user_content)
    except AgentRunError:
        return None
    return result.output
