"""
dashboard.py — FinSolve RAG Pro Production Monitoring Dashboard

Run with: streamlit run app/monitoring/dashboard.py --server.port 8502

Shows:
  - Real-time KPI cards (queries, avg latency, total cost, guardrail blocks)
  - Latency trend chart
  - Cost per query over time
  - Model usage breakdown
  - Role distribution
  - Cache hit rate gauge
  - Guardrail event log
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import duckdb
import pandas as pd
from datetime import datetime

DB_PATH = os.environ.get("DUCKDB_PATH", "finsolve_audit.db")

st.set_page_config(
    page_title="FinSolve RAG Pro — Monitoring",
    page_icon="📊",
    layout="wide",
)

# ─────────────────────────────────────────────
# Styling
# ─────────────────────────────────────────────
st.markdown("""
<style>
    body { background: #0f1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e2130, #252a3a);
        border: 1px solid #2d3250;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .metric-value { font-size: 2.2rem; font-weight: 700; color: #7c9ef0; }
    .metric-label { font-size: 0.85rem; color: #8b95b0; margin-top: 4px; }
    .stMetric > div { background: #1e2130; border-radius: 10px; padding: 12px; }
    h1, h2, h3 { color: #e0e6f0 !important; }
    .stDataFrame { border-radius: 8px; }
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────

@st.cache_data(ttl=30)  # refresh every 30s
def load_metrics(hours: int = 24) -> pd.DataFrame:
    try:
        conn = duckdb.connect(DB_PATH)
        df = conn.execute(f"""
            SELECT * FROM query_metrics
            WHERE timestamp >= NOW() - INTERVAL '{hours} HOUR'
            ORDER BY timestamp DESC
        """).df()
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30)
def load_guardrail_events(hours: int = 24) -> pd.DataFrame:
    try:
        conn = duckdb.connect(DB_PATH)
        df = conn.execute(f"""
            SELECT timestamp, username, role, event_type, reason
            FROM guardrail_events
            WHERE timestamp >= NOW() - INTERVAL '{hours} HOUR'
            ORDER BY timestamp DESC
            LIMIT 50
        """).df()
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30)
def load_chat_logs(hours: int = 24) -> pd.DataFrame:
    try:
        conn = duckdb.connect(DB_PATH)
        df = conn.execute(f"""
            SELECT timestamp, username, role, query, model_used, latency_ms, cache_hit
            FROM chat_logs
            WHERE timestamp >= NOW() - INTERVAL '{hours} HOUR'
            ORDER BY timestamp DESC
            LIMIT 100
        """).df()
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────

st.markdown("# 📊 FinSolve RAG Pro — Production Monitoring")
st.markdown("Real-time observability dashboard · Auto-refreshes every 30 seconds")

hours_filter = st.select_slider(
    "Time window", options=[1, 6, 12, 24, 48, 168], value=24,
    format_func=lambda h: f"{h}h" if h < 48 else f"{h//24}d"
)
st.markdown("---")

df = load_metrics(hours_filter)
guardrail_df = load_guardrail_events(hours_filter)
chat_df = load_chat_logs(hours_filter)

# ─────────────────────────────────────────────
# KPI Cards
# ─────────────────────────────────────────────

col1, col2, col3, col4, col5, col6 = st.columns(6)

total_queries = len(df)
avg_latency   = round(df["latency_ms"].mean(), 1) if not df.empty else 0
total_cost    = round(df["cost_usd"].sum(), 4) if not df.empty else 0
guardrail_blocks = int(df["guardrail_triggered"].sum()) if not df.empty else 0
cache_hits    = int(df["cache_hit"].sum()) if not df.empty else 0
cache_rate    = round((cache_hits / total_queries * 100) if total_queries > 0 else 0, 1)

col1.metric("💬 Total Queries",   total_queries)
col2.metric("⚡ Avg Latency",     f"{avg_latency} ms")
col3.metric("💰 Total Cost",      f"${total_cost}")
col4.metric("🛡️ Guardrail Blocks", guardrail_blocks)
col5.metric("🎯 Cache Hits",      cache_hits)
col6.metric("📈 Cache Rate",      f"{cache_rate}%")

st.markdown("---")

# ─────────────────────────────────────────────
# Charts
# ─────────────────────────────────────────────

if not df.empty:
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df_sorted = df.sort_values("timestamp")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("⚡ Latency Over Time (ms)")
        latency_ts = df_sorted.set_index("timestamp")[["latency_ms"]].resample("5min").mean()
        st.line_chart(latency_ts, color="#7c9ef0")

    with c2:
        st.subheader("💰 Cost Per Query (USD)")
        cost_ts = df_sorted.set_index("timestamp")[["cost_usd"]].resample("5min").sum()
        st.line_chart(cost_ts, color="#f07c9e")

    c3, c4 = st.columns(2)

    with c3:
        st.subheader("🤖 Queries by Model")
        model_counts = df["model_used"].value_counts().reset_index()
        model_counts.columns = ["Model", "Queries"]
        st.bar_chart(model_counts.set_index("Model"), color="#9ef07c")

    with c4:
        st.subheader("👥 Queries by Role")
        role_counts = df["role"].value_counts().reset_index()
        role_counts.columns = ["Role", "Queries"]
        st.bar_chart(role_counts.set_index("Role"), color="#f0c47c")

    st.markdown("---")
    st.subheader("📋 Complexity Distribution")
    comp_counts = df["complexity"].value_counts()
    st.bar_chart(comp_counts, color="#c47cf0")

else:
    st.info("No metrics data yet. Start chatting with the assistant to see data here.")

# ─────────────────────────────────────────────
# Guardrail Events Table
# ─────────────────────────────────────────────

st.markdown("---")
st.subheader("🛡️ Guardrail Events")

if not guardrail_df.empty:
    st.dataframe(guardrail_df, use_container_width=True, hide_index=True)
else:
    st.success("✅ No guardrail events in selected time window.")

# ─────────────────────────────────────────────
# Recent Chat Logs
# ─────────────────────────────────────────────

st.markdown("---")
st.subheader("💬 Recent Queries")

if not chat_df.empty:
    st.dataframe(
        chat_df[["timestamp", "username", "role", "query", "model_used", "latency_ms", "cache_hit"]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No chat logs yet.")

st.markdown("---")
st.caption(f"Last refreshed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
