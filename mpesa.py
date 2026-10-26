"""Fake M-Pesa + shop records. This is the truth that every customer claim is checked against."""

import sqlite3

# Money that arrived through M-Pesa, keyed by the M-Pesa code (unique per payment).
# "account" is what the customer typed as the account number when paying: it should be their order number.

SAFARICOM_DB = "safaricom.db"


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


def _safaricom()-> sqlite3.Connection:
    conn = sqlite3.connect(SAFARICOM_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payouts (
            idempotency_key TEXT PRIMARY KEY,
            refund_id       TEXT NOT NULL,
            phone           TEXT NOT NULL,
            amount          INTEGER NOT NULL
        )""")
    return conn
    


def send_refund(phone:str, amount: int, idempotency_key:str) -> str:
    """Pretend to send money back. The ONLY function that moves money."""
    # Idempotent: one refund per M-Pesa payment. Asking again returns the first refund, no new money.
    #    Like real payment APIs: the same idempotency key returns the first payout instead of paying again."""
    
    with _safaricom() as conn:
        row = conn.execute("SELECT refund_id FROM payouts WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
        if row:
            print(f"  safaricom: {idempotency_key} was already paid as {row[0]}, NOT sending again")
            return row[0]
        refund_id = f"RF{conn.execute('SELECT COUNT(*) FROM payouts').fetchone()[0] + 1:04d}"
        conn.execute("INSERT INTO payouts VALUES (?, ?, ?, ?)", (idempotency_key, refund_id, phone, amount))
    print(f"  >>> SENT KSh {amount} to {phone} (refund {refund_id})")
    return refund_id

    
 


