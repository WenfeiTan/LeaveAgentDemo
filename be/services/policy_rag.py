from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Any

from sqlalchemy import text, bindparam
from sqlmodel import Session
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from be.model.models import VectorType

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 3072


class PolicyRagService:
    def __init__(self) -> None:
        self._emb: GoogleGenerativeAIEmbeddings | None = None

    def _get_embeddings(self) -> GoogleGenerativeAIEmbeddings:
        if self._emb is None:
            self._emb = GoogleGenerativeAIEmbeddings(
                model=EMBED_MODEL,
                api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
            )
        return self._emb

    @staticmethod
    def _chunk_text(content: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        normalized = "\n".join(line.rstrip() for line in content.splitlines()).strip()
        chunks: List[str] = []
        start = 0
        while start < len(normalized):
            end = min(start + chunk_size, len(normalized))
            chunks.append(normalized[start:end])
            if end >= len(normalized):
                break
            start = max(end - overlap, start + 1)
        return [c for c in chunks if c.strip()]

    @staticmethod
    def ensure_table(session: Session) -> None:
        session.exec(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        session.exec(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS public.policy_chunks (
                    chunk_id SERIAL PRIMARY KEY,
                    policy_group TEXT NOT NULL,
                    doc_name TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR({EMBED_DIM}) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
        )
        session.exec(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_policy_chunks_policy_group
                ON public.policy_chunks(policy_group);
                """
            )
        )
        if EMBED_DIM <= 2000:
            session.exec(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_policy_chunks_embedding
                    ON public.policy_chunks USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 50);
                    """
                )
            )
        session.commit()

    def ingest_markdown(self, session: Session, policy_group: str, doc_path: str) -> Dict[str, Any]:
        self.ensure_table(session)

        md_path = Path(doc_path)
        if not md_path.exists():
            raise FileNotFoundError(f"Policy document not found: {doc_path}")

        content = md_path.read_text(encoding="utf-8")
        chunks = self._chunk_text(content)
        vectors = self._get_embeddings().embed_documents(chunks)

        session.execute(
            text("DELETE FROM public.policy_chunks WHERE policy_group = :policy_group AND doc_name = :doc_name"),
            {"policy_group": policy_group, "doc_name": md_path.name},
        )

        insert_stmt = text(
            """
            INSERT INTO public.policy_chunks(policy_group, doc_name, chunk_index, content, embedding)
            VALUES (:policy_group, :doc_name, :chunk_index, :content, :embedding);
            """
        ).bindparams(bindparam("embedding", type_=VectorType(EMBED_DIM)))

        for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
            session.execute(
                insert_stmt,
                {
                    "policy_group": policy_group,
                    "doc_name": md_path.name,
                    "chunk_index": idx,
                    "content": chunk,
                    "embedding": vec,
                },
            )

        session.commit()
        return {
            "policy_group": policy_group,
            "doc_name": md_path.name,
            "chunks": len(chunks),
        }

    def retrieve(self, session: Session, policy_group: str, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        self.ensure_table(session)

        q_vec = self._get_embeddings().embed_query(query)

        retrieve_stmt = text(
            """
            SELECT
                chunk_id,
                doc_name,
                chunk_index,
                content,
                1 - (embedding <=> :qvec) AS score
            FROM public.policy_chunks
            WHERE policy_group = :policy_group
            ORDER BY embedding <=> :qvec
            LIMIT :top_k;
            """
        ).bindparams(bindparam("qvec", type_=VectorType(EMBED_DIM)))

        rows = session.execute(
            retrieve_stmt,
            {"policy_group": policy_group, "qvec": q_vec, "top_k": top_k},
        ).all()

        return [
            {
                "chunk_id": r[0],
                "doc_name": r[1],
                "chunk_index": r[2],
                "content": r[3],
                "score": float(r[4]) if r[4] is not None else 0.0,
            }
            for r in rows
        ]


policy_rag_service = PolicyRagService()
