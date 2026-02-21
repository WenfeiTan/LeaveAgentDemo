from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, START, END

from tool.tools import (
    directory_lookup,
    policy_lookup,
    leave_balance_lookup,
    case_create,
    case_update,
    eligibility_engine,
)


TOOLS: List[BaseTool] = [
    directory_lookup,
    policy_lookup,
    leave_balance_lookup,
    case_create,
    case_update,
    eligibility_engine,
]
TOOL_MAP = {t.name: t for t in TOOLS}


class AgentState(TypedDict):
    messages: List[BaseMessage]


def _append_log(log_path: str, title: str, content: str) -> None:
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(f"\n## {title}\n\n{content}\n")


def _build_system_prompt(user_profile: Dict[str, Any]) -> str:
    employee = user_profile.get("employee_profile", {})
    manager = user_profile.get("manager_profile") or {}

    return f"""
You are LeaveAgentDemo.

General Rule (must follow):
1) Identify user first (already provided below).
2) Understand user request.
3) For QA answers, you must use internal document support first.
   - Use policy_lookup for evidence.
   - If doc support is insufficient, do not answer as fact; say not supported yet.
4) For non-QA requests, you must create a case record.
5) Before submitting (case_update to PENDING_APPROVAL), ask user confirmation first.

User Identity (trusted):
- employee_id: {employee.get('employee_id')}
- name: {employee.get('name')}
- email: {employee.get('email')}
- leave_policy_group: {employee.get('leave_policy_group')}
- manager_id: {manager.get('employee_id')}
- manager_email: {manager.get('email')}

Available tools and what each does:
- directory_lookup(lookup_by, value): query employee profile and manager profile.
- policy_lookup(policy_group, query, top_k): retrieve internal policy chunks with similarity scores.
- leave_balance_lookup(employee_id, leave_type): query actual leave balance in system. leave type only can be ANNUAL or SICK.
- case_create(requester_id, case_type, payload_json): create DRAFT case.
- case_update(case_id, status, payload_json?): update case status/payload.
- eligibility_engine(...): deterministic leave checks; returns eligibility and approval chain.

Case type constraint for this demo:
- LEAVE_REQUEST for leave execution.
- GENERAL_REQUEST for other non-QA requests.

Behavior:
- Be concise.
- Use tools; do not fabricate.
- If user asks unrelated tasks and no doc support, say:
  "目前还不支持这项工作，可以试试让我帮你提交工单。"
""".strip()


def build_graph(llm_with_tools, system_prompt: str, log_path: str):
    def node_assistant(state: AgentState) -> Dict[str, Any]:
        messages = state["messages"]
        ai_msg = llm_with_tools.invoke([SystemMessage(content=system_prompt), *messages])

        tool_calls = getattr(ai_msg, "tool_calls", []) or []
        _append_log(
            log_path,
            "ASSISTANT",
            json.dumps(
                {
                    "content": ai_msg.content,
                    "tool_calls": tool_calls,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
        )
        return {"messages": [*messages, ai_msg]}

    def node_tools(state: AgentState) -> Dict[str, Any]:
        messages = state["messages"]
        last = messages[-1]
        if not isinstance(last, AIMessage) or not last.tool_calls:
            return {"messages": messages}

        out_messages = [*messages]
        for tc in last.tool_calls:
            name = tc["name"]
            args = tc.get("args", {})
            if name not in TOOL_MAP:
                raise RuntimeError(f"Unknown tool call: {name}")

            result = TOOL_MAP[name].invoke(args)
            _append_log(
                log_path,
                f"TOOL::{name}",
                json.dumps({"args": args, "result": result}, ensure_ascii=False, indent=2, default=str),
            )
            out_messages.append(
                ToolMessage(
                    content=json.dumps(result, ensure_ascii=False, default=str),
                    tool_call_id=tc["id"],
                )
            )

        return {"messages": out_messages}

    def route_after_assistant(state: AgentState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "TOOLS"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("ASSISTANT", node_assistant)
    graph.add_node("TOOLS", node_tools)

    graph.add_edge(START, "ASSISTANT")
    graph.add_conditional_edges("ASSISTANT", route_after_assistant)
    graph.add_edge("TOOLS", "ASSISTANT")
    return graph.compile()


def main() -> None:
    sso_email = os.getenv("SSO_EMAIL", "xiaoming@company.com")

    try:
        profile = directory_lookup.invoke({"lookup_by": "email", "value": sso_email})
    except Exception as e:
        print(f"身份识别失败: {e}")
        return

    name = profile.get("employee_profile", {}).get("name", sso_email)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_path = str(Path(__file__).resolve().parent / "logs" / f"session_{run_id}.md")
    _append_log(log_path, "SESSION_START", f"sso_email={sso_email}")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.1,
        api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
    )
    system_prompt = _build_system_prompt(profile)
    app = build_graph(llm.bind_tools(TOOLS), system_prompt, log_path)

    print(f"[Fake SSO] 当前用户: {sso_email}")
    print(f"你好，{name}。我能为你做些什么？")
    print(f"[Session Log] {log_path}")

    messages: List[BaseMessage] = []

    while True:
        user_text = input("> ").strip()
        if user_text.lower() in {"exit", "quit", "bye", "退出", "再见"}:
            print("已退出。")
            return
        if not user_text:
            continue

        _append_log(log_path, "USER", user_text)
        messages = [*messages, HumanMessage(content=user_text)]

        out = app.invoke({"messages": messages})
        messages = out["messages"]

        last = messages[-1]
        if isinstance(last, AIMessage):
            print(last.content)
            _append_log(log_path, "ASSISTANT_FINAL", str(last.content))


if __name__ == "__main__":
    main()
