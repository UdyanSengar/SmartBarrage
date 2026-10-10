from datetime import datetime
import sqlite3
import time
import numpy as np

DB_PATH = "barrage_state.db"
SAFE_CAPACITY_CUSECS = 75000.0
SAFETY_BUFFER = 0.90  # 90% threshold
MAX_GATE_DELTA_PER_STEP = 8000.0  # mechnical failure prevention
EVAL_INTERVAL_SECONDS = 2


class PredictiveBarrageController:

    def __init__(
        self,
        safe_capacity=SAFE_CAPACITY_CUSECS,
        buffer_ratio=SAFETY_BUFFER,
        max_delta=MAX_GATE_DELTA_PER_STEP,
    ):
        self.safe_capacity = safe_capacity
        self.target_threshold = safe_capacity * buffer_ratio
        self.max_delta = max_delta

    def evaluate(self, current_inflow: float, forecast_window: list, prev_outflow: float):
        # Rolling forecast peak
        peak_inflow = max(forecast_window) if forecast_window else current_inflow

        if peak_inflow > self.safe_capacity:
            target_outflow = min(current_inflow, self.target_threshold)
            delta = np.clip(
                target_outflow - prev_outflow, -self.max_delta, self.max_delta
            )
            downstream = prev_outflow + delta
            diversion = max(0.0, current_inflow - downstream)
            action = "LIFT DIVERSION GATES" if diversion > 0 else "HOLD GATES"
            reason = (
                f"SURGE ALERT: Projected peak {peak_inflow:,.0f} cusecs exceeds {self.safe_capacity:,.0f} limit. "
                f"Diverting {diversion:,.0f} cusecs to retention basin."
            )
        else:
            delta = np.clip(
                current_inflow - prev_outflow, -self.max_delta, self.max_delta
            )
            downstream = prev_outflow + delta
            diversion = 0.0
            action = "NOMINAL RIVER FLOW"
            reason = "NOMINAL: Flow within safe discharge envelope."

        return downstream, diversion, action, reason


def get_recent_inflows(limit=15):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT inflow_cusecs FROM sensor_telemetry ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in reversed(rows)]


def get_last_downstream():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT downstream_cusecs FROM gate_decisions ORDER BY id DESC LIMIT 1"
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 50000.0


def log_decision(inflow, downstream, diversion, action, reason):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO gate_decisions (timestamp, inflow_cusecs, downstream_cusecs, diversion_cusecs, gate_action, reason)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.utcnow().isoformat(),
            inflow,
            downstream,
            diversion,
            action,
            reason,
        ),
    )
    conn.commit()
    conn.close()


def run_controller():
    controller = PredictiveBarrageController()
    print("🧠 Barrage Controller Engine Running...")

    while True:
        inflows = get_recent_inflows(limit=15)
        if inflows:
            curr_inflow = inflows[-1]
            prev_outflow = get_last_downstream()
            downstream, diversion, action, reason = controller.evaluate(
                curr_inflow, inflows, prev_outflow
            )
            log_decision(curr_inflow, downstream, diversion, action, reason)
            print(
                f"[{datetime.utcnow().strftime('%H:%M:%S')}] In: {curr_inflow:,.0f} | Out: {downstream:,.0f} | Div: {diversion:,.0f} -> {action}"
            )
        time.sleep(EVAL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_controller()