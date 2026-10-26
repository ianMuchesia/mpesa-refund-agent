"""Journey 1: one refund case, start to finish, in one run."""


"""Journey 2: a refund case that survives the program stopping.

Each status has one step. A step does its work, then moves the case to the next status and SAVES it.
After a crash, `resume` reads the saved status and carries on from there.

    python workflow.py new "message"   # start a new case
    python workflow.py resume          # continue every unfinished case
"""

import sys
import os

from decide import decide
from extract import extract
from mpesa import get_payment, send_refund
from store import claim_refund, create_case, record_sent, save_case, unfinished_cases
from models import RefundRequest



def advance(case: dict, status:str, **info)->None:
    """Move the case to its next status and show it. (Journey 2 will also SAVE it here.)"""
    
    
    case.update(info,status=status)
    save_case(case)
    print(f"[{status}] {info}")
    
    
def staff_approves(case:dict)->bool:
    print(f"\n STAFF: refund Ksh {case['refund_amount']} to {case['refund_to']}?")
    
    print(f" reason: {case['reason']}")
    return input( "approve? [y/N]").strip().lower() == "y"



# --- one function per step. Each reads ONLY from the case: after a restart, nothing else exists. ---

def step_extract(case: dict) -> None:
    req = extract(case["message"])
    advance(case, "extracted", request=req.model_dump())
    
    
    
    
def step_decide(case: dict) -> None:
    req = RefundRequest(**case["request"])
    decision = decide(req)
    if decision.action == "reject":
        advance(case, "closed", reason=decision.reason, reply=f"Sorry, we can't refund this: {decision.reason}.")
    elif decision.action == "human":
        advance(case, "needs_human", reason=decision.reason,
                reply="Thanks. A teammate will look into this and get back to you.")
    else:
        # Phone and amount come from OUR records, never from the customer.
        payment = get_payment(req.mpesa_code)
        advance(case, "waiting_approval", reason=decision.reason,
                refund_to=payment["phone"], refund_amount=payment["amount"])
        
        
        
        
def step_approve(case: dict) -> None:
    if staff_approves(case):
        advance(case, "approved")
    else:
        advance(case, "needs_human", reply="Thanks. A teammate will look into this and get back to you.")
        
        
def step_send(case: dict) -> None:
    code = case["request"]["mpesa_code"]
    # Lock 1 (ours): claim the payment in the append-only ledger BEFORE any money moves.
    owner = claim_refund(code, case["id"])
    
    if owner != case["id"]:
        advance(case, "needs_human", reason=f"case {owner} is already refunding {code}",
                reply="Thanks. A teammate will look into this and get back to you.")
        return
    # Lock 2 (Safaricom's): same key every time for this payment, so a retry after a crash can never pay twice.
    refund_id = send_refund(case["refund_to"], case["refund_amount"], idempotency_key=f"refund-{code}")


    
    if os.getenv("CRASH_AFTER_SEND"):  # "break it" switch: die right after the money left
        print("  CRASH! (simulated) after sending, before saving", flush=True)
        os._exit(1)
    record_sent(code, case["id"], refund_id)
    advance(case, "refunded", refund_id=refund_id)


    
    
    
def step_reply(case: dict) -> None:
    advance(case, "closed",
            reply=f"Done! We've sent KSh {case['refund_amount']} back to {case['refund_to']} (ref {case['refund_id']}).")
    
    
    
    

# Which step runs for each status. 'closed' and 'needs_human' have no step: the case is finished.
STEPS = {
    "new": step_extract,
    "extracted": step_decide,
    "waiting_approval": step_approve,
    "approved": step_send,
    "refunded": step_reply,
}


def run(case: dict) -> None:
    while case["status"] in STEPS:
        STEPS[case["status"]](case)
    print(f"  CUSTOMER SEES: {case['reply']}")






if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "new"
    if command == "new":
        msg = sys.argv[2] if len(sys.argv) > 2 else (
            "M-Pesa took my money but my order says unpaid. My number is 0712345678, "
            "code QJK3XYZ12A, KSh 2,500, order 1042.")
        run(create_case(msg))
    elif command == "resume":
        cases = unfinished_cases()
        print(f"{len(cases)} unfinished case(s)")
        for case in cases:
            print(f"\nresuming case {case['id']} from '{case['status']}'")
            run(case)