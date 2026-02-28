import json
from typing import Any, Dict, List
import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool

from tool.tools import directory_lookup, case_create, case_get, case_update, policy_lookup, eligibility_engine

TOOLS: List[BaseTool] = [policy_lookup, directory_lookup, case_create, case_get, case_update, eligibility_engine]
TOOL_MAP = {t.name: t for t in TOOLS}


SYSTEM_PROMPT = """
You are an HR Agent Orchestrator for a Leave Management System.

Rules:
1. Always use tools when accessing employee data or cases.
2. Never fabricate employee information.
2.1 Eligibility decisions must use eligibility_engine (deterministic). Do not infer by yourself.
3. If creating a case, default status should be DRAFT unless user explicitly asks to submit. If required information is missing, ask user before calling tools.
Never call case_create without requester_id.
4. Prefer lookup by email if provided.
5. After calling tools, summarize results clearly for the user.
6. Only use available tools. Do not invent new ones.
"""


def run_with_tools(user_text: str) -> Dict[str, Any]:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.1,
        api_key=os.getenv("GOOGLE_API_KEY")
    ).bind_tools(TOOLS)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_text),
    ]

    for _ in range(5):
        ai_msg = llm.invoke(messages)

        # 如果模型直接给出文本且没有 tool_calls
        if ai_msg.content and not ai_msg.tool_calls:
            return {"final_text": ai_msg.content, "messages": messages + [ai_msg]}

        # 如果模型调用工具
        if ai_msg.tool_calls:
            messages.append(ai_msg)

            for tc in ai_msg.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["args"]

                if tool_name not in TOOL_MAP:
                    raise RuntimeError(f"Unknown tool call: {tool_name}")

                tool = TOOL_MAP[tool_name]
                result = tool.invoke(tool_args)

                messages.append(
                    ToolMessage(
                        content=json.dumps(result, ensure_ascii=False),
                        tool_call_id=tc["id"],
                    )
                )

            continue

        return {"final_text": "", "messages": messages + [ai_msg]}

    return {"final_text": "(stopped: too many tool iterations)", "messages": messages}


if __name__ == "__main__":
    out = run_with_tools(
        "Create a case for XiaoMing, employee ID EMP2001, playload_json could be demotest"
    )
    print("\n=== FINAL ===\n", out["final_text"])
