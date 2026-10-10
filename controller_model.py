import time
import sqlite3
import numpy as np
from datetime import datetime, timezone

DB_PATH = "barrage_state.db"
SAFE_CAPACITY_CUSECS = 75000.0
SAFETY_BUFFER = 0.90  
MAX_GATE_DELTA_PER_STEP = 8000.0
EVAL_INTERVAL_SECONDS = 2
HEARTBEAT_TIMEOUT_SECONDS = 6.0


def init_control_tables():
    """Initializes tables for sensor data, decisions, and system override state."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
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
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gate_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            inflow_cusecs REAL NOT NULL,
            downstream_cusecs REAL NOT NULL,
            diversion_cusecs REAL NOT NULL,
            gate_action TEXT NOT NULL,
            reason TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_control_tables()


class PredictiveBarrageController:
    def __init__(self, safe_capacity=SAFE_CAPACITY_CUSECS, buffer_ratio=SAFETY_BUFFER, max_delta=MAX_GATE_DELTA_PER_STEP):
        self.safe_capacity = safe_capacity
        self.target_threshold = safe_capacity * buffer_ratio
        self.max_delta = max_delta

    def evaluate(self, current_inflow: float, forecast_window: list, prev_outflow: float):
        peak_inflow = max(forecast_window) if forecast_window else current_inflow

        if peak_inflow > self.safe_capacity:
            target_outflow = min(current_inflow, self.target_threshold)
            delta = np.clip(target_outflow - prev_outflow, -self.max_delta, self.max_delta)
            downstream = prev_outflow + delta
            diversion = max(0.0, current_inflow - downstream)
            action = "AUTO: LIFT DIVERSION GATES" if diversion > 0 else "AUTO: HOLD GATES"
            reason = (
                f"SURGE DETECTED: Forecast peak {peak_inflow:,.0f} cusecs exceeds {self.safe_capacity:,.0f} limit. "
                f"Diverting {diversion:,.0f} cusecs to retention basin."
            )
        else:
            delta = np.clip(current_inflow - prev_outflow, -self.max_delta, self.max_delta)
            downstream = prev_outflow + delta
            diversion = 0.0
            action = "AUTO: NOMINAL FLOW"
            reason = "NOMINAL: Inflow remains inside safe channel capacity."

        return downstream, diversion, action, reason


def pulse_heartbeat():
    """Signals that the autonomous worker is active and healthy."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE system_control SET controller_heartbeat = ? WHERE id = 1", (datetime.now(timezone.utc).isoformat(),))
    conn.commit()
    conn.close()


def get_system_control_state():
    """Reads current operation mode and manual setpoints."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT mode, manual_downstream, manual_diversion, manual_action, override_reason FROM system_control WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"mode": "AUTO"}
    return {
        "mode": row[0],
        "manual_downstream": row[1],
        "manual_diversion": row[2],
        "manual_action": row[3],
        "override_reason": row[4]
    }


def get_recent_inflows(limit=15):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT inflow_cusecs FROM sensor_telemetry ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in reversed(rows)]


def get_last_downstream():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT downstream_cusecs FROM gate_decisions ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 50000.0


def log_decision(inflow, downstream, diversion, action, reason):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO gate_decisions (timestamp, inflow_cusecs, downstream_cusecs, diversion_cusecs, gate_action, reason)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.now(timezone.utc).isoformat(), inflow, downstream, diversion, action, reason))
    conn.commit()
    conn.close()


def run_controller():
    controller = PredictiveBarrageController()
    print("🧠 Barrage Controller Engine Running (Auto + Override Guard Active)...")

    while True:
        try:
            pulse_heartbeat()
            ctrl_state = get_system_control_state()
            inflows = get_recent_inflows(limit=15)

            if inflows:
                curr_inflow = inflows[-1]

                
                if ctrl_state["mode"] == "MANUAL_OVERRIDE":
                    downstream = ctrl_state["manual_downstream"]
                    diversion = ctrl_state["manual_diversion"]
                    action = f"MANUAL: {ctrl_state['manual_action']}"
                    reason = f"OPERATOR OVERRIDE: {ctrl_state['override_reason']}"
                    log_decision(curr_inflow, downstream, diversion, action, reason)
                    print(f"⚠️ [MANUAL DISPATCH] Out: {downstream:,.0f} | Div: {diversion:,.0f} | Reason: {ctrl_state['override_reason']}")
                else:
                    
                    prev_outflow = get_last_downstream()
                    downstream, diversion, action, reason = controller.evaluate(curr_inflow, inflows, prev_outflow)
                    log_decision(curr_inflow, downstream, diversion, action, reason)
                    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] In: {curr_inflow:,.0f} | Out: {downstream:,.0f} | Div: {diversion:,.0f} -> {action}")

        except Exception as e:
            print(f"❌ Controller Execution Error: {e}")

        time.sleep(EVAL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_controller()