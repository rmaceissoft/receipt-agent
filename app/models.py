from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from sqlmodel import Field, SQLModel, String


class Receipt(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
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
        Field(
            sa_type=String,
            description="Payment method used. Classify IZIPAY as 'credit_card'.",
        )
    )
    note: str = Field(
        description="What the receipt is about. This information is usually provided in the user query. For Yape and Plin receipt, a small description might be present in the receipt itself, but the user query is predominant if provided."
    )
