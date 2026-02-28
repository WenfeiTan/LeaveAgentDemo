from __future__ import annotations

import argparse
import json
import os
from typing import Callable, List, Literal, Optional

from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI

from tool.tools import policy_lookup

API_BASE = os.getenv("API_BASE", "http://localhost:8000")


class ApprovalRule(BaseModel):
    condition: str
    approvers: List[str]


class Citation(BaseModel):
    doc_name: str
    chunk_index: int
    quote: str


class LeavePolicy(BaseModel):
    min_unit: float
    advance_days_required: int
    max_consecutive_days: int
    approval_rules: List[ApprovalRule]
    citations: List[Citation]


class PolicyExtractionResult(BaseModel):
    policy_type: Literal["leave_policy"]
    policy_group: str
    is_applicable: bool
    applicability_reason: str
    data: Optional[LeavePolicy] = None


def run_policy_rag(
    query: str,
    policy_group: str = "FTE_CN_GZ",
    top_k: int = 4,
    debug_log: Optional[Callable[[str, str], None]] = None,
) -> PolicyExtractionResult:
    retrieval = policy_lookup.invoke({"policy_group": policy_group, "query": query, "top_k": top_k})
    chunks = retrieval["chunks"]

    context_blocks = []
    for c in chunks:
        context_blocks.append(
            f"[doc={c['doc_name']} chunk={c['chunk_index']} score={c['score']:.4f}]\n{c['content']}"
        )
    context_text = "\n\n".join(context_blocks)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.1,
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    structured_llm = llm.with_structured_output(PolicyExtractionResult)

    prompt = f"""
You are an HR policy parser.
Return ONLY data supported by retrieved policy chunks.
If there are multiple variants in context, choose the strictest applicable rule.
For citations, include concise quote snippets copied from context.
policy_type MUST be "leave_policy".
policy_group MUST be "{policy_group}".
Determine whether policy applies to user question.
If question is about contractor while policy says applies to FTE, set:
- is_applicable=false
- applicability_reason explaining mismatch
- data=null
If policy applies, set is_applicable=true and fill data.

User question: {query}
Policy group: {policy_group}

Retrieved chunks:
{context_text}
"""
    if debug_log:
        debug_log("policy_rag_prompt", prompt)

    result = structured_llm.invoke(prompt)
    if debug_log:
        debug_log("policy_rag_result", json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="I am a contractor, can I ask for annual leave?")
    parser.add_argument("--policy-group", default="FTE_CN_GZ")
    parser.add_argument("--top-k", type=int, default=4)
    args = parser.parse_args()

    result = run_policy_rag(
        query=args.query,
        policy_group=args.policy_group,
        top_k=args.top_k,
    )
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
