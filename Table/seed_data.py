from sqlmodel import Session, create_engine, select
from datetime import datetime

from create_tables import Employees, LeaveBalances  

DATABASE_URL = "postgresql+psycopg2://postgres:123456@localhost:5432/postgres"

engine = create_engine(DATABASE_URL, echo=True)


def seed_employees(session: Session):
    existing = session.exec(select(Employees)).first()
    if existing:
        print("Employees already seeded. Skipping.")
        return

    zhaopeng = Employees(
        employee_id="EMP2001",
        name="ZhaoPeng",
        email="zhaopeng@company.com",
        employment_type="FTE",
        location="Guangzhou",
        department="DataTech",
        grade="M2",
        leave_policy_group="FTE_CN_GZ",
        manager_id=None,
    )

    xiaoming = Employees(
        employee_id="EMP1001",
        name="XiaoMing",
        email="xiaoming@company.com",
        employment_type="FTE",
        location="Guangzhou",
        department="DataTech",
        grade="IC2",
        leave_policy_group="FTE_CN_GZ",
        manager_id="EMP2001",
    )

    session.add(zhaopeng)
    session.add(xiaoming)
    session.commit()

    print("Seeded employees.")


def seed_leave_balances(session: Session):
    existing = session.exec(select(LeaveBalances)).first()
    if existing:
        print("Leave balances already seeded. Skipping.")
        return

    balances = [
        LeaveBalances(
            employee_id="EMP1001",
            leave_type="ANNUAL",
            available_units=10.0,
            last_updated_at=datetime.utcnow(),
        ),
        LeaveBalances(
            employee_id="EMP1001",
            leave_type="SICK",
            available_units=5.0,
            last_updated_at=datetime.utcnow(),
        ),
    ]

    session.add_all(balances)
    session.commit()

    print("Seeded leave balances.")


def main():
    with Session(engine) as session:
        seed_employees(session)
        seed_leave_balances(session)


if __name__ == "__main__":
    main()
