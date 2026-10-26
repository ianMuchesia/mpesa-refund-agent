"""Fake M-Pesa + shop records. This is the truth that every customer claim is checked against."""

# Money that arrived through M-Pesa, keyed by the M-Pesa code (unique per payment).
# "account" is what the customer typed as the account number when paying: it should be their order number.
PAYMENTS = {
    "QJK3XYZ12A": {"phone": "0712345678", "amount": 2500, "account": "1042"},  # paid, but order still unpaid
    "QJK4ABC34B": {"phone": "0722000111", "amount": 1800, "account": "1043"},  # paid, order IS paid
    "QJK5DEF56C": {"phone": "0733222333", "amount": 4000, "account": "9999"},  # typo in the account number
}


ORDERS = {
    "1042": {"amount": 2500, "status": "unpaid"},
    "1043": {"amount": 1800, "status": "paid"},
    "1044": {"amount": 4000, "status": "unpaid"},
}

REFUNDS: list[dict] = []  # every refund we've sent


def get_payment(mpesa_code:str) -> dict | None:
    return PAYMENTS.get(mpesa_code)


def get_order(order_id: str) -> dict | None:
    return ORDERS.get(order_id)


def send_refund(phone:str, amount: int, mpesa_code:str) -> str:
    """Pretend to send money back. The ONLY function that moves money."""
    # Idempotent: one refund per M-Pesa payment. Asking again returns the first refund, no new money.
    for r in REFUNDS:
        if r["mpesa_code"] == mpesa_code:
            print(f"  already refunded {mpesa_code} as {r['refund_id']}, NOT sending again")
            return r["refund_id"]
    refund_id = f"RF{len(REFUNDS) + 1:04d}"
    REFUNDS.append({
        "refund_id":refund_id,
        "phone": phone,
        "amount":amount,
        "mpesa_code":mpesa_code
    })
    print(f"  >>> SENT KSh {amount} to {phone} (refund {refund_id})")
    return refund_id


