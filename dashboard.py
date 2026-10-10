"""
dashboard_app.py
Real-Time Barrage SCADA Dashboard with Emergency Manual Override & Failover Control.
Run with: streamlit run dashboard_app.py
"""
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timezone

def st_autorefresh(interval=2000, key=None):
    components.html(
        f"""
        <script>
            setTimeout(function () {{
                window.parent.location.reload();
            }}, {int(interval)});
        </script>
        """,
        height=0,
    )

DB_PATH = "barrage_state.db"
SAFE_LIMIT_CUSECS = 75000.0
HEARTBEAT_TIMEOUT_SECONDS = 6.0

st.set_page_config(page_title="Smart Barrage SCADA & Supervisory Control", layout="wide")
st_autorefresh(interval=2000, key="data_refresh")

st.title("🌊 Smart Barrage SCADA & Supervisory Control")

def get_control_state():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("SELECT mode, manual_downstream, manual_diversion, manual_action, override_reason, controller_heartbeat FROM system_control WHERE id = 1")
        row = cur.fetchone()
    except Exception:
        row = None
    finally:
        conn.close()

    if not row:
        return {"mode": "AUTO", "controller_alive": False, "manual_downstream": 60000.0, "manual_diversion": 0.0, "manual_action": "HOLD"}

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
        "controller_alive": is_alive
    }


def set_manual_override(downstream, diversion, action, reason):
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        UPDATE system_control
        SET mode = 'AUTO',
            override_reason = 'Operator resumed autonomous mode'
        WHERE id = 1
    """)
    conn.commit()
    conn.close()


def fetch_system_telemetry():
    conn = sqlite3.connect(DB_PATH)
    try:
        df_decisions = pd.read_sql_query("SELECT * FROM gate_decisions ORDER BY id DESC LIMIT 100", conn)
        df_sensor = pd.read_sql_query("SELECT source_type, inflow_cusecs FROM sensor_telemetry ORDER BY id DESC LIMIT 1", conn)
    except Exception:
        df_decisions = pd.DataFrame()
        df_sensor = pd.DataFrame()
    finally:
        conn.close()
    return df_decisions, df_sensor


ctrl_state = get_control_state()
df_decisions, df_sensor = fetch_system_telemetry()

model_alive = ctrl_state["controller_alive"]
is_manual = ctrl_state["mode"] == "MANUAL_OVERRIDE"

col1, col2, col3, col4 = st.columns(4)

with col1:
    if not model_alive:
        st.error("🚨 MODEL HEALTH: OFFLINE / CRASHED")
    elif is_manual:
        st.warning("⚠️ MODE: MANUAL OVERRIDE")
    else:
        st.success("🟢 MODE: AUTONOMOUS")
    source_type = df_sensor["source_type"].iloc[0] if not df_sensor.empty else "N/A"
    st.caption(f"Telemetry Source: **{source_type}**")

with col2:
    current_inflow = df_sensor["inflow_cusecs"].iloc[0] if not df_sensor.empty else 0.0
    st.metric("Live Inflow Gauge", f"{current_inflow:,.0f} cusecs")

with col3:
    latest_downstream = df_decisions["downstream_cusecs"].iloc[0] if not df_decisions.empty else 0.0
    st.metric(
        "Downstream Release",
        f"{latest_downstream:,.0f} cusecs",
        delta=f"{latest_downstream - SAFE_LIMIT_CUSECS:,.0f} vs limit",
        delta_color="inverse"
    )

with col4:
    latest_action = df_decisions["gate_action"].iloc[0] if not df_decisions.empty else "N/A"
    st.metric("Current Gate Directive", latest_action)

st.markdown("---")

with st.expander("🛠️ MANUAL OVERRIDE & DISPATCH CONSOLE", expanded=(is_manual or not model_alive)):
    st.markdown("Intervene manually if the predictive model encounters an error, sensor drift occurs, or emergency human control is required.")
    
    col_ctrl1, col_ctrl2 = st.columns(2)
    
    with col_ctrl1:
        st.write("### Target Flow Allocation")
        manual_downstream_target = st.slider(
            "Manual Downstream Release (cusecs)",
            min_value=10000.0,
            max_value=120000.0,
            value=float(ctrl_state.get("manual_downstream", 60000.0)),
            step=2500.0
        )
        manual_diversion_target = st.slider(
            "Manual Diversion Discharge (cusecs)",
            min_value=0.0,
            max_value=150000.0,
            value=float(ctrl_state.get("manual_diversion", 0.0)),
            step=5000.0
        )

    with col_ctrl2:
        st.write("### Gate Commands & Justification")
        manual_action_select = st.selectbox(
            "Gate Actuation Command",
            ["HOLD GATES", "LIFT DIVERSION GATES (EMERGENCY)", "LOWER MAIN GATES", "OPEN FULL ALL CANALS"]
        )
        override_reason_text = st.text_input(
            "Operator Log / Reason for Override",
            value="Manual intervention by barrage control officer" if not is_manual else ctrl_state.get("override_reason", "")
        )
        
        btn1, btn2 = st.columns(2)
        with btn1:
            if st.button("🚨 ENGAGE OVERRIDE", type="primary", use_container_width=True):
                set_manual_override(
                    downstream=manual_downstream_target,
                    diversion=manual_diversion_target,
                    action=manual_action_select,
                    reason=override_reason_text
                )
                st.rerun()

        with btn2:
            if st.button("🔄 RESUME AUTO MODEL", use_container_width=True):
                resume_auto_mode()
                st.rerun()


if not df_decisions.empty:
    df_plot = df_decisions.iloc[::-1].reset_index(drop=True)
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_plot["timestamp"], y=df_plot["inflow_cusecs"],
        mode="lines+markers", name="River Inflow", line=dict(color="gray", dash="dash")
    ))
    fig.add_trace(go.Scatter(
        x=df_plot["timestamp"], y=df_plot["downstream_cusecs"],
        mode="lines+markers", name="Downstream Release", line=dict(color="#1f77b4", width=3)
    ))
    fig.add_trace(go.Scatter(
        x=df_plot["timestamp"], y=df_plot["diversion_cusecs"],
        mode="lines+markers", name="Diversion Discharge", line=dict(color="#ff7f0e", width=2)
    ))
    fig.add_trace(go.Scatter(
        x=[df_plot["timestamp"].iloc[0], df_plot["timestamp"].iloc[-1]],
        y=[SAFE_LIMIT_CUSECS, SAFE_LIMIT_CUSECS],
        mode="lines", name=f"Safe Limit ({SAFE_LIMIT_CUSECS:,.0f})", line=dict(color="red", width=2, dash="dot")
    ))

    fig.update_layout(
        title="Live Water Routing & Allocation Stream",
        xaxis_title="UTC Timestamp",
        yaxis_title="Discharge Rate (cusecs)",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Decision & Actuation Audit Trail")
    st.dataframe(
        df_plot[["timestamp", "inflow_cusecs", "downstream_cusecs", "diversion_cusecs", "gate_action", "reason"]].tail(25),
        use_container_width=True,
        height=260
    )
else:
    st.info("⏳ Waiting for data from `sensor_stream.py` and `controller_model.py`...")