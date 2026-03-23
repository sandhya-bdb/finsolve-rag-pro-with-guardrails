"""
UI.py — FinSolve RAG Pro Streamlit Chat Interface (Production)

Connects to the FastAPI backend using JWT authentication.
Features: login form, chat with role display, latency/model indicator,
guardrail warning display, source document citations,
HITL feedback (👍/👎), and HyDE/reranking status badges.
"""

import streamlit as st
import requests
import os

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="FinSolve RAG Pro",
    page_icon="🏦",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }

body {
    background: linear-gradient(135deg, #0a0e1a 0%, #0f1528 100%);
    color: #e0e6f0;
}

.stApp { background: transparent; }

.hero-title {
    font-size: 2.4rem;
    font-weight: 700;
    background: linear-gradient(135deg, #7c9ef0, #a78bf0, #f07c9e);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}

.hero-sub {
    color: #8b95b0;
    font-size: 0.95rem;
    margin-bottom: 1.5rem;
}

.role-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.chat-meta {
    font-size: 0.72rem;
    color: #8b95b0;
    margin-top: 4px;
}

.guardrail-warning {
    background: linear-gradient(135deg, #2a1a1a, #3a1c1c);
    border: 1px solid #8b3030;
    border-radius: 10px;
    padding: 12px 16px;
    color: #f07c7c;
}

.source-chip {
    background: #1e2130;
    border: 1px solid #2d3250;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 0.72rem;
    color: #7c9ef0;
    display: inline-block;
    margin: 2px;
}

div[data-testid="stChatMessage"] {
    background: #1a1f35;
    border-radius: 12px;
    border: 1px solid #252a40;
    margin-bottom: 8px;
    padding: 4px 8px;
}

.stTextInput > div > div > input {
    background: #1e2130;
    border: 1px solid #2d3250;
    border-radius: 8px;
    color: #e0e6f0;
}

.stButton > button {
    background: linear-gradient(135deg, #5c7af0, #8b5cf6);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(92, 122, 240, 0.4);
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Role color map
# ─────────────────────────────────────────────
ROLE_COLORS = {
    "c-levelexecutives": "#f0a030",
    "finance":           "#30c0f0",
    "hr":                "#f07c9e",
    "engineering":       "#7cf07c",
    "marketing":         "#c07cf0",
    "employee":          "#8b95b0",
}

# ─────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "feedback_given" not in st.session_state:
    # Set of chat_ids for which the user already submitted feedback
    st.session_state.feedback_given = set()


# ─────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────

def do_login(username: str, password: str) -> bool:
    try:
        resp = requests.post(
            f"{API_BASE}/login",
            data={"username": username, "password": password},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.token = data["access_token"]
            st.session_state.user  = data["username"]
            st.session_state.role  = data["role"]
            return True
        return False
    except Exception as e:
        st.error(f"Cannot connect to API: {e}")
        return False


def do_chat(message: str) -> dict:
    headers = {
        "Authorization": f"Bearer {st.session_state.token}",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        f"{API_BASE}/chat",
        json={"message": message},
        headers=headers,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def do_feedback(chat_id: str, rating: int, comment: str = "") -> bool:
    """Submit HITL feedback. Returns True on success."""
    try:
        headers = {
            "Authorization": f"Bearer {st.session_state.token}",
            "Content-Type": "application/json",
        }
        resp = requests.post(
            f"{API_BASE}/feedback",
            json={"chat_id": chat_id, "rating": rating, "comment": comment},
            headers=headers,
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


# ─────────────────────────────────────────────
# Login screen
# ─────────────────────────────────────────────

if not st.session_state.token:
    col_left, col_mid, col_right = st.columns([1, 1.5, 1])
    with col_mid:
        st.markdown('<div class="hero-title">🏦 FinSolve RAG Pro</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-sub">Enterprise AI Assistant · Secured · Role-Aware</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            st.subheader("Sign In")
            username = st.text_input("Username", placeholder="e.g. Binoy")
            password = st.text_input("Password", type="password", placeholder="Your password")
            submitted = st.form_submit_button("🔐 Login", use_container_width=True)

            if submitted:
                if do_login(username, password):
                    st.success(f"Welcome back, {st.session_state.user}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")

        st.markdown("---")
        st.caption("💡 **Demo users**: Binoy (finance) · sangit (hr) · Deb (engineering) · sandhya (c-level)")

# ─────────────────────────────────────────────
# Chat screen
# ─────────────────────────────────────────────

else:
    role_color = ROLE_COLORS.get(st.session_state.role, "#8b95b0")

    # Sidebar
    with st.sidebar:
        st.markdown("## 🏦 FinSolve RAG Pro")
        st.markdown(f"**User:** {st.session_state.user}")
        st.markdown(
            f"**Role:** <span class='role-badge' style='background:{role_color}22;color:{role_color};border:1px solid {role_color}44'>"
            f"{st.session_state.role}</span>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.markdown("**Quick Questions:**")
        examples = [
            "What is the Q3 revenue?",
            "Explain the leave policy",
            "How does deployment work?",
            "What are the marketing KPIs?",
        ]
        for ex in examples:
            if st.button(ex, key=f"ex_{ex[:20]}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": ex})
                with st.spinner("Thinking..."):
                    try:
                        result = do_chat(ex)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": result["response"],
                            "meta": result,
                        })
                    except Exception as e:
                        st.error(f"Error: {e}")
                st.rerun()

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for k in ["token", "user", "role", "messages"]:
                st.session_state[k] = None if k != "messages" else []
            st.rerun()

        st.markdown("---")
        st.caption("📊 [Monitoring Dashboard](http://localhost:8502)")

    # Main chat area
    st.markdown('<div class="hero-title">🏦 FinSolve RAG Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Ask anything about your company documents</div>', unsafe_allow_html=True)
    st.markdown("---")

    # Render history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
            if msg.get("meta", {}).get("guardrail_triggered"):
                st.markdown(f'<div class="guardrail-warning">{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(msg["content"])

            if msg["role"] == "assistant" and "meta" in msg:
                m = msg["meta"]
                cols = st.columns([2, 2, 2, 2])
                cols[0].caption(f"⚡ {m.get('latency_ms', 0):.0f}ms")
                cols[1].caption(f"🤖 {m.get('model_used', '?')}")
                cols[2].caption(f"🧠 {m.get('complexity', '?')}")
                cols[3].caption(f"{'🎯 cached' if m.get('cache_hit') else '🔍 retrieved'}")

                # Enhancement badges
                if m.get("hyde_used") or m.get("rerank_used"):
                    badge_cols = st.columns([1, 1, 6])
                    if m.get("hyde_used"):
                        badge_cols[0].caption("💡 HyDE")
                    if m.get("rerank_used"):
                        badge_cols[1].caption("🏆 Reranked")

                if m.get("sources"):
                    st.markdown("**📂 Sources:**")
                    for src in set(m["sources"]):
                        st.markdown(f'<span class="source-chip">📄 {src}</span>', unsafe_allow_html=True)

                # HITL Feedback buttons
                chat_id = m.get("chat_id", "")
                if chat_id and not m.get("guardrail_triggered"):
                    if chat_id in st.session_state.feedback_given:
                        st.caption("✔️ Feedback recorded")
                    else:
                        st.markdown("**Was this helpful?**")
                        fb_cols = st.columns([1, 1, 6])
                        if fb_cols[0].button("👍", key=f"up_{chat_id}"):
                            if do_feedback(chat_id, 1):
                                st.session_state.feedback_given.add(chat_id)
                                st.toast("✅ Thanks for your feedback!", icon="👍")
                                st.rerun()
                        if fb_cols[1].button("👎", key=f"dn_{chat_id}"):
                            if do_feedback(chat_id, -1):
                                st.session_state.feedback_given.add(chat_id)
                                st.toast("✅ Thanks for your feedback!", icon="👎")
                                st.rerun()

    # Chat input
    if prompt := st.chat_input("Ask a question about your company..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Searching documents and generating response..."):
                try:
                    result = do_chat(prompt)
                    if result.get("guardrail_triggered"):
                        st.markdown(f'<div class="guardrail-warning">{result["response"]}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(result["response"])

                    cols = st.columns([2, 2, 2, 2])
                    cols[0].caption(f"⚡ {result.get('latency_ms', 0):.0f}ms")
                    cols[1].caption(f"🤖 {result.get('model_used', '?')}")
                    cols[2].caption(f"🧠 {result.get('complexity', '?')}")
                    cols[3].caption(f"{'🎯 cached' if result.get('cache_hit') else '🔍 retrieved'}")

                    # Enhancement badges
                    if result.get("hyde_used") or result.get("rerank_used"):
                        badge_cols = st.columns([1, 1, 6])
                        if result.get("hyde_used"):
                            badge_cols[0].caption("💡 HyDE")
                        if result.get("rerank_used"):
                            badge_cols[1].caption("🏆 Reranked")

                    if result.get("sources"):
                        st.markdown("**📂 Sources:**")
                        for src in set(result["sources"]):
                            st.markdown(f'<span class="source-chip">📄 {src}</span>', unsafe_allow_html=True)

                    # HITL Feedback buttons for fresh response
                    chat_id = result.get("chat_id", "")
                    if chat_id and not result.get("guardrail_triggered"):
                        st.markdown("**Was this helpful?**")
                        fb_cols = st.columns([1, 1, 6])
                        if fb_cols[0].button("👍", key=f"up_new_{chat_id}"):
                            if do_feedback(chat_id, 1):
                                st.session_state.feedback_given.add(chat_id)
                                st.toast("✅ Thanks for your feedback!", icon="👍")
                        if fb_cols[1].button("👎", key=f"dn_new_{chat_id}"):
                            if do_feedback(chat_id, -1):
                                st.session_state.feedback_given.add(chat_id)
                                st.toast("✅ Thanks for your feedback!", icon="👎")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result["response"],
                        "meta": result,
                    })
                except Exception as e:
                    st.error(f"Error communicating with API: {e}")
