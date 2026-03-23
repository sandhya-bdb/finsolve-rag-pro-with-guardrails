# FinSolve RAG Pro

FinSolve RAG Pro is a modular enterprise RAG assistant built with FastAPI, Streamlit, ChromaDB, and DuckDB. The project is designed for internal knowledge retrieval where security, role-aware access, observability, and controlled model usage matter just as much as answer quality.

It combines retrieval, guardrails, semantic caching, feedback tracking, and evaluation into one repo that is practical for demos, internal pilots, and future production hardening.

## Highlights

- Role-based retrieval with metadata filtering over Chroma
- Guardrails for prompt injection, PII, and out-of-scope requests
- Provider-aware LLM routing with Groq as the default and Ollama as an optional local backend
- HyDE retrieval and cross-encoder reranking for better context selection
- JWT authentication and chat audit logging
- DuckDB-backed metrics, guardrail logs, and human feedback capture
- Streamlit chat UI and monitoring dashboard
- Local test suite plus CI-friendly evaluation smoke test

## Why This Project Exists

Typical RAG demos focus on retrieval and answer generation only. In real internal tooling, that is not enough. Teams also need:

- Access control so each employee only sees the documents they are allowed to access
- Guardrails so the assistant can reject unsafe or irrelevant inputs
- Cost and latency visibility so the team can understand operational behavior
- Evaluation so changes can be checked before deployment
- A clean path between cloud-hosted inference and local inference

This repository is structured around those practical needs.

## Recommended Model Strategy

Use **Groq as the default provider** and keep **Ollama as an optional fallback**.

Why Groq should be the default:

- Easier onboarding for contributors because they do not need to download local models first
- Cleaner GitHub story for demos, CI, and quick testing
- Better fit for a repo that other people may clone and try immediately

Why keep Ollama support:

- Useful for local-only experimentation
- Helpful when you want lower-cost or offline-style iteration
- Lets the same app architecture support both hosted and local inference

Provider switching is controlled through one environment variable:

```bash
LLM_PROVIDER=groq
```

or

```bash
LLM_PROVIDER=ollama
```

## System Architecture

```text
Streamlit Chat UI (8501)
        |
        v
FastAPI Backend (8000)
        |
        +--> JWT Authentication
        +--> Input Guardrails
        +--> Semantic Cache
        +--> Model Router
        +--> HyDE Query Expansion
        +--> Chroma Retrieval with RBAC
        +--> Cross-Encoder Reranking
        +--> Groq or Ollama Generation
        +--> Output Guardrails
        +--> DuckDB Logging + Metrics

Streamlit Monitoring Dashboard (8502)
        |
        v
Reads DuckDB metrics, guardrail events, and recent chat activity
```

## Repository Layout

```text
Finsolve RAG Pro/
├── app/
│   ├── main.py
│   ├── UI.py
│   ├── embed_doc.py
│   ├── db.py
│   ├── guardrails/
│   │   ├── guardrails_manager.py
│   │   ├── injection_detector.py
│   │   ├── pii_detector.py
│   │   └── scope_filter.py
│   ├── monitoring/
│   │   ├── dashboard.py
│   │   └── metrics.py
│   └── services/
│       ├── hyde_retriever.py
│       ├── llm_provider.py
│       ├── model_router.py
│       ├── rbac.py
│       ├── reranker.py
│       └── semantic_cache.py
├── eval/
│   ├── eval_dataset.py
│   ├── ragas_eval.py
│   ├── run_evaluation.py
│   └── results/
├── resources/
│   └── data/
├── tests/
├── .github/workflows/
├── .env.example
├── requirements_prod.txt
└── README.md
```

## Core Modules

### `app/main.py`
The main FastAPI application. It handles login, chat, feedback, health, and metrics summary routes. It also orchestrates the full RAG pipeline.

### `app/services/llm_provider.py`
Unified provider layer for text generation. This module abstracts Groq and Ollama behind one interface so the rest of the codebase does not need provider-specific branching everywhere.

### `app/services/model_router.py`
Selects the appropriate model based on query complexity, user role, and configured provider.

### `app/services/hyde_retriever.py`
Creates a short hypothetical passage to improve retrieval recall before vector search.

### `app/services/reranker.py`
Reorders retrieved candidate chunks with a cross-encoder so the final context passed to the answer model is more relevant.

