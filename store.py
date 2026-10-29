"""Saves every case in SQLite, so a case survives the program stopping."""


import json
import sqlite3
from datetime import datetime


DB_PATH = "cases.db"

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            status     TEXT NOT NULL,
            data       TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
    
    # The money ledger. APPEND-ONLY: rows are added, never updated or deleted.
    # UNIQUE(mpesa_code, event): at most one 'claimed' and one 'sent' per payment, ever.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS refund_events (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            mpesa_code TEXT NOT NULL,
            case_id    INTEGER NOT NULL,
            event      TEXT NOT NULL CHECK (event IN ('claimed', 'sent')),
            refund_id  TEXT,
            at         TEXT NOT NULL,
            UNIQUE (mpesa_code, event)
        )""")

    return conn


def create_case(message: str) -> dict:
    case = {"message": message, "status": "new"}
    with _connect() as conn:
        cur = conn.execute("INSERT INTO cases (status, data, updated_at) VALUES (?, ?, ?)",
                           ("new", json.dumps(case), datetime.now().isoformat(timespec="seconds")))
        case["id"] = cur.lastrowid
    save_case(case)  # save again so the stored data includes its own id
    return case



def save_case(case: dict) -> None:
    with _connect() as conn:
        conn.execute("UPDATE cases SET status = ?, data = ?, updated_at = ? WHERE id = ?",
                     (case["status"], json.dumps(case), datetime.now().isoformat(timespec="seconds"), case["id"]))
        
        
        
def load_case(case_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT data FROM cases WHERE id = ?", (case_id,)).fetchone()
    return json.loads(row[0]) if row else None



def unfinished_cases() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
                       # waiting_approval is not "unfinished work": it's parked until a staff member acts.
                        "SELECT data FROM cases WHERE status NOT IN ('closed', 'needs_human', 'waiting_approval', 'waiting_customer','stuck') ORDER BY id").fetchall()


    return [json.loads(r[0]) for r in rows]




def cases_with_status(status: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT data FROM cases WHERE status = ? ORDER BY id", (status,)).fetchall()
    return [json.loads(r[0]) for r in rows]









def _append_event(conn: sqlite3.Connection, mpesa_code: str, case_id: int, event: str, refund_id: str | None = None) -> None:
    conn.execute("INSERT OR IGNORE INTO refund_events (mpesa_code, case_id, event, refund_id, at) VALUES (?, ?, ?, ?, ?)",
                 (mpesa_code, case_id, event, refund_id, datetime.now().isoformat(timespec="seconds")))
    
    
    
def claim_refund(mpesa_code: str, case_id: int) -> int:
    """Append 'claimed' BEFORE sending money. Only the first claim per payment is kept.
    Returns the id of the case that owns the claim (may be another case)."""
    with _connect() as conn:
        _append_event(conn, mpesa_code, case_id, "claimed")
        return conn.execute("SELECT case_id FROM refund_events WHERE mpesa_code = ? AND event = 'claimed'",
                            (mpesa_code,)).fetchone()[0]
        
        
def record_sent(mpesa_code: str, case_id: int, refund_id: str) -> None:
    """Append 'sent' AFTER the money left."""
    with _connect() as conn:
        _append_event(conn, mpesa_code, case_id, "sent", refund_id)
        
        
        
def refund_history(mpesa_code: str) -> list[dict]:
    """Every ledger event for one payment, oldest first. The current state is read from this."""
    with _connect() as conn:
        rows = conn.execute("SELECT case_id, event, refund_id, at FROM refund_events WHERE mpesa_code = ? ORDER BY id",
                            (mpesa_code,)).fetchall()
    return [{"case_id": r[0], "event": r[1], "refund_id": r[2], "at": r[3]} for r in rows]


