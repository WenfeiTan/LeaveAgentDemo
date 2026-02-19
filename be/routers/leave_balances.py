from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from be.config.db import get_session
from be.model.models import LeaveBalances
from be.model.schemas import LeaveBalancesResponse, LeaveBalanceItem

router = APIRouter(prefix="/leave-balances", tags=["leave-balances"])


@router.get("/{employee_id}", response_model=LeaveBalancesResponse)
def get_all_balances(employee_id: str, session: Session = Depends(get_session)):
    rows = session.exec(select(LeaveBalances).where(LeaveBalances.employee_id == employee_id)).all()
    if not rows:
        # demo 里宁愿 404，避免“没数据但看起来像 0”
        raise HTTPException(status_code=404, detail="No leave balances found for this employee")

    return LeaveBalancesResponse(
        employee_id=employee_id,
        balances=[
            LeaveBalanceItem(employee_id=r.employee_id, leave_type=r.leave_type, available_units=r.available_units)
            for r in rows
        ],
    )


@router.get("/{employee_id}/{leave_type}", response_model=LeaveBalanceItem)
def get_one_balance(employee_id: str, leave_type: str, session: Session = Depends(get_session)):
    row = session.exec(
        select(LeaveBalances).where(
            (LeaveBalances.employee_id == employee_id) & (LeaveBalances.leave_type == leave_type)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Leave balance not found")

    return LeaveBalanceItem(employee_id=row.employee_id, leave_type=row.leave_type, available_units=row.available_units)
