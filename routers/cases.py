from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from config.db import get_session
from model.models import Cases, Employees
from model.schemas import CaseCreateRequest, CasePatchRequest, CaseResponse, ALLOWED_CASE_STATUS

router = APIRouter(prefix="/cases", tags=["cases"])


def to_case_response(c: Cases) -> CaseResponse:
    return CaseResponse(
        case_id=c.case_id,
        requester_id=c.requester_id,
        case_type=c.case_type,
        status=c.status,
        payload_json=c.payload_json,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


@router.post("", response_model=CaseResponse)
def create_case(payload: CaseCreateRequest, session: Session = Depends(get_session)):
    # requester 必须存在（避免脏数据）
    requester = session.exec(select(Employees).where(Employees.employee_id == payload.requester_id)).first()
    if not requester:
        raise HTTPException(status_code=400, detail="requester_id does not exist")

    c = Cases(
        requester_id=payload.requester_id,
        case_type=payload.case_type,
        status="DRAFT",
        payload_json=payload.payload_json or {},
    )
    session.add(c)
    session.commit()
    session.refresh(c)
    return to_case_response(c)


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: int, session: Session = Depends(get_session)):
    c = session.get(Cases, case_id)
    if not c:
        raise HTTPException(status_code=404, detail="Case not found")
    return to_case_response(c)


@router.get("", response_model=list[CaseResponse])
def list_cases(
    requester_id: str = Query(..., description="employee_id of requester"),
    session: Session = Depends(get_session),
):
    rows = session.exec(select(Cases).where(Cases.requester_id == requester_id).order_by(Cases.created_at.desc())).all()
    return [to_case_response(r) for r in rows]


@router.patch("/{case_id}", response_model=CaseResponse)
def patch_case(case_id: str, patch: CasePatchRequest, session: Session = Depends(get_session)):
    c = session.get(Cases, case_id)
    if not c:
        raise HTTPException(status_code=404, detail="Case not found")

    if patch.status is not None:
        if patch.status not in ALLOWED_CASE_STATUS:
            raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {sorted(ALLOWED_CASE_STATUS)}")
        c.status = patch.status

    if patch.payload_json is not None:
        c.payload_json = patch.payload_json

    # updated_at 由 DB onupdate 处理；但为了 demo 直观，也可以手动 touch
    c.updated_at = datetime.utcnow()

    session.add(c)
    session.commit()
    session.refresh(c)
    return to_case_response(c)
