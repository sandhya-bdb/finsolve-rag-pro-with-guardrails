"""
main.py - FinSolve RAG Pro FastAPI backend.

Features integrated:
  - JWT authentication
  - RBAC retrieval over Chroma
  - Guardrails pipeline
  - Semantic cache
  - Provider-aware model routing (Groq or Ollama)
  - HyDE and cross-encoder reranking
  - Feedback logging and monitoring
"""

import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from passlib.context import CryptContext
from pydantic import BaseModel

from db import (
    get_feedback_summary,
    init_db,
    log_chat,
    log_feedback,
    log_guardrail_event,
    log_metrics,
)
from guardrails.guardrails_manager import guardrails
from monitoring.metrics import QueryMetrics, calculate_cost, estimate_tokens, timer
from services.hyde_retriever import generate_hypothesis
from services.llm_provider import generate_text, get_provider_health
from services.model_router import route_query
from services.rbac import get_chroma_filter
from services.reranker import rerank
from services.semantic_cache import semantic_cache

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s"}',
)
logger = logging.getLogger("finsolve")

SECRET_KEY = os.environ.get("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_USE_STRONG_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("TOKEN_EXPIRE_MINUTES", "60"))
CHROMA_DIR = os.environ.get("CHROMA_DIR", "chroma_db")
HYDE_ENABLED = os.environ.get("HYDE_ENABLED", "true").lower() == "true"
RERANK_ENABLED = os.environ.get("RERANK_ENABLED", "true").lower() == "true"
HYDE_CANDIDATES = int(os.environ.get("HYDE_CANDIDATES", "8"))
RERANK_TOP_K = int(os.environ.get("RERANK_TOP_K", "4"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

USERS_DB: Dict[str, Dict] = {
    "Deb": {"hashed_password": pwd_context.hash("password123"), "role": "engineering"},
    "Ved": {"hashed_password": pwd_context.hash("securepass"), "role": "marketing"},
    "Binoy": {"hashed_password": pwd_context.hash("financepass"), "role": "finance"},
    "sangit": {"hashed_password": pwd_context.hash("hrpass123"), "role": "hr"},
    "sandhya": {"hashed_password": pwd_context.hash("ceopass"), "role": "c-levelexecutives"},
    "Karabi": {"hashed_password": pwd_context.hash("employeepass"), "role": "employee"},
}

app = FastAPI(
    title="FinSolve RAG Pro",
    description=(
        "Enterprise RAG assistant with RBAC, guardrails, monitoring, and "
        "provider-aware LLM routing for Groq and Ollama."
    ),
    version="3.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

init_db()
embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectordb = Chroma(
    persist_directory=CHROMA_DIR,
    embedding_function=embedding_function,
    collection_name="company_docs",
)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    user = USERS_DB.get(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return {"username": username, "role": user["role"]}


def create_access_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({**data, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc
    return {"username": username, "role": role}


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    chat_id: str
    username: str
    role: str
    query: str
    response: str
    sources: list
    model_used: str
    complexity: str
    latency_ms: float
    cache_hit: bool
    guardrail_triggered: bool
    hyde_used: bool
    rerank_used: bool


class FeedbackRequest(BaseModel):
    chat_id: str
    rating: Literal[1, -1]
    comment: str = ""


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "3.1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "hyde_enabled": HYDE_ENABLED,
            "rerank_enabled": RERANK_ENABLED,
            **get_provider_health(),
        },
    }


@app.get("/metrics/summary")
def metrics_summary(current_user: Dict = Depends(get_current_user)):
    from db import get_metrics_summary

    return get_metrics_summary(hours=24)


@app.post("/feedback", status_code=200)
def submit_feedback(req: FeedbackRequest, current_user: Dict = Depends(get_current_user)):
    username = current_user["username"]
    role = current_user["role"]
    try:
        log_feedback(
            chat_id=req.chat_id,
            username=username,
            role=role,
            rating=req.rating,
            comment=req.comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info("Feedback: user=%s chat_id=%s rating=%s", username, req.chat_id, req.rating)
    return {"status": "recorded", "chat_id": req.chat_id, "rating": req.rating}


@app.get("/feedback/summary")
def feedback_summary(hours: int = 24, current_user: Dict = Depends(get_current_user)):
    return get_feedback_summary(hours=hours)


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    token = create_access_token({"sub": user["username"], "role": user["role"]})
    logger.info("Login: user=%s role=%s", user["username"], user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"],
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, current_user: Dict = Depends(get_current_user)):
    chat_id = str(uuid.uuid4())
    username = current_user["username"]
    role = current_user["role"]
    message = req.message
    metrics = QueryMetrics()
    hyde_used = False
    rerank_used = False

    with timer() as t:
        guard_result = guardrails.check_input(message, role)
        if not guard_result.passed:
            metrics.guardrail_triggered = True
            metrics.latency_ms = t["ms"]
            log_guardrail_event(username, role, guard_result.block_type, guard_result.blocked_reason, message)
            log_metrics(
                username=username,
                role=role,
                model_used="none",
                complexity="blocked",
                latency_ms=metrics.latency_ms,
                tokens_used=0,
                cost_usd=0.0,
                cache_hit=False,
                guardrail_triggered=True,
                guardrail_reason=guard_result.blocked_reason,
            )
            return ChatResponse(
                chat_id=chat_id,
                username=username,
                role=role,
                query=message,
                response=f"Warning: {guard_result.blocked_reason}",
                sources=[],
                model_used="none",
                complexity="blocked",
                latency_ms=metrics.latency_ms,
                cache_hit=False,
                guardrail_triggered=True,
                hyde_used=False,
                rerank_used=False,
            )

        safe_query = guard_result.sanitized_input or message
        query_embedding = embedding_function.embed_query(safe_query)
        cached = semantic_cache.get(safe_query, query_embedding)
        if cached:
            metrics.cache_hit = True
            metrics.model_used = cached.model_used
            metrics.latency_ms = t["ms"]
            log_metrics(
                username=username,
                role=role,
                model_used=cached.model_used,
                complexity="cached",
                latency_ms=metrics.latency_ms,
                tokens_used=0,
                cost_usd=0.0,
                cache_hit=True,
                guardrail_triggered=False,
            )
            logger.info("Cache hit: user=%s query_len=%s", username, len(safe_query))
            return ChatResponse(
                chat_id=chat_id,
                username=username,
                role=role,
                query=message,
                response=cached.response,
                sources=cached.sources,
                model_used=cached.model_used,
                complexity="cached",
                latency_ms=metrics.latency_ms,
                cache_hit=True,
                guardrail_triggered=False,
                hyde_used=False,
                rerank_used=False,
            )

        model_config = route_query(safe_query, role)
        metrics.model_used = model_config.model_name
        metrics.complexity = model_config.complexity.value
        logger.info(
            "Routing: user=%s role=%s complexity=%s provider=%s model=%s",
            username,
            role,
            metrics.complexity,
            model_config.provider,
            metrics.model_used,
        )

        retrieval_query = safe_query
        if HYDE_ENABLED:
            hypothesis = generate_hypothesis(query=safe_query, provider=model_config.provider)
            if hypothesis != safe_query:
                retrieval_query = hypothesis
                hyde_used = True
                logger.info("HyDE active: user=%s hypothesis_len=%s", username, len(hypothesis))

        retrieval_embedding = (
            embedding_function.embed_query(retrieval_query) if hyde_used else query_embedding
        )

        chroma_filter = get_chroma_filter(role)
        k_candidates = HYDE_CANDIDATES if RERANK_ENABLED else RERANK_TOP_K
        if chroma_filter:
            docs = vectordb.similarity_search_by_vector(retrieval_embedding, k=k_candidates, filter=chroma_filter)
        else:
            docs = vectordb.similarity_search_by_vector(retrieval_embedding, k=k_candidates)

        if not docs:
            return ChatResponse(
                chat_id=chat_id,
                username=username,
                role=role,
                query=message,
                response="No relevant documents found for your role and query.",
                sources=[],
                model_used=metrics.model_used,
                complexity=metrics.complexity,
                latency_ms=round(t["ms"], 2),
                cache_hit=False,
                guardrail_triggered=False,
                hyde_used=hyde_used,
                rerank_used=False,
            )

        if RERANK_ENABLED and len(docs) > RERANK_TOP_K:
            docs = rerank(safe_query, docs, top_k=RERANK_TOP_K)
            rerank_used = True
            logger.info("Reranking: user=%s top_k=%s", username, RERANK_TOP_K)
        else:
            docs = docs[:RERANK_TOP_K]

        context = "\n\n-----\n\n".join(d.page_content for d in docs)
        prompt = f"""You are FinSolve-AI, an enterprise assistant for FinSolve company.
Your task is to give long, detailed, well-structured answers using ONLY the context provided.

Instructions:
- Provide a clear, multi-paragraph answer.
- Include explanations, examples, and reasoning steps when the context supports them.
- Never guess beyond the provided context.
- Write in a professional, easy-to-understand tone.
- Minimum length: 6-10 sentences.

User Role: {role}

Context:
{context}

Question:
{safe_query}

Final Answer:"""

        try:
            llm_answer = generate_text(
                prompt=prompt,
                model=metrics.model_used,
                provider=model_config.provider,
                temperature=0.2,
                max_tokens=2048,
                timeout=60,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"LLM service error: {exc}") from exc

        tokens_used = estimate_tokens(prompt + llm_answer)
        out_guard = guardrails.check_output(llm_answer)
        final_answer = out_guard.sanitized_input or llm_answer
        if out_guard.block_type == "OUTPUT_PII":
            logger.warning("Output PII redacted for user=%s reason=%s", username, out_guard.blocked_reason)

    metrics.latency_ms = round(t["ms"], 2)
    metrics.tokens_used = tokens_used
    metrics.cost_usd = calculate_cost(tokens_used, metrics.model_used)

    sources_list = [d.metadata.get("source", "unknown") for d in docs]
    chunk_ids = [d.metadata.get("chunk_id", "") for d in docs]

    log_chat(
        username=username,
        role=role,
        query=message,
        chunk_ids=chunk_ids,
        answer_text=final_answer,
        model_used=metrics.model_used,
        latency_ms=metrics.latency_ms,
    )
    log_metrics(
        username=username,
        role=role,
        model_used=metrics.model_used,
        complexity=metrics.complexity,
        latency_ms=metrics.latency_ms,
        tokens_used=metrics.tokens_used,
        cost_usd=metrics.cost_usd,
        cache_hit=False,
        guardrail_triggered=False,
    )

    semantic_cache.put(safe_query, query_embedding, final_answer, sources_list, metrics.model_used)

    logger.info(
        "Chat: user=%s role=%s model=%s latency=%sms tokens=%s hyde=%s rerank=%s",
        username,
        role,
        metrics.model_used,
        metrics.latency_ms,
        tokens_used,
        hyde_used,
        rerank_used,
    )

    return ChatResponse(
        chat_id=chat_id,
        username=username,
        role=role,
        query=message,
        response=final_answer,
        sources=sources_list,
        model_used=metrics.model_used,
        complexity=metrics.complexity,
        latency_ms=metrics.latency_ms,
        cache_hit=False,
        guardrail_triggered=False,
        hyde_used=hyde_used,
        rerank_used=rerank_used,
    )
