import requests
from datetime import date, datetime
from typing import Any, Dict, Optional, Union, List

from langchain_core.tools import tool

from tool.utils import (
    API_BASE,
    _normalize_payload_json,
    _parse_date_iso,
    _rank_assets,
    _retrieve_policy_chunks,
)


# Tool1 – Policy RAG Lookup
@tool
def policy_lookup(policy_group: str, query: str, top_k: int = 4) -> Dict[str, Any]:
    """Retrieve top-k policy chunks from Policy RAG index."""
    return _retrieve_policy_chunks(policy_group=policy_group, query=query, top_k=top_k)


@tool
def policy_asset_lookup(
    policy_group: str,
    intent: str,
    cited_docs: Optional[List[str]] = None,
    answer_text: Optional[str] = None,
    top_k: int = 2,
) -> Dict[str, Any]:
    """Lookup policy-related attachments with doc-driven recall and intent+answer rerank."""
    return _rank_assets(
        policy_group=policy_group,
        intent=intent,
        cited_docs=cited_docs,
        answer_text=answer_text,
        top_k=top_k,
    )


@tool
def policy_and_asset_lookup(
    policy_group: str,
    query: str,
    top_k: int = 4,
    asset_top_k: int = 2,
) -> Dict[str, Any]:
    """
    Unified lookup for Tool1:
    1) policy retrieval (RAG chunks)
    2) cited-doc extraction
    3) asset retrieval constrained by cited docs
    """
    retrieval = _retrieve_policy_chunks(policy_group=policy_group, query=query, top_k=top_k)
    chunks = retrieval.get("chunks", [])

    cited_docs: List[str] = []
    for c in chunks:
        if isinstance(c, dict) and c.get("doc_name"):
            cited_docs.append(str(c["doc_name"]))
    # de-dup cited docs while preserving order
    seen: set[str] = set()
    dedup_docs: List[str] = []
    for d in cited_docs:
        if d not in seen:
            seen.add(d)
            dedup_docs.append(d)

    asset_result = _rank_assets(
        policy_group=policy_group,
        intent=query,
        cited_docs=dedup_docs,
        answer_text=None,
        top_k=asset_top_k,
    )

    return {
        "policy_group": policy_group,
        "query": query,
        "top_k": top_k,
        "chunks": chunks,
        "cited_docs": dedup_docs,
        "recommended_assets": asset_result.get("assets", []),
        "asset_top_k": asset_top_k,
    }



# Tool2 – People Directory Lookup
@tool
def directory_lookup(lookup_by: str, value: str) -> Dict[str, Any]:
    """Lookup an employee profile (and manager profile) by email or employee_id."""
    if lookup_by == "email":
        url = f"{API_BASE}/directory/by-email/{value}"
    elif lookup_by == "employee_id":
        url = f"{API_BASE}/directory/by-id/{value}"
    else:
        raise ValueError("lookup_by must be 'email' or 'employee_id'")

    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


@tool
def leave_balance_lookup(employee_id: str, leave_type: str = "ANNUAL") -> Dict[str, Any]:
    """Get leave balance for one leave type."""
    url = f"{API_BASE}/leave-balances/{employee_id}/{leave_type}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


# Tool3 – Case/Ticket Create
@tool
def case_create(
    requester_id: str,
    case_type: str,
    payload_json: Optional[Union[Dict[str, Any], str]] = None,
) -> Dict[str, Any]:
    """Create a new HR case. Returns the created case object."""
    url = f"{API_BASE}/cases"
    body = {
        "requester_id": requester_id,
        "case_type": case_type,
        "payload_json": _normalize_payload_json(payload_json),
    }
    r = requests.post(url, json=body, timeout=10)
    r.raise_for_status()
    return r.json()


@tool
def case_get(case_id: str) -> Dict[str, Any]:
    """Get a case by case_id (UUID string)."""
    url = f"{API_BASE}/cases/{case_id}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


@tool
def case_update(
    case_id: str,
    status: Optional[str] = None,
    payload_json: Optional[Union[Dict[str, Any], str]] = None,
) -> Dict[str, Any]:
    """Patch a case (status and/or payload_json)."""
    url = f"{API_BASE}/cases/{case_id}"
    body: Dict[str, Any] = {}

    if status is not None:
        body["status"] = status
    if payload_json is not None:
        body["payload_json"] = _normalize_payload_json(payload_json)

    r = requests.patch(url, json=body, timeout=10)
    r.raise_for_status()
    return r.json()



# Tool4 – Eligibility Engine (deterministic)
@tool
def eligibility_engine(
    available_units: float,
    requested_units: float,
    start_date: str,
    advance_days_required: int,
    max_consecutive: int,
    manager_id: str,
    dept_head_id: Optional[str] = None,
    today: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deterministic leave eligibility check.

    Rules:
    1) Reject if available_units < requested_units
    2) Reject if today + advance_days_required > start_date
    3) Reject if requested_units > max_consecutive

    Approval chain:
    - Default manager
    - If requested_units > 3 days, add dept head
    """
    run_date = _parse_date_iso(today) if today else date.today()
    start = _parse_date_iso(start_date)
    min_submit_date = run_date.fromordinal(run_date.toordinal() + advance_days_required)

    reasons: List[str] = []
    if available_units < requested_units:
        reasons.append("Insufficient leave balance")
    if min_submit_date > start:
        reasons.append("Advance notice requirement not met")
    if requested_units > max_consecutive:
        reasons.append("Requested units exceed max consecutive limit")

    approval_chain = [manager_id]
    if requested_units > 3 and dept_head_id:
        approval_chain.append(dept_head_id)

    return {
        "eligible": len(reasons) == 0,
        "reasons": reasons,
        "balance_snapshot": {
            "available_units": available_units,
            "requested_units": requested_units,
            "remaining_if_approved": available_units - requested_units,
        },
        "normalized_form": {
            "today": run_date.isoformat(),
            "start_date": start.isoformat(),
            "advance_days_required": advance_days_required,
            "max_consecutive": max_consecutive,
        },
        "approval_chain": approval_chain,
    }
