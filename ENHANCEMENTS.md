# FinSolve RAG Pro: Advanced Enhancements

FinSolve RAG Pro builds upon basic RAG architectures by integrating enterprise-grade features for security, retrieval precision, and operational observability. Below is a summary of the key enhancements.

---

## 1. Multi-Stage Guardrails Pipeline
The `GuardrailsManager` implements a defensive "fast-fail" pipeline for both inputs and outputs:
- **Injection Detection**: Uses heuristic patterns to block prompt injection (e.g., "ignore previous instructions") and jailbreak attempts.
- **PII Protection**: Automatically detects and redacts Sensitive Personal Information (SSN, emails, credit cards) using regex-based scanners.
- **Scope Filtering**: Ensures the assistant only responds to queries within the enterprise domain (Finance, HR, Engineering, etc.), preventing "out-of-scope" usage.

## 2. Advanced Retrieval Strategy
To overcome the limitations of simple semantic search, we've implemented:
- **HyDE (Hypothetical Document Embeddings)**: The system generates a "fake" answer first and uses it for retrieval, which often leads to better document matches than the raw user query.
- **Cross-Encoder Reranking**: After getting the initial results from ChromaDB, a reranker re-evaluates the top-K chunks to ensure the most relevant context is passed to the LLM.
- **RBAC (Role-Based Access Control)**: Every document is tagged with department and role metadata. Retrieval is automatically filtered based on the authenticated user's role (e.g., an "hr" user cannot retrieve "finance" documents).

## 3. Intelligent Model Routing
The `model_router` dynamically selects the best LLM for the task:
- **Complexity Classification**: Queries are classified as *Simple*, *Moderate*, or *Complex* based on custom keywords and length.
- **Provider Abstraction**: Supports both **Groq** (for high-speed cloud inference) and **Ollama** (for local/offline iteration), switchable via a single environment variable.

## 4. Production Observability & Persistence
Unlike stateless demos, this project maintains a permanent audit trail:
- **DuckDB Integration**: A high-performance local database stores chat logs, performance metrics (latency, tokens, cost), and guardrail events.
- **Monitoring Dashboard**: A dedicated Streamlit interface visualizes operational health, including satisfaction trends and cache efficiency.
- **Semantic Caching**: Frequently asked questions are answered from a vector-based cache, drastically reducing latency and API costs.

## 5. Human-in-the-Loop (HITL) Feedback
Every chat response includes a feedback mechanism (thumbs up/down). This data is captured in DuckDB and summarized in the dashboard to guide future model tuning and evaluation.

---

## 6. Comprehensive Evaluation
Equipped with a **RAGAS-based evaluation pipeline**, the project allows for automated quality testing (faithfulness, relevancy, etc.) before any deployment, ensuring that updates don't degrade the assistant's performance.
