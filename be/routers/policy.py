from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from be.config.db import get_session
from be.model.schemas import PolicyIngestRequest, PolicyRetrieveRequest
from be.services.policy_rag import policy_rag_service

router = APIRouter(prefix="/policy", tags=["policy"])


@router.post("/ingest")
def ingest_policy(payload: PolicyIngestRequest, session: Session = Depends(get_session)):
    default_doc = Path(__file__).resolve().parents[1] / "policies" / "annual_leave_fte_cn_gz.md"
    doc_path = payload.doc_path or str(default_doc)

    try:
        return policy_rag_service.ingest_markdown(
            session=session,
            policy_group=payload.policy_group,
            doc_path=doc_path,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/retrieve")
def retrieve_policy(payload: PolicyRetrieveRequest, session: Session = Depends(get_session)):
    if payload.top_k <= 0 or payload.top_k > 10:
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 10")

    chunks = policy_rag_service.retrieve(
        session=session,
        policy_group=payload.policy_group,
        query=payload.query,
        top_k=payload.top_k,
    )

    if not chunks:
        raise HTTPException(status_code=404, detail="No policy chunks found for policy_group")

    return {
        "policy_group": payload.policy_group,
        "query": payload.query,
        "top_k": payload.top_k,
        "chunks": chunks,
    }
