from datetime import datetime
import os
import sqlite3
import time
from typing import Optional
from fastapi import FastAPI, HTTPException
import numpy as np
from pydantic import BaseModel, Field

DB_PATH = "barrage_state.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sensor_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            station_id TEXT NOT NULL,
            inflow_cusecs REAL NOT NULL,
            source_type TEXT NOT NULL,  -- 'SIMULATED' or 'HARDWARE'
            water_level_m REAL,
            battery_v REAL
        )
    """)
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


init_db()

app = FastAPI(title="Smart Barrage Hardware Gateway", version="1.0.0")


class HardwareTelemetry(BaseModel):
    station_id: str = Field(..., example="GAUGE_STATION_ALPHA")
    inflow_cusecs: float = Field(..., ge=0.0)
    water_level_m: Optional[float] = None
    battery_v: Optional[float] = None


@app.post("/api/v1/telemetry", status_code=201)
def ingest_physical_sensor(data: HardwareTelemetry):
    """Call this endpoint from physical IoT hardware (ESP32, Cellular RTU, LoRa) in the future."""
    now = datetime.utcnow().isoformat()
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO sensor_telemetry (timestamp, station_id, inflow_cusecs, source_type, water_level_m, battery_v)
            VALUES (?, ?, ?, 'HARDWARE', ?, ?)
            """,
            (
                now,
                data.station_id,
                data.inflow_cusecs,
                data.water_level_m,
                data.battery_v,
            ),
        )
        conn.commit()
        conn.close()
        return {
            "status": "INGESTED",
            "source": "HARDWARE",
            "station": data.station_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class HydrographSimulator:

    def __init__(
        self,
        base_flow=50000.0,
        peak_flow=190000.0,
        cycle_minutes=15,
        step_interval_sec=2,
    ):
        self.base_flow = base_flow
        self.peak_flow = peak_flow
        self.cycle_seconds = cycle_minutes * 60
        self.step_sec = step_interval_sec
        self.elapsed = 0.0

    def get_next_reading(self) -> float:
        """Generates continuous surge cycles using half-sine flood curves with sensor noise."""
        phase = (self.elapsed % self.cycle_seconds) / self.cycle_seconds
        # Half sine wave for flood surge between 20% and 80% of cycle
        if 0.2 <= phase <= 0.8:
            spike_progress = (phase - 0.2) / 0.6
            surge = (self.peak_flow - self.base_flow) * np.sin(
                spike_progress * np.pi
            )
        else:
            surge = 0.0

        noise = np.random.normal(0, 0.02 * self.base_flow)
        reading = max(0.0, self.base_flow + surge + noise)
        self.elapsed += self.step_sec
        return reading


def run_continuous_simulation():
    """Continuously writes simulated hydrograph readings into the database."""
    print("📡 Sensor Simulator Active (Press Ctrl+C to stop)...")
    sim = HydrographSimulator(
        base_flow=50000.0,
        peak_flow=195000.0,
        cycle_minutes=10,
        step_interval_sec=2,
    )

    while True:
        val = sim.get_next_reading()
        now = datetime.utcnow().isoformat()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO sensor_telemetry (timestamp, station_id, inflow_cusecs, source_type)
            VALUES (?, 'SIM_RIVER_GAUGE', ?, 'SIMULATED')
            """,
            (now, val),
        )
        conn.commit()
        conn.close()

        print(f"[{now[11:19]}] Simulated Inflow: {val:,.1f} cusecs")
        time.sleep(2)


if __name__ == "__main__":
    run_continuous_simulation()