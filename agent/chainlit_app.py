from __future__ import annotations

import json
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import List

import chainlit as cl
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from leave_agent_demo import TOOLS, build_graph, _append_log, _build_system_prompt, _normalize_user_turn
from tool.tools import directory_lookup


def _extract_policy_asset_elements(delta_messages: List[BaseMessage]) -> List[cl.Element]:
    call_id_to_name: dict[str, str] = {}
    assets: list[dict] = []

    for m in delta_messages:
        if isinstance(m, AIMessage):
            for tc in (m.tool_calls or []):
                call_id_to_name[str(tc.get("id"))] = str(tc.get("name"))
        elif isinstance(m, ToolMessage):
            tool_name = call_id_to_name.get(str(m.tool_call_id))
            if tool_name not in {"policy_and_asset_lookup", "policy_asset_lookup"}:
                continue
            try:
                payload = json.loads(str(m.content))
                rows = payload.get("recommended_assets", payload.get("assets", []))
                if isinstance(rows, list):
                    assets.extend([r for r in rows if isinstance(r, dict)])
            except Exception:
                continue

    seen: set[str] = set()
    elements: List[cl.Element] = []
    for a in assets:
        file_path = str(a.get("file_path", "")).strip()
        if not file_path or file_path in seen:
            continue
        p = Path(file_path)
        if not p.exists():
            continue
        seen.add(file_path)

        title = str(a.get("title") or p.name)
        mime = str(a.get("mime_type") or "")
        ext = p.suffix.lower()
        is_image = mime.startswith("image/") or ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
        if is_image:
            elements.append(cl.Image(name=title, path=str(p), display="inline"))
            elements.append(cl.File(name=f"{title} (download)", path=str(p), display="inline"))
        else:
            elements.append(cl.File(name=title, path=str(p), display="inline"))
    return elements


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
    cl.user_session.set(
        "policy_group",
        profile.get("employee_profile", {}).get("leave_policy_group", "FTE_CN_GZ"),
    )
    _append_log(log_path, "SESSION_READY", f"name={name}, sso_email={sso_email}")

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

    try:
        _append_log(log_path, "USER", message.content)
        normalized_text = _normalize_user_turn(messages, message.content)
        _append_log(log_path, "USER_NORMALIZED", normalized_text)
        _append_log(log_path, "APP_INVOKE_START", f"message_count_before={len(messages)}")

        prev_len = len(messages)
        messages = [*messages, HumanMessage(content=normalized_text)]

        out = app.invoke({"messages": messages})
        messages = out["messages"]
        cl.user_session.set("messages", messages)
        delta_messages = messages[prev_len:]
        _append_log(log_path, "APP_INVOKE_END", f"message_count_after={len(messages)}")

        last = messages[-1]
        if isinstance(last, AIMessage):
            content = str(last.content)
        else:
            content = "已处理。"

        _append_log(log_path, "ASSISTANT_FINAL", content)
        elements = _extract_policy_asset_elements(delta_messages)
        await cl.Message(content=content, elements=elements).send()
    except Exception as e:
        err = f"{e}\n\n{traceback.format_exc()}"
        _append_log(log_path, "ON_MESSAGE_ERROR", err)
        await cl.Message(content=f"处理请求时发生错误：{e}").send()
