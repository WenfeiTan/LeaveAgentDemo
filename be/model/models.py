from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.types import UserDefinedType
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func


class VectorType(UserDefinedType):
    def __init__(self, dims: int):
        self.dims = dims

    def get_col_spec(self, **kw):
        return f"VECTOR({self.dims})"

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            if isinstance(value, list):
                return "[" + ",".join(str(float(x)) for x in value) + "]"
            return value

        return process


class Employees(SQLModel, table=True):
    __tablename__ = "employees"
    __table_args__ = {"schema": "public"}

    employee_id: int = Field(sa_column=Column(String, primary_key=True))
    name: str = Field(sa_column=Column(String, nullable=False))
    email: str = Field(sa_column=Column(String, nullable=False, unique=True, index=True))

    employment_type: str = Field(sa_column=Column(String, nullable=False))  # e.g., FTE/Contractor
    location: str = Field(sa_column=Column(String, nullable=False))
    department: str = Field(sa_column=Column(String, nullable=False))
    grade: str = Field(sa_column=Column(String, nullable=False))
    leave_policy_group: str = Field(sa_column=Column(String, nullable=False))

    manager_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("public.employees.employee_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


class LeaveBalances(SQLModel, table=True):
    __tablename__ = "leave_balances"
    __table_args__ = {"schema": "public"}

    employee_id: int = Field(
        sa_column=Column(
            String, 
            ForeignKey("public.employees.employee_id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        )
    )
    leave_type: str = Field(
        sa_column=Column(String, primary_key=True, nullable=False)
    )  # e.g., annual
    available_units: float = Field(sa_column=Column(Float, nullable=False, default=0.0))

    last_updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    )


class Cases(SQLModel, table=True):
    __tablename__ = "cases"
    __table_args__ = {"schema": "public"}

    case_id: str = Field(
    default_factory=lambda: str(uuid.uuid4()),
    primary_key=True
)
    requester_id: int = Field(
        sa_column=Column(
            ForeignKey("public.employees.employee_id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )

    case_type: str = Field(sa_column=Column(String, nullable=False))  # e.g., LEAVE_REQUEST
    status: str = Field(sa_column=Column(String, nullable=False, default="DRAFT"))

    payload_json: dict = Field(sa_column=Column(JSONB, nullable=False, default=dict))

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    )


class PolicyChunks(SQLModel, table=True):
    __tablename__ = "policy_chunks"
    __table_args__ = {"schema": "public"}

    chunk_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True),
    )
    policy_group: str = Field(sa_column=Column(String, nullable=False, index=True))
    doc_name: str = Field(sa_column=Column(String, nullable=False))
    chunk_index: int = Field(sa_column=Column(Integer, nullable=False))
    content: str = Field(sa_column=Column(Text, nullable=False))
    embedding: str = Field(sa_column=Column(VectorType(3072), nullable=False))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )
