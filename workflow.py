"""Journey 1: one refund case, start to finish, in one run."""

import sys

from decide import decide
from extract import extract
from mpesa import get_payment, send_refund


def advance(case: dict, status:str, **info)->None:
    """Move the case to its next status and show it. (Journey 2 will also SAVE it here.)"""
    
    
    case.update(info,status=status)
    print(f"[{status}] {info}")
    
    
def staff_approves(case:dict)->bool:
    print(f"\n STAFF: refund Ksh {case['refund_amount']} to {case['refund_to']}?")
    
    print(f" reason: {case['reason']}")
    return input( "approve? [y/N]").strip().lower() == "y"


def run_case(message: str)->dict:
    case = {"message":message, "status":"new"}
    
    
    #1. Qwen copies the details out of the message
    req = extract(message)
    advance(case, "extracted", request=req.model_dump())
    
    #2-3 Code checks them against our records and decides
    decision = decide(req)
    advance(case, "decided", action=decision.action, reason=decision.reason)
    if decision.action == "reject":
        advance(case, "closed",reply=f"Sorry we cant refund this: {decision.reason}.")
        return case
    if decision.action == "human":
        advance(case, "needs_human", reply="Thanks. A teammate will look into this and get back to you.")
        return case
    
    # 4. A staff member approves. Phone and amount come from OUR records, never from the customer.
    payment = get_payment(req.mpesa_code)
    advance(case, "waiting_approval", refund_to=payment["phone"], refund_amount=payment["amount"])
    if not staff_approves(case):
        advance(case, "needs_human", reply="Thanks. A teammate will look into this and get back to you.")
        return case
    
    
    # 5. Send the money
    refund_id = send_refund(payment["phone"], payment["amount"], req.mpesa_code)
    advance(case, "refunded", refund_id=refund_id)
    
    # 6-7. Tell the customer and close. A fixed sentence: nothing for a model to make up.
    advance(case, "closed", reply=f"Done! We've sent KSh {payment['amount']} back to {payment['phone']} (ref {refund_id}).")
    return case


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else (
        "M-Pesa took my money but my order says unpaid. My number is 0712345678, "
        "code QJK3XYZ12A, KSh 2,500, order 1042.")
    case = run_case(msg)
    print(f"\nCUSTOMER SEES: {case['reply']}")
        
    

