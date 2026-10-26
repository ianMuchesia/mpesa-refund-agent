"""Step 1: pull the refund details out of a customer message. All code, no model: nothing can be invented.

Anything not found is None. The workflow then asks the customer for it.
"""
import re

from amounts import parse_amount

PHONE_RE = re.compile(r"(?:\+?254|0)[\s-]?[17](?:[\s-]?\d){8}")              # 0712345678, +254 712 345 678
CODE_RE = re.compile(r"\b(?=[A-Z0-9]*[A-Z])(?=[A-Z0-9]*\d)[A-Z0-9]{10}\b")     # 10 chars, letters AND digits
ORDER_RE = re.compile(r"\border\b\D{0,12}?(\d{4})\b", re.IGNORECASE)          # "order 1042", "order no. 1042"


def extract(message: str) -> dict:
    """Returns every detail we could find. Missing ones are None."""
    phone = PHONE_RE.search(message)
    code = CODE_RE.search(message.upper())
    order = ORDER_RE.search(message)
    return {
        "phone": phone.group() if phone else None,
        "mpesa_code": code.group() if code else None,
        "order_id": order.group(1) if order else None,
        "amount": parse_amount(message),
    }


if __name__ == "__main__":
    import sys
    print(extract(sys.argv[1]))
