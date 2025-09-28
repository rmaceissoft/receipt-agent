from app.agent import ReceiptInfo
from app.db import db_session
from app.models import Receipt


def save_receipt_into_db(receipt: ReceiptInfo) -> Receipt:
    """Saves extracted receipt information into the database.

    This function takes a `ReceiptInfo` object, maps its fields to the `Receipt`
    SQLModel, and persists it to the database.

    Args:
        receipt (ReceiptInfo): An instance of `ReceiptInfo` containing the
            structured data extracted from a receipt.

    Returns:
        Receipt: The `Receipt` object as it was saved in the database,
            including any database-generated fields.
    """
    with db_session() as session:
        receipt_at_db = Receipt(
            issued_at=receipt.issued_at,
            vendor_name=receipt.vendor_name,
            vendor_ruc=receipt.vendor_ruc,
            currency=receipt.currency,
            total_amount=receipt.total_amount,
            tip=receipt.tip,
            payment_method=receipt.payment_method,
            note=receipt.note,
        )
        session.add(receipt_at_db)
        session.commit()
        session.refresh(receipt_at_db)
        return receipt_at_db
