from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests


API_BASE = os.getenv("API_BASE", "http://localhost:8000")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _normalize_payload_json(payload_json: Optional[Union[Dict[str, Any], str]]) -> Dict[str, Any]:
    if payload_json is None:
        return {}
    if isinstance(payload_json, dict):
        return payload_json
    if isinstance(payload_json, str):
        s = payload_json.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
        return {"note": payload_json}
    return {"note": str(payload_json)}


def _parse_date_iso(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    normalized = text.lower().replace("_", " ").replace("-", " ")
    for ch in [",", ".", ";", ":", "(", ")", "[", "]", "{", "}", "/", "\\", '"', "'"]:
        normalized = normalized.replace(ch, " ")
    return [t for t in normalized.split() if t]


def _load_assets_from_api(policy_group: str) -> List[Dict[str, Any]]:
    url = f"{API_BASE}/policy-assets/list"
    body = {"policy_group": policy_group}
    r = requests.post(url, json=body, timeout=10)
    r.raise_for_status()
    payload = r.json()
    assets = payload.get("assets", [])
    return assets if isinstance(assets, list) else []


def _retrieve_policy_chunks(policy_group: str, query: str, top_k: int) -> Dict[str, Any]:
    url = f"{API_BASE}/policy/retrieve"
    body = {"policy_group": policy_group, "query": query, "top_k": top_k}
    r = requests.post(url, json=body, timeout=20)
    r.raise_for_status()
    return r.json()


def _rank_assets(
    *,
    policy_group: str,
    intent: str,
    cited_docs: Optional[List[str]] = None,
    answer_text: Optional[str] = None,
    top_k: int = 2,
) -> Dict[str, Any]:
    assets = _load_assets_from_api(policy_group)
    query_tokens = set(_tokenize(intent))
    answer_tokens = set(_tokenize(answer_text or ""))
    cited_doc_set = {d.strip() for d in (cited_docs or []) if str(d).strip()}

    scored: List[Dict[str, Any]] = []
    for asset in assets:
        if asset.get("policy_group") != policy_group:
            continue

        tags = [str(t) for t in asset.get("tags", [])]
        doc_names = [str(d) for d in asset.get("related_docs", [])]
        haystack_tokens = set(_tokenize(" ".join([asset.get("title", ""), asset.get("description", ""), *tags])))

        doc_overlap = cited_doc_set.intersection(set(doc_names))
        if cited_doc_set and not doc_overlap:
            continue

        doc_overlap_score = 0.0
        if cited_doc_set:
            doc_overlap_score = len(doc_overlap) / max(1, len(cited_doc_set))

        intent_match_cnt = len(query_tokens.intersection(haystack_tokens))
        answer_match_cnt = len(answer_tokens.intersection(haystack_tokens))
        intent_match_score = min(intent_match_cnt / 5.0, 1.0)
        answer_match_score = min(answer_match_cnt / 6.0, 1.0)

        score = (0.6 * doc_overlap_score) + (0.25 * intent_match_score) + (0.15 * answer_match_score)

        file_path = Path(str(asset.get("file_path", "")))
        if not file_path.is_absolute():
            file_path = (PROJECT_ROOT / file_path).resolve()

        if score > 0 and file_path.exists():
            scored.append(
                {
                    "asset_id": asset.get("asset_id"),
                    "title": asset.get("title") or file_path.name,
                    "description": asset.get("description", ""),
                    "mime_type": asset.get("mime_type", ""),
                    "file_path": str(file_path),
                    "related_docs": doc_names,
                    "score": score,
                    "score_detail": {
                        "doc_overlap_score": round(doc_overlap_score, 4),
                        "intent_match_score": round(intent_match_score, 4),
                        "answer_match_score": round(answer_match_score, 4),
                        "intent_match_count": intent_match_cnt,
                        "answer_match_count": answer_match_cnt,
                        "matched_docs": sorted(list(doc_overlap)),
                    },
                }
            )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return {
        "policy_group": policy_group,
        "intent": intent,
        "cited_docs": sorted(list(cited_doc_set)),
        "top_k": top_k,
        "assets": scored[: max(1, top_k)],
    }
