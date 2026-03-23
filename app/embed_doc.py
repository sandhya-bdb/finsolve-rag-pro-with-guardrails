"""
embed_doc.py — Document ingestion pipeline (production version).

Loads department PDFs/MD/CSV, chunks them, stores embeddings in Chroma,
and logs chunk metadata to DuckDB.
"""

import os
import shutil
import uuid
import sys

sys.path.insert(0, os.path.dirname(__file__))

from langchain_community.document_loaders import (
    UnstructuredFileLoader, CSVLoader, TextLoader, PyPDFLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from db import init_db, log_doc_chunk
from services.semantic_cache import semantic_cache

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
BASE_DIR  = os.environ.get("DATA_DIR", "../resources/data")
CHROMA_DIR = os.environ.get("CHROMA_DIR", "chroma_db")
COLLECTION = "company_docs"

init_db()
embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Clear existing Chroma DB + semantic cache
shutil.rmtree(CHROMA_DIR, ignore_errors=True)
semantic_cache.invalidate()
print("♻️  Cleared old Chroma DB and semantic cache.")

all_split_docs = []

# ─────────────────────────────────────────────
# Process each department folder
# ─────────────────────────────────────────────
for department in os.listdir(BASE_DIR):
    dept_path = os.path.join(BASE_DIR, department)
    if not os.path.isdir(dept_path):
        continue

    print(f"\n🔍 Processing department: {department}")
    dept_docs = []

    for fname in os.listdir(dept_path):
        file_path = os.path.join(dept_path, fname)
        if not os.path.isfile(file_path):
            continue

        try:
            if fname.endswith((".md", ".txt")):
                try:
                    loader = UnstructuredFileLoader(file_path)
                    docs = loader.load()
                except Exception:
                    loader = TextLoader(file_path, encoding="utf-8")
                    docs = loader.load()
            elif fname.endswith(".csv"):
                loader = CSVLoader(file_path)
                docs = loader.load()
            elif fname.endswith(".pdf"):
                loader = PyPDFLoader(file_path)
                docs = loader.load()
            else:
                continue

            for d in docs:
                d.metadata["file_name"]  = fname
                d.metadata["role"]       = department.lower()
                d.metadata["department"] = department.lower()
                d.metadata["source"]     = fname

            dept_docs.extend(docs)
            print(f"  ✅ Loaded: {fname} ({len(docs)} pages/chunks)")

        except Exception as e:
            print(f"  ❌ Failed: {file_path}: {e}")

    if not dept_docs:
        print(f"  ⚠️  No documents for: {department}")
        continue

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    split_docs = splitter.split_documents(dept_docs)

    for doc in split_docs:
        chunk_id = str(uuid.uuid4())
        doc.metadata["chunk_id"] = chunk_id
        log_doc_chunk(
            chunk_id=chunk_id,
            file_name=doc.metadata.get("file_name", "unknown"),
            role=doc.metadata.get("role", department.lower()),
            department=doc.metadata.get("department", department.lower()),
            source=doc.metadata.get("source", "unknown"),
        )

    all_split_docs.extend(split_docs)
    print(f"  📦 Created {len(split_docs)} chunks for {department}")

# ─────────────────────────────────────────────
# Store in Chroma
# ─────────────────────────────────────────────
vectordb = Chroma.from_documents(
    documents=all_split_docs,
    embedding=embedding_function,
    persist_directory=CHROMA_DIR,
    collection_name=COLLECTION,
)

print(f"\n🎉 Stored {len(all_split_docs)} chunks in Chroma DB at '{CHROMA_DIR}'.")
print("📌 Remember to restart the API server after re-ingestion.")
