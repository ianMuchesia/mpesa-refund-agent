from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RefundRequest(BaseModel):
    """What the customer told us. Filled by Qwen, checked by Pydantic."""
    phone: str = Field(pattern=r"^0[17]\d{8}$", description="Safaricom number, e.g. 0712345678")

    mpesa_code: str = Field(pattern=r"^[A-Z0-9]{10}$", description="10-character M-Pesa code, e.g. QJK3XYZ12A")
    amount: int = Field(gt=0, description="amount paid in whole Kenya shillings")
    order_id: str = Field(pattern=r"^\d{4}$", description="4-digit order number")
    
    
    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v) -> str:
        """Accept +254712345678, 254712345678 or 0712 345 678; store as 0712345678."""
        digits = "".join(ch for ch in str(v) if ch.isdigit())
        if digits.startswith("254") and len(digits) == 12:
            digits = "0" + digits[3:]
        return digits
    
    
class Decision(BaseModel):
    """What we decided. Made by OUR CODE, never by the model."""
    action: Literal["refund","reject", "human"]
    reason: str
    
    
    





 