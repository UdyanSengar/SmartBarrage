
import _sqlite3
import panda as pd
import poly.graph_objects as go 
import streamlite as st
from streamlit_autorefresh import st_autorefresh
DB_PATH =" barrage_state.db"
SAFE_LIMIT_CUSEC=75000.0
st.st_page_config(
    page_title="Smart Barrage Operations Center",layout="cwide"
)

#AUTO REFRESH UI
st_autorefresh(interval=2000,key="data_refresh")
st.title("Smart Barrage SCAD and flood Management ")
def fetch_system_state():
    conn=sqlit3.connect(DB_PATH)
    try:
        df_descision=pd.read_sql_query("SELECT"* FROM gate_decisions ORDER BY id DESC LIMIT 100",conn)
        df_sensor=pd.read_sql_query("SELECT source_type from telemetry ORDER BY ID DESCT LIMIT 1",)                               