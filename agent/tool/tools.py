import os
import json
import requests
from typing import Any, Dict, Optional, Union

from langchain_core.tools import tool

API_BASE = os.getenv("API_BASE", "http://localhost:8000")


def _normalize_payload_json(payload_json: Optional[Union[Dict[str, Any], str]]) -> Dict[str, Any]:
    """
    Ensure payload_json is always a dict.
    - None -> {}
    - dict -> itself
    - str  -> {"note": <str>} OR parse JSON string if it looks like JSON object
    """
    if payload_json is None:
        return {}

    if isinstance(payload_json, dict):
        return payload_json

    if isinstance(payload_json, str):
        s = payload_json.strip()
        # If user/model passes a JSON object string, try to parse it
        if s.startswith("{") and s.endswith("}"):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
        return {"note": payload_json}

    # Unexpected type -> coerce to string note
    return {"note": str(payload_json)}


# Tool1 – Policy RAG Lookup
@tool
def policy_lookup(policy_group: str, query: str, top_k: int = 4) -> Dict[str, Any]:
    """Retrieve top-k policy chunks from Policy RAG index."""
    url = f"{API_BASE}/policy/retrieve"
    body = {"policy_group": policy_group, "query": query, "top_k": top_k}
    r = requests.post(url, json=body, timeout=20)
    r.raise_for_status()
    return r.json()


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