### `app/services/rbac.py`
Encodes role hierarchy and retrieval permissions used for metadata filtering in Chroma.

### `app/guardrails/`
Contains the security and product-boundary checks used before and after generation.

### `app/db.py`
Stores chat logs, chunk metadata, metrics, guardrail events, and user feedback in DuckDB.

### `app/monitoring/dashboard.py`
Provides a local monitoring dashboard for latency, model usage, cache hits, and guardrail activity.

## Supported Roles

The app currently ships with demo roles for local testing:

- `c-levelexecutives`
- `finance`
- `hr`
- `engineering`
- `marketing`
- `employee`

These are implemented for demo purposes and should be replaced by a real identity system before production deployment.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements_prod.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

### 3. Choose your provider

For Groq:

```bash
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
```

For Ollama:

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

### 4. Optional: pull local models for Ollama

Only needed when `LLM_PROVIDER=ollama`.

```bash
ollama pull llama3.2:1b
ollama pull llama3.2
ollama pull mistral
```

### 5. Add company documents

Create department folders under `resources/data/` and place documents there.

```text
resources/data/
├── finance/
├── hr/
├── engineering/
├── marketing/
└── general/
```

### 6. Ingest documents

```bash
cd app
python embed_doc.py
```

### 7. Start the backend

```bash
cd app
uvicorn main:app --reload --port 8000
```

### 8. Start the chat UI

```bash
cd app
streamlit run UI.py --server.port 8501
```

### 9. Start the monitoring dashboard

```bash
cd app
streamlit run monitoring/dashboard.py --server.port 8502
```

## Demo Credentials

| Username | Password | Role |
|---|---|---|
| `sandhya` | `ceopass` | c-levelexecutives |
| `Binoy` | `financepass` | finance |
| `sangit` | `hrpass123` | hr |
| `Deb` | `password123` | engineering |
| `Ved` | `securepass` | marketing |
| `Karabi` | `employeepass` | employee |

## Testing

Run the full local suite:

```bash
python -m pytest tests -v -p no:cacheprovider
```

Current local verification status for this snapshot:

- `pytest`: passing
- `ruff check`: passing
- dry-run evaluation: passing

## Evaluation

### Dry-run evaluation

This checks the evaluation pipeline itself and is suitable for CI smoke testing.

```bash
python eval/run_evaluation.py --threshold 0.3
```

### Live evaluation

This is the more meaningful evaluation mode. It calls the running API and should be used once the app is configured with a real provider and ingested documents.

```bash
python eval/run_evaluation.py --live --token <your_jwt> --threshold 0.5
```

The report is saved to `eval/results/latest_eval.json`.

## API Endpoints

Main routes include:

- `POST /login`
- `POST /chat`
- `POST /feedback`
- `GET /feedback/summary`
- `GET /metrics/summary`
- `GET /health`

## Environment Variables

The most important variables are:

- `SECRET_KEY`
- `TOKEN_EXPIRE_MINUTES`
- `LLM_PROVIDER`
- `GROQ_API_KEY`
- `OLLAMA_BASE_URL`
- `MODEL_SIMPLE`
- `MODEL_MODERATE`
- `MODEL_COMPLEX`
- `HYDE_MODEL`
- `HYDE_ENABLED`
- `RERANK_ENABLED`
- `CHROMA_DIR`
- `DUCKDB_PATH`
- `DATA_DIR`
- `API_BASE_URL`

See `.env.example` for the full template.

## CI

GitHub Actions is configured to run:

- test suite
- evaluation smoke test
- lint checks

Workflow file:

- `.github/workflows/eval_ci.yml`

## Publish Checklist

Before pushing publicly later, make sure to:

- keep `.env` out of version control
- avoid committing real internal documents
- rotate any demo secrets you may have used locally
- replace hardcoded demo authentication with a real identity provider
- review CORS and transport security for deployment

## Security Notes

This project is structured with security-aware features, but it is still a development-stage repository. Before production use, consider:

- replacing demo users with real auth
- hardening token handling and secret management
- tightening CORS
- adding HTTPS and deployment security controls
- reviewing guardrail policy against your actual internal use cases

## Roadmap Ideas

Natural next improvements include:

- hybrid retrieval
- reranker score observability
- real user management
- streaming responses
- richer offline evals against real document sets
- automated feedback review loops
