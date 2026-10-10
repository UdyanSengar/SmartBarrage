import sqlite3
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

DB_PATH = "barrage_state.db"
SAFE_LIMIT_CUSECS = 75000.0

st.set_page_config(
    page_title="Smart Barrage Operations Center", layout="wide"
)

st_autorefresh(interval=2000, key="data_refresh")

st.title("🌊 Smart Barrage SCADA & Flood Management")


def fetch_system_state():
    conn = sqlite3.connect(DB_PATH)
    try:
        df_decisions = pd.read_sql_query(
            "SELECT * FROM gate_decisions ORDER BY id DESC LIMIT 100", conn
        )
        df_sensor = pd.read_sql_query(
            "SELECT source_type FROM sensor_telemetry ORDER BY id DESC LIMIT 1",
            conn,
        )
    except Exception:
        df_decisions = pd.DataFrame()
        df_sensor = pd.DataFrame()
    finally:
        conn.close()
    return df_decisions, df_sensor


df_decisions, df_sensor = fetch_system_state()

if df_decisions.empty:
    st.info(
        "⏳ Waiting for sensor data. Ensure `python sensor_stream.py` and `python controller_model.py` are running."
    )
    st.stop()


df = df_decisions.iloc[::-1].reset_index(drop=True)
latest = df.iloc[-1]
source_type = df_sensor["source_type"].iloc[0] if not df_sensor.empty else "N/A"

col1, col2, col3, col4 = st.columns(4)

with col1:
    if latest["downstream_cusecs"] > SAFE_LIMIT_CUSECS:
        st.error("🚨 FLOOD THRESHOLD BREACHED")
    else:
        st.success("✅ SYSTEM SECURE")
    st.caption(f"Input Mode: **{source_type}**")

with col2:
    st.metric("Inflow", f"{latest['inflow_cusecs']:,.0f} cusecs")

with col3:
    st.metric(
        "Downstream Release",
        f"{latest['downstream_cusecs']:,.0f} cusecs",
        delta=f"{latest['downstream_cusecs'] - SAFE_LIMIT_CUSECS:,.0f} vs safe cap",
        delta_color="inverse",
    )

with col4:
    st.metric("Active Gate Directive", latest["gate_action"])

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=df["timestamp"],
        y=df["inflow_cusecs"],
        mode="lines+markers",
        name="Reservoir Inflow",
        line=dict(color="gray", dash="dash"),
    )
)
fig.add_trace(
    go.Scatter(
        x=df["timestamp"],
        y=df["downstream_cusecs"],
        mode="lines+markers",
        name="Downstream Controlled Flow",
        line=dict(color="#1f77b4", width=3),
    )
)
fig.add_trace(
    go.Scatter(
        x=df["timestamp"],
        y=df["diversion_cusecs"],
        mode="lines+markers",
        name="Diversion Canal Flow",
        line=dict(color="#ff7f0e", width=2),
    )
)
fig.add_trace(
    go.Scatter(
        x=[df["timestamp"].iloc[0], df["timestamp"].iloc[-1]],
        y=[SAFE_LIMIT_CUSECS, SAFE_LIMIT_CUSECS],
        mode="lines",
        name="Safe River Limit (75,000 cusecs)",
        line=dict(color="red", width=2, dash="dot"),
    )
)

fig.update_layout(
    title="Real-Time Flood Routing Stream",
    xaxis_title="UTC Timestamp",
    yaxis_title="Discharge Rate (cusecs)",
    hovermode="x unified",
    margin=dict(l=20, r=20, t=40, b=20),
)

st.plotly_chart(fig, use_container_width=True)


st.subheader("📋 Autonomous Gate Actuation Audit Trail")
st.dataframe(
    df[
        [
            "timestamp",
            "inflow_cusecs",
            "downstream_cusecs",
            "diversion_cusecs",
            "gate_action",
            "reason",
        ]
    ].tail(25),
    use_container_width=True,
    height=260,
)