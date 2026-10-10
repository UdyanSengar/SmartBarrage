import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

DB_PATH = "barrage_state.db"
SAFE_CAPACITY_CUSECS = 75000.0
HEARTBEAT_TIMEOUT_SECONDS = 6.0

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_control_state():
    """Initializes the single-row control state latch table."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS system_control (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            mode TEXT NOT NULL DEFAULT 'AUTO',
            manual_downstream REAL DEFAULT 50000.0,
            manual_diversion REAL DEFAULT 0.0,
            manual_action TEXT DEFAULT 'HOLD',
            override_reason TEXT DEFAULT '',
            controller_heartbeat TEXT
        )
    """)
    cur.execute("""
        INSERT OR IGNORE INTO system_control 
        (id, mode, manual_downstream, manual_diversion, manual_action, override_reason, controller_heartbeat)
        VALUES (1, 'AUTO', 50000.0, 0.0, 'HOLD', 'System Initialized', ?)
    """, (datetime.now(timezone.utc).isoformat(),))
    conn.commit()
    conn.close()


def get_system_mode() -> Dict[str, Any]:
    """Retrieves current control mode and operator setpoints."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT mode, manual_downstream, manual_diversion, manual_action, override_reason, controller_heartbeat FROM system_control WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"mode": "AUTO", "controller_alive": False}

    last_beat = row[5]
    is_alive = False
    if last_beat:
        try:
            delta = (datetime.now(timezone.utc) - datetime.fromisoformat(last_beat)).total_seconds()
            is_alive = delta < HEARTBEAT_TIMEOUT_SECONDS
        except Exception:
            is_alive = False

    return {
        "mode": row[0],
        "manual_downstream": row[1],
        "manual_diversion": row[2],
        "manual_action": row[3],
        "override_reason": row[4],
        "last_heartbeat": last_beat,
        "controller_alive": is_alive
    }


def set_manual_override(downstream: float, diversion: float, action: str, reason: str):
    """Enables manual override and sets operator discharge targets."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE system_control
        SET mode = 'MANUAL_OVERRIDE',
            manual_downstream = ?,
            manual_diversion = ?,
            manual_action = ?,
            override_reason = ?
        WHERE id = 1
    """, (downstream, diversion, action, reason))
    conn.commit()
    conn.close()


def resume_auto_mode():
    """Hands control back to the predictive model."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE system_control
        SET mode = 'AUTO',
            override_reason = 'Operator resumed autonomous mode'
        WHERE id = 1
    """)
    conn.commit()
    conn.close()


def update_heartbeat():
    """Called by controller_model.py every iteration to prove it has not frozen."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE system_control
        SET controller_heartbeat = ?
        WHERE id = 1
    """, (datetime.now(timezone.utc).isoformat(),))
    conn.commit()
    conn.close()