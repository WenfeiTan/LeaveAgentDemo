from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from sqlalchemy import text
from sqlmodel import Session

THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[2]
BE_ROOT = THIS_FILE.parents[1]
for p in (str(PROJECT_ROOT), str(BE_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from be.config.db import engine


POLICY_GROUP = "FTE_CN_GZ"
LOCATION = "Guangzhou"


EMPLOYEES: List[Dict[str, str | None]] = [
    {
        "employee_id": "EMP9000",
        "name": "LiJun",
        "email": "lijun@company.com",
        "employment_type": "FTE",
        "location": LOCATION,
        "department": "DataTech",
        "grade": "Director",
        "leave_policy_group": POLICY_GROUP,
        "manager_id": None,
    },
    {
        "employee_id": "EMP9100",
        "name": "ZhaoPeng",
        "email": "zhaopeng@company.com",
        "employment_type": "FTE",
        "location": LOCATION,
        "department": "DataTech",
        "grade": "M2",
        "leave_policy_group": POLICY_GROUP,
        "manager_id": "EMP9000",
    },
    {
        "employee_id": "EMP9101",
        "name": "XiaoMing",
        "email": "xiaoming@company.com",
        "employment_type": "FTE",
        "location": LOCATION,
        "department": "DataTech",
        "grade": "IC2",
        "leave_policy_group": POLICY_GROUP,
        "manager_id": "EMP9100",
    },
    {
        "employee_id": "EMP9102",
        "name": "NancyFu",
        "email": "nancyfu@company.com",
        "employment_type": "FTE",
        "location": LOCATION,
        "department": "DataTech",
        "grade": "IC1",
        "leave_policy_group": POLICY_GROUP,
        "manager_id": "EMP9101",
    },
    {
        "employee_id": "EMP9110",
        "name": "HeRui",
        "email": "herui@company.com",
        "employment_type": "FTE",
        "location": LOCATION,
        "department": "DataTech",
        "grade": "HRBP",
        "leave_policy_group": POLICY_GROUP,
        "manager_id": "EMP9100",
    },
    {
        "employee_id": "EMP9200",
        "name": "WangMin",
        "email": "wangmin@company.com",
        "employment_type": "FTE",
        "location": LOCATION,
        "department": "Admin",
        "grade": "M1",
        "leave_policy_group": POLICY_GROUP,
        "manager_id": "EMP9000",
    },
    {
        "employee_id": "EMP9201",
        "name": "LiuXin",
        "email": "liuxin@company.com",
        "employment_type": "FTE",
        "location": LOCATION,
        "department": "Admin",
        "grade": "IC2",
        "leave_policy_group": POLICY_GROUP,
        "manager_id": "EMP9200",
    },
    {
        "employee_id": "EMP9210",
        "name": "SunQing",
        "email": "sunqing@company.com",
        "employment_type": "FTE",
        "location": LOCATION,
        "department": "Admin",
        "grade": "HRBP",
        "leave_policy_group": POLICY_GROUP,
        "manager_id": "EMP9200",
    },
    {
        "employee_id": "EMP9250",
        "name": "GaoLin",
        "email": "gaolin@company.com",
        "employment_type": "FTE",
        "location": LOCATION,
        "department": "Finance",
        "grade": "M1",
        "leave_policy_group": POLICY_GROUP,
        "manager_id": "EMP9000",
    },
    {
        "employee_id": "EMP9251",
        "name": "XuTao",
        "email": "xutao@company.com",
        "employment_type": "FTE",
        "location": LOCATION,
        "department": "Finance",
        "grade": "IC2",
        "leave_policy_group": POLICY_GROUP,
        "manager_id": "EMP9250",
    },
    {
        "employee_id": "EMP9260",
        "name": "ZhouYi",
        "email": "zhouyi@company.com",
        "employment_type": "FTE",
        "location": LOCATION,
        "department": "Finance",
        "grade": "HRBP",
        "leave_policy_group": POLICY_GROUP,
        "manager_id": "EMP9250",
    },
]


BENEFIT_BY_GRADE: Dict[str, Tuple[float, float]] = {
    "IC1": (10.0, 5.0),
    "IC2": (12.0, 6.0),
    "IC3": (14.0, 7.0),
    "M1": (16.0, 8.0),
    "M2": (18.0, 10.0),
    "Director": (20.0, 12.0),
    "HRBP": (15.0, 8.0),
}


def reset_demo_rows(session: Session) -> None:
    employee_ids = [e["employee_id"] for e in EMPLOYEES]
    session.execute(
        text("DELETE FROM public.leave_balances WHERE employee_id = ANY(:employee_ids)"),
        {"employee_ids": employee_ids},
    )
    session.execute(
        text("DELETE FROM public.cases WHERE requester_id = ANY(:employee_ids)"),
        {"employee_ids": employee_ids},
    )
    session.execute(
        text("DELETE FROM public.employees WHERE employee_id = ANY(:employee_ids)"),
        {"employee_ids": employee_ids},
    )


def upsert_employees(session: Session) -> None:
    stmt = text(
        """
        INSERT INTO public.employees
        (employee_id, name, email, employment_type, location, department, grade, leave_policy_group, manager_id)
        VALUES
        (:employee_id, :name, :email, :employment_type, :location, :department, :grade, :leave_policy_group, :manager_id)
        ON CONFLICT (employee_id) DO UPDATE SET
            name = EXCLUDED.name,
            email = EXCLUDED.email,
            employment_type = EXCLUDED.employment_type,
            location = EXCLUDED.location,
            department = EXCLUDED.department,
            grade = EXCLUDED.grade,
            leave_policy_group = EXCLUDED.leave_policy_group,
            manager_id = EXCLUDED.manager_id
        """
    )
    for emp in EMPLOYEES:
        session.execute(stmt, emp)


def upsert_leave_balances(session: Session) -> None:
    stmt = text(
        """
        INSERT INTO public.leave_balances
        (employee_id, leave_type, available_units, last_updated_at)
        VALUES
        (:employee_id, :leave_type, :available_units, :last_updated_at)
        ON CONFLICT (employee_id, leave_type) DO UPDATE SET
            available_units = EXCLUDED.available_units,
            last_updated_at = EXCLUDED.last_updated_at
        """
    )
    now = datetime.now(timezone.utc)
    for emp in EMPLOYEES:
        employee_id = str(emp["employee_id"])
        grade = str(emp["grade"])
        annual, sick = BENEFIT_BY_GRADE[grade]
        session.execute(
            stmt,
            {
                "employee_id": employee_id,
                "leave_type": "ANNUAL",
                "available_units": annual,
                "last_updated_at": now,
            },
        )
        session.execute(
            stmt,
            {
                "employee_id": employee_id,
                "leave_type": "SICK",
                "available_units": sick,
                "last_updated_at": now,
            },
        )


def main() -> None:
    with Session(engine) as session:
        reset_demo_rows(session)
        upsert_employees(session)
        upsert_leave_balances(session)
        session.commit()

    print("Seeded demo employees and leave_balances.")
    print("Hierarchy source: be/policies/org_hierarchy_fte_cn_gz.md")
    print("Benefit source: be/policies/employee_benefits_fte_cn_gz.md")


if __name__ == "__main__":
    main()
