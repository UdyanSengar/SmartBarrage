from datetime import datetime
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
# --- CONSTANTS ---
SAFE_CAPACITY_CUSECS = 75000.0
CRITICAL_CAPACITY_CUSECS = 200000.0
CUSECS_TO_M3S = 0.0283168
SAFETY_BUFFER = 0.90
EVAL_INTERVAL_SECONDS = 2
MAX_GATE_DELTA_PER_STEP = 8000.0
DB_PATH = "barrage_stage.db"
class PrdeictiveBarrageController:
    def _init_(self,safe_capacity=SAFE_CAPACITY_CUSCES,buffer_ratio=SAFETY_BUFFER,max_delta=MAX_GATE_DELTA_PER_STEP):
        self.safe_capacity = safe_capacity
        self.target_threshold = safe_capacity * buffer_ratio
        self.max_delta = max_delta