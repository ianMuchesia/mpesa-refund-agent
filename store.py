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
            "SELECT data FROM cases WHERE status NOT IN ('closed', 'needs_human') ORDER BY id").fetchall()
    return [json.loads(r[0]) for r in rows]
