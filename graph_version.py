"""The approval part of workflow.py, rebuilt with LangGraph, to see what a framework does for us.

Same rules (decide.py), same money locks (store.py ledger + Safaricom idempotency key).
LangGraph replaces: the STEPS table, advance()/save_case(), resume, waiting_approval + staff_decision(), MAX_STEPS.

    python graph_version.py new <case_id> "message"     # runs until it pauses for staff
    python graph_version.py approve <case_id> <name>    # resumes the paused graph
    python graph_version.py reject <case_id> <name>
    python graph_version.py resume <case_id>            # after a crash: carry on from the last checkpoint
"""


import os
import sqlite3
import sys
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from decide import decide
from extract import extract
from models import RefundRequest
from mpesa import get_payment, send_refund
from store import claim_refund, record_sent


class Case(TypedDict, total=False):  # the state: what our `case` dict was
    case_id: int
    message: str
    request: dict
    action: str
    reason: str
    refund_to: str
    refund_amount: int
    approved_by: str
    refund_id: str
    reply: str
    
    
# --- nodes: the same work as our steps, but they RETURN changes instead of calling advance() ---

def extract_node(case: Case) -> dict:
    details = extract(case["message"])
    if None in details.values():
        return {"action": "human", "reason": "missing details (Journey 5 not rebuilt here)"}
    return {"request": RefundRequest(**details).model_dump()}


def decide_node(case: Case) -> dict:
    req = RefundRequest(**case["request"])
    decision = decide(req)
    update = {"action": decision.action, "reason": decision.reason}
    if decision.action == "refund":
        payment = get_payment(req.mpesa_code)
        update |= {"refund_to": payment["phone"], "refund_amount": payment["amount"]}
    return update




def approval_node(case: Case) -> dict:
    print(f"  approval_node: asking staff about KSh {case['refund_amount']} to {case['refund_to']}")
    # interrupt() saves everything and STOPS the program. Resuming re-runs this node from the top,
    # and this time interrupt() returns what staff sent.
    answer = interrupt({"refund_to": case["refund_to"], "amount": case["refund_amount"]})
    if answer["approve"]:
        return {"approved_by": answer["staff"]}
    return {"action": "human", "reason": f"rejected by {answer['staff']}"}




def send_node(case: Case) -> dict:
    code = case["request"]["mpesa_code"]
    owner = claim_refund(code, case["case_id"])  # our ledger lock: LangGraph doesn't give you this
    if owner != case["case_id"]:
        return {"action": "human", "reason": f"case {owner} is already refunding {code}"}
    refund_id = send_refund(case["refund_to"], case["refund_amount"], idempotency_key=f"refund-{code}")
    if os.getenv("CRASH_AFTER_SEND"):
        print("  CRASH! (simulated) after sending, before saving", flush=True)
        os._exit(1)
    record_sent(code, case["case_id"], refund_id)
    return {"refund_id": refund_id, "reply": f"Done! KSh {case['refund_amount']} sent (ref {refund_id})."}



# --- edges: our STEPS table, written as a graph ---

def after_extract(case: Case) -> str:
    nxt = "decide" if case.get("request") else END
    print(f"  ARROW after extract -> {nxt}")
    return nxt


def after_decide(case: Case) -> str:
    nxt = "approval" if case["action"] == "refund" else END
    print(f"  ARROW after decide (action={case['action']}) -> {nxt}")
    return nxt

def after_approval(case: Case) -> str:
    nxt = "send" if case.get("approved_by") else END
    print(f"  ARROW after approval (approved_by={case.get('approved_by')}) -> {nxt}")
    return nxt



builder = StateGraph(Case)
builder.add_node("extract", extract_node)
builder.add_node("decide", decide_node)
builder.add_node("approval", approval_node)
builder.add_node("send", send_node)
builder.add_edge(START, "extract")
builder.add_conditional_edges("extract", after_extract)
builder.add_conditional_edges("decide", after_decide)
builder.add_conditional_edges("approval", after_approval)
builder.add_edge("send", END)


def run(graph, graph_input, config) -> None:
    """Like graph.invoke, but prints what each node returned. After each line, LangGraph saved a checkpoint."""
    for event in graph.stream(graph_input, config, stream_mode="updates"):
        for node, update in event.items():
            if node == "__interrupt__":
                print(f"  PAUSE: interrupt() asked {update[0].value}")
            else:
                print(f"  NODE {node} returned {update}   (saved)")


def show(graph, config) -> None:
    snap = graph.get_state(config)
    if snap.next:
        print(f"  PAUSED before/at: {snap.next}  (saved in graph.db, the program can stop now)")
    else:
        print(f"  FINISHED: action={snap.values.get('action')} reason={snap.values.get('reason')}"
              f" refund_id={snap.values.get('refund_id')}")
        
        
        
if __name__ == "__main__":
    command, case_id = sys.argv[1], int(sys.argv[2])
    # The checkpointer saves the state after every node: our advance()/save_case(), for free.
    saver = SqliteSaver(sqlite3.connect("graph.db", check_same_thread=False))
    graph = builder.compile(checkpointer=saver)
    # thread_id = which case. recursion_limit = our MAX_STEPS.
    config = {"configurable": {"thread_id": str(case_id)}, "recursion_limit": 10}

    if command == "new":
        run(graph, {"case_id": case_id, "message": sys.argv[3]}, config)
    elif command in ("approve", "reject"):
        if not graph.get_state(config).next:
            print(f"case {case_id} is not waiting for anything. Nothing done.")
            sys.exit()
        run(graph, Command(resume={"approve": command == "approve", "staff": sys.argv[3]}), config)
    elif command == "resume":
        run(graph, None, config)  # None = "carry on from the last checkpoint"
    show(graph, config)

