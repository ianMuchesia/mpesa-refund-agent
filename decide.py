"""Compare what the customer claims with our records. Plain rules, no model."""


from models import Decision, RefundRequest
from mpesa import REFUNDS, get_order, get_payment


def decide(req: RefundRequest)->Decision:
    # 1. Does the payment exist at all?
    payment = get_payment(req.mpesa_code)
    
    if payment is None:
        return Decision(action="reject", reason=f"no M-Pesa payment found with code {req.mpesa_code}")
    
    # 2. Already refunded?
    if any(r["mpesa_code"] == req.mpesa_code for r in REFUNDS):
        return Decision(action="reject", reason=f"payment {req.mpesa_code} was already refunded")
    
    
    # 3. Does what the customer says match the payment? If not, a human looks.
    if payment["phone"] != req.phone:
        return Decision(action="human", reason="the payment was made from a different phone number")
    if payment["amount"] != req.amount:
        return Decision(action="human", reason=f"customer says KSh {req.amount}, records say KSh {payment['amount']}")
    if payment["account"] != req.order_id:
        return Decision(action="human", reason=f"payment went to account {payment['account']}, not order {req.order_id}")
    
    
    # 4. Is the order really unpaid?
    order = get_order(req.order_id)
    if order is None:
        return Decision(action="human", reason=f"order {req.order_id} does not exist")
    if order["status"] == "paid":
        return Decision(action="reject", reason=f"order {req.order_id} is already paid, nothing to refund")
    
    
    
    # Every check passed: the records prove it.
    return Decision(action="refund", reason=f"KSh {payment['amount']} received as {req.mpesa_code}, but order {req.order_id} is unpaid")


if __name__ == "__main__":
    tests = [
        RefundRequest(phone="0712345678", mpesa_code="QJK3XYZ12A", amount=2500, order_id="1042"),
        RefundRequest(phone="0722000111", mpesa_code="QJK4ABC34B", amount=1800, order_id="1043"),
        RefundRequest(phone="0733222333", mpesa_code="QJK5DEF56C", amount=4000, order_id="1044"),
        RefundRequest(phone="0712345678", mpesa_code="QJK3XYZ12A", amount=50000, order_id="1042"),
        RefundRequest(phone="0712345678", mpesa_code="ZZZ9999999", amount=2500, order_id="1042"),
    ]
    for t in tests:
        d = decide(t)
        print(f"{t.mpesa_code}  KSh {t.amount:>6}  ->  {d.action:<6}  {d.reason}")
    
    

