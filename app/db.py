"""
db.py — DuckDB persistence layer.
Stores: chat audit logs, document chunk metadata, query performance metrics,
        and Human-in-the-Loop (HITL) feedback ratings.
"""

import duckdb
import os
import json
from datetime import datetime

DB_PATH = os.environ.get("DUCKDB_PATH", "finsolve_audit.db")


def get_conn():
    return duckdb.connect(DB_PATH)


def init_db():
    """Create all tables if they don't exist."""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_logs (
            id          VARCHAR PRIMARY KEY,
            timestamp   TIMESTAMP,
            username    VARCHAR,
            role        VARCHAR,
            query       TEXT,
            answer      TEXT,
            chunk_ids   TEXT,
            model_used  VARCHAR,
            latency_ms  DOUBLE,
            cache_hit   BOOLEAN DEFAULT FALSE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS doc_chunks (
            chunk_id    VARCHAR PRIMARY KEY,
            file_name   VARCHAR,
            role        VARCHAR,
            department  VARCHAR,
            source      VARCHAR,
            indexed_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS query_metrics (
            id                  VARCHAR PRIMARY KEY,
            timestamp           TIMESTAMP,
            username            VARCHAR,
            role                VARCHAR,
            model_used          VARCHAR,
            complexity          VARCHAR,
            latency_ms          DOUBLE,
            tokens_used         INTEGER,
            cost_usd            DOUBLE,
            cache_hit           BOOLEAN,
            guardrail_triggered BOOLEAN,
            guardrail_reason    VARCHAR
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS guardrail_events (
            id          VARCHAR PRIMARY KEY,
            timestamp   TIMESTAMP,
            username    VARCHAR,
            role        VARCHAR,
            event_type  VARCHAR,
            reason      VARCHAR,
            query_hash  VARCHAR
        )
    """)

    # ── HITL Feedback ─────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id          VARCHAR PRIMARY KEY,
            timestamp   TIMESTAMP,
            chat_id     VARCHAR NOT NULL,
            username    VARCHAR,
            role        VARCHAR,
            rating      INTEGER NOT NULL,   -- +1 thumbs-up, -1 thumbs-down
            comment     TEXT DEFAULT ''
        )
    """)
    conn.close()


def log_chat(
    username: str,
    role: str,
    query: str,
    chunk_ids: list,
    answer_text: str,
    model_used: str = "unknown",
    latency_ms: float = 0.0,
    cache_hit: bool = False,
):
    import uuid
    conn = get_conn()
    conn.execute(
        """
        INSERT OR REPLACE INTO chat_logs
            (id, timestamp, username, role, query, answer, chunk_ids, model_used, latency_ms, cache_hit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            str(uuid.uuid4()),
            datetime.utcnow(),
            username,
            role,
            query,
            answer_text,
            json.dumps(chunk_ids),
            model_used,
            latency_ms,
            cache_hit,
        ],
    )
    conn.close()


def log_doc_chunk(
    chunk_id: str, file_name: str, role: str, department: str, source: str
):
    conn = get_conn()
    conn.execute(
        """
        INSERT OR REPLACE INTO doc_chunks (chunk_id, file_name, role, department, source)
        VALUES (?, ?, ?, ?, ?)
        """,
        [chunk_id, file_name, role, department, source],
    )
    conn.close()


def log_metrics(
    username: str,
    role: str,
    model_used: str,
    complexity: str,
    latency_ms: float,
    tokens_used: int,
    cost_usd: float,
    cache_hit: bool,
    guardrail_triggered: bool,
    guardrail_reason: str = "",
):
    import uuid
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO query_metrics
            (id, timestamp, username, role, model_used, complexity,
             latency_ms, tokens_used, cost_usd, cache_hit,
             guardrail_triggered, guardrail_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            str(uuid.uuid4()),
            datetime.utcnow(),
            username,
            role,
            model_used,
            complexity,
            latency_ms,
            tokens_used,
            cost_usd,
            cache_hit,
            guardrail_triggered,
            guardrail_reason,
        ],
    )
    conn.close()


def log_guardrail_event(
    username: str, role: str, event_type: str, reason: str, query: str
):
    import uuid
    import hashlib
    query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO guardrail_events (id, timestamp, username, role, event_type, reason, query_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [str(uuid.uuid4()), datetime.utcnow(), username, role, event_type, reason, query_hash],
    )
    conn.close()


def log_feedback(
    chat_id: str,
    username: str,
    role: str,
    rating: int,
    comment: str = "",
):
    """
    Persist a HITL feedback rating.

    Parameters
    ----------
    chat_id  : UUID of the chat message being rated (from ChatResponse.chat_id).
    username : Authenticated user who submitted the rating.
    role     : User's role at time of feedback.
    rating   : +1 for thumbs-up, -1 for thumbs-down.
    comment  : Optional free-text comment (max 500 chars recommended).
    """
    import uuid
    if rating not in (1, -1):
        raise ValueError(f"rating must be +1 or -1, got {rating}")
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO feedback (id, timestamp, chat_id, username, role, rating, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [str(uuid.uuid4()), datetime.utcnow(), chat_id, username, role, rating, comment[:500]],
    )
    conn.close()


def get_feedback_summary(hours: int = 24) -> dict:
    """Return aggregate HITL feedback stats over the last `hours` hours."""
    conn = get_conn()
    result = conn.execute(
        f"""
        SELECT
            COUNT(*)                                                    AS total_ratings,
            COALESCE(SUM(CASE WHEN rating = 1  THEN 1 ELSE 0 END), 0)  AS thumbs_up,
            COALESCE(SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END), 0)  AS thumbs_down,
            ROUND(
                100.0 * COALESCE(SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END), 0)
                / NULLIF(COUNT(*), 0),
                1
            )                                                           AS satisfaction_pct
        FROM feedback
        WHERE timestamp >= NOW() - INTERVAL {hours} HOUR
        """,
    ).fetchone()
    conn.close()
    if result:
        return dict(zip(["total_ratings", "thumbs_up", "thumbs_down", "satisfaction_pct"], result))
    return {"total_ratings": 0, "thumbs_up": 0, "thumbs_down": 0, "satisfaction_pct": None}


def get_recent_metrics(hours: int = 24):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT * FROM query_metrics
        WHERE timestamp >= NOW() - INTERVAL ? HOUR
        ORDER BY timestamp DESC
        """,
        [hours],
    ).fetchall()
    cols = [d[0] for d in conn.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def get_metrics_summary(hours: int = 24):
    conn = get_conn()
    result = conn.execute(
        """
        SELECT
            COUNT(*)                        AS total_queries,
            AVG(latency_ms)                 AS avg_latency_ms,
            SUM(cost_usd)                   AS total_cost_usd,
            SUM(tokens_used)                AS total_tokens,
            SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)              AS cache_hits,
            SUM(CASE WHEN guardrail_triggered THEN 1 ELSE 0 END)    AS guardrail_blocks,
            COUNT(DISTINCT username)        AS unique_users
        FROM query_metrics
        WHERE timestamp >= NOW() - INTERVAL ? HOUR
        """,
        [hours],
    ).fetchone()
    conn.close()
    keys = [
        "total_queries", "avg_latency_ms", "total_cost_usd",
        "total_tokens", "cache_hits", "guardrail_blocks", "unique_users"
    ]
    return dict(zip(keys, result)) if result else {}
