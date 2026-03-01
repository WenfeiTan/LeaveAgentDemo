from __future__ import annotations

from pathlib import Path
import uuid
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import text
from sqlmodel import Session, select

from be.config.db import get_session
from be.model.models import PolicyAssets
from be.model.schemas import (
    PolicyAssetListRequest,
    PolicyAssetListResponse,
    PolicyAssetItem,
)

router = APIRouter(prefix="/policy-assets", tags=["policy-assets"])


def ensure_policy_assets_table(session: Session) -> None:
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS public.policy_assets (
                asset_id TEXT PRIMARY KEY,
                policy_group TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                mime_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                tags JSONB NOT NULL DEFAULT '[]'::jsonb,
                related_docs JSONB NOT NULL DEFAULT '[]'::jsonb,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_policy_assets_policy_group
            ON public.policy_assets(policy_group);
            """
        )
    )
    session.commit()


@router.post("/list", response_model=PolicyAssetListResponse)
def list_policy_assets(payload: PolicyAssetListRequest, session: Session = Depends(get_session)):
    ensure_policy_assets_table(session)
    rows = session.exec(
        select(PolicyAssets).where(
            (PolicyAssets.policy_group == payload.policy_group) & (PolicyAssets.is_active == True)  # noqa: E712
        )
    ).all()

    assets = [
        PolicyAssetItem(
            asset_id=r.asset_id,
            policy_group=r.policy_group,
            title=r.title,
            description=r.description or "",
            mime_type=r.mime_type,
            file_path=r.file_path,
            tags=[str(t) for t in (r.tags or [])],
            related_docs=[str(d) for d in (r.related_docs or [])],
            is_active=bool(r.is_active),
        )
        for r in rows
    ]

    return PolicyAssetListResponse(policy_group=payload.policy_group, assets=assets)


def _parse_list_field(raw: str | None) -> list[str]:
    if raw is None:
        return []
    v = raw.strip()
    if not v:
        return []
    # Try JSON array first.
    if v.startswith("[") and v.endswith("]"):
        try:
            arr = json.loads(v)
            if isinstance(arr, list):
                return [str(x).strip() for x in arr if str(x).strip()]
        except Exception:
            pass
    # Fallback to comma-separated.
    return [p.strip() for p in v.split(",") if p.strip()]


@router.post("/register", response_model=PolicyAssetItem)
async def register_policy_asset(
    session: Session = Depends(get_session),
    file: UploadFile = File(...),
    policy_group: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    mime_type: str | None = Form(None),
    tags: str | None = Form(None),
    related_docs: str | None = Form(None),
    is_active: bool = Form(True),
):
    ensure_policy_assets_table(session)
    project_root = Path(__file__).resolve().parents[2]
    assets_root = (project_root / "be" / "policies" / "assets").resolve()
    assets_root.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "").suffix
    stored_name = f"{uuid.uuid4().hex}{ext}"
    resolved_path = (assets_root / stored_name).resolve()
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    resolved_path.write_bytes(raw_bytes)

    parsed_tags = _parse_list_field(tags)
    parsed_related_docs = _parse_list_field(related_docs)
    final_mime_type = mime_type or (file.content_type or "application/octet-stream")

    row = PolicyAssets(
        asset_id=str(uuid.uuid4()),
        policy_group=policy_group,
        title=title,
        description=description,
        mime_type=final_mime_type,
        file_path=str(resolved_path),
        tags=parsed_tags,
        related_docs=parsed_related_docs,
        is_active=is_active,
    )
    session.add(row)

    session.commit()
    session.refresh(row)

    return PolicyAssetItem(
        asset_id=row.asset_id,
        policy_group=row.policy_group,
        title=row.title,
        description=row.description or "",
        mime_type=row.mime_type,
        file_path=row.file_path,
        tags=[str(t) for t in (row.tags or [])],
        related_docs=[str(d) for d in (row.related_docs or [])],
        is_active=bool(row.is_active),
    )
