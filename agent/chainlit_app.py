from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import List

import chainlit as cl
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from leave_agent_demo import TOOLS, build_graph, _append_log, _build_system_prompt, _normalize_user_turn
from tool.tools import directory_lookup


@cl.on_chat_start
async def on_chat_start() -> None:
    sso_email = os.getenv("SSO_EMAIL", "nancyfu@company.com")

    try:
        profile = directory_lookup.invoke({"lookup_by": "email", "value": sso_email})
    except Exception as e:
        await cl.Message(content=f"身份识别失败: {e}").send()
        return

    name = profile.get("employee_profile", {}).get("name", sso_email)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_path = str(Path(__file__).resolve().parent / "logs" / f"web_session_{run_id}.md")
    _append_log(log_path, "SESSION_START", f"sso_email={sso_email}")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.1,
        api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
    )
    app = build_graph(llm.bind_tools(TOOLS), _build_system_prompt(profile), log_path)

    cl.user_session.set("app", app)
    cl.user_session.set("messages", [])
    cl.user_session.set("log_path", log_path)

    await cl.Message(
        content=(
            f"[Fake SSO] 当前用户: {sso_email}\n"
            f"你好，{name}。我能为你做些什么？\n"
            f"[Session Log] {log_path}"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    app = cl.user_session.get("app")
    messages: List[BaseMessage] = cl.user_session.get("messages") or []
    log_path: str = cl.user_session.get("log_path")

    if app is None:
        await cl.Message(content="会话未初始化，请刷新页面重试。",).send()
        return

    _append_log(log_path, "USER", message.content)
    normalized_text = _normalize_user_turn(messages, message.content)
    _append_log(log_path, "USER_NORMALIZED", normalized_text)
    messages = [*messages, HumanMessage(content=normalized_text)]

    out = app.invoke({"messages": messages})
    messages = out["messages"]
    cl.user_session.set("messages", messages)

    last = messages[-1]
    if isinstance(last, AIMessage):
        content = str(last.content)
    else:
        content = "已处理。"

    _append_log(log_path, "ASSISTANT_FINAL", content)
    await cl.Message(content=content).send()
