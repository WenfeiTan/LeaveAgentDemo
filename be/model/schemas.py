from __future__ import annotations
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field


# -------- Directory --------
class PersonProfile(BaseModel):
    employee_id: str
    name: str
    email: str
    employment_type: str
    location: str
    department: str
    grade: str
    leave_policy_group: str
    manager_id: Optional[str] = None


class DirectoryResponse(BaseModel):
    employee_profile: PersonProfile
    manager_profile: Optional[PersonProfile] = None
    skip_manager_profile: Optional[PersonProfile] = None
    hrbp_profile: Optional[PersonProfile] = None


# -------- Leave Balances --------
class LeaveBalanceItem(BaseModel):
    employee_id: str
    leave_type: str
    available_units: float


class LeaveBalancesResponse(BaseModel):
    employee_id: str
    balances: List[LeaveBalanceItem]


# -------- Cases --------
ALLOWED_CASE_STATUS = {"DRAFT", "PENDING_APPROVAL", "APPROVED", "REJECTED"}


class CaseCreateRequest(BaseModel):
    requester_id: str
    case_type: str = Field(..., examples=["LEAVE_REQUEST"])
    payload_json: Dict[str, Any] = Field(default_factory=dict)



class CasePatchRequest(BaseModel):
    status: Optional[str] = None
    payload_json: Optional[Dict[str, Any]] = None


class CaseResponse(BaseModel):
    case_id: str
    requester_id: str
    case_type: str
    status: str
    payload_json: Dict[str, Any]
    created_at: str
    updated_at: str


# -------- Policy RAG --------
class PolicyIngestRequest(BaseModel):
    policy_group: str = Field(..., examples=["FTE_CN_GZ"])
    doc_path: Optional[str] = None


class PolicyRetrieveRequest(BaseModel):
    policy_group: str = Field(..., examples=["FTE_CN_GZ"])
    query: str
    top_k: int = 4
