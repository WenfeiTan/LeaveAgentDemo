from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from config.db import get_session
from model.models import Employees
from model.schemas import DirectoryResponse, PersonProfile

router = APIRouter(prefix="/directory", tags=["directory"])


def to_profile(e: Employees) -> PersonProfile:
    return PersonProfile(
        employee_id=e.employee_id,
        name=e.name,
        email=e.email,
        employment_type=e.employment_type,
        location=e.location,
        department=e.department,
        grade=e.grade,
        leave_policy_group=e.leave_policy_group,
        manager_id=e.manager_id,
    )


@router.get("/by-email/{email}", response_model=DirectoryResponse)
def get_by_email(email: str, session: Session = Depends(get_session)):
    emp = session.exec(select(Employees).where(Employees.email == email)).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    manager_profile = None
    if emp.manager_id:
        mgr = session.exec(select(Employees).where(Employees.employee_id == emp.manager_id)).first()
        if mgr:
            manager_profile = to_profile(mgr)

    return DirectoryResponse(employee_profile=to_profile(emp), manager_profile=manager_profile)


@router.get("/by-id/{employee_id}", response_model=DirectoryResponse)
def get_by_id(employee_id: str, session: Session = Depends(get_session)):
    emp = session.exec(select(Employees).where(Employees.employee_id == employee_id)).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    manager_profile = None
    if emp.manager_id:
        mgr = session.exec(select(Employees).where(Employees.employee_id == emp.manager_id)).first()
        if mgr:
            manager_profile = to_profile(mgr)

    return DirectoryResponse(employee_profile=to_profile(emp), manager_profile=manager_profile)
