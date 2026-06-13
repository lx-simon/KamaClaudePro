from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from kama_claude.core.bus.envelope import HandlerError
from kama_claude.core.events.bus import EventBus
from kama_claude.core.runner import RunOutcome
from kama_claude.core.session.manager import (
    SESSION_ALIAS_CONFLICT,
    SESSION_CLOSED,
    SESSION_NOT_FOUND,
    SessionManager,
)
from kama_claude.core.session.model import Session
from kama_claude.core.session.store import SessionStore


class _Runner:
    # 模拟 AgentRunner，将 run 新消息写入 thread 后返回成功
    async def run_and_capture(
        self,
        goal: str,
        *,
        run_id: str | None = None,
        session: Session | None = None,
        store: SessionStore | None = None,
        system_prompt_override: str | None = None,
        tool_whitelist: list[str] | None = None,
    ) -> RunOutcome:
        assert run_id is not None
        assert session is not None
        assert store is not None
        store.append_messages(
            session.id,
            [{"role": "assistant", "content": [{"type": "text", "text": f"done {goal}"}]}],
            run_id,
        )
        return RunOutcome(status="success", result="done", reason=None)


class _SlowRunner:
    async def run_and_capture(
        self,
        goal: str,
        *,
        run_id: str | None = None,
        session: Session | None = None,
        store: SessionStore | None = None,
        system_prompt_override: str | None = None,
        tool_whitelist: list[str] | None = None,
    ) -> RunOutcome:
        await asyncio.sleep(60)
        return RunOutcome(status="success", result="done", reason=None)


# 功能：验证 create 会创建 active session、写入 meta 并发布 session.created 事件
# 设计：用真实 SessionStore + EventBus 收集事件，覆盖 manager 与 store/bus 的协作边界
async def test_create_session_writes_meta_and_event(tmp_path: Path) -> None:
    events: list[object] = []
    bus = EventBus()

    async def collect(event: object) -> None:
        events.append(event)

    bus.subscribe(collect)
    store = SessionStore(tmp_path)
    manager = SessionManager(store, lambda: _Runner(), bus)  # type: ignore[arg-type]

    session = await manager.create("chat", "title")

    assert session.status == "active"
    assert store.read_meta(session.id).title == "title"
    assert [e.type for e in events] == ["session.created"]  # type: ignore[attr-defined]


# 功能：验证 chat session 处理一条消息后进入 waiting_for_input，并保留 user/assistant thread
# 设计：mock runner 主动追加 assistant 消息，确认 send_message 负责 user 消息、状态流转和 run_id 记录
async def test_send_message_chat_enters_waiting_and_writes_thread(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    manager = SessionManager(store, lambda: _Runner(), EventBus())  # type: ignore[arg-type]
    session = await manager.create("chat")

    run_id = await manager.send_message(session.id, "hello")

    loaded = store.read_meta(session.id)
    assert loaded.status == "waiting_for_input"
    assert loaded.run_ids == [run_id]
    messages = store.read_messages(session.id)
    assert messages[0] == {"role": "user", "content": "hello"}
    assert messages[1]["role"] == "assistant"


# 功能：验证 one_shot session 在单次消息完成后自动 closed
# 设计：复用 mock runner 的成功路径，聚焦 mode 对最终状态的影响，保证 kama run 的统一路径正确
async def test_one_shot_auto_closes(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    manager = SessionManager(store, lambda: _Runner(), EventBus())  # type: ignore[arg-type]
    session = await manager.create("one_shot")

    await manager.send_message(session.id, "hello")

    assert store.read_meta(session.id).status == "closed"


# 功能：验证不存在的 session_id 返回 session_not_found 错误码
# 设计：直接调用 get_history 的查找路径，断言 HandlerError code，覆盖 IPC handler 可结构化返回错误
async def test_missing_session_raises_handler_error(tmp_path: Path) -> None:
    manager = SessionManager(SessionStore(tmp_path), lambda: _Runner(), EventBus())  # type: ignore[arg-type]
    with pytest.raises(HandlerError) as exc:
        await manager.get_history("missing")
    assert exc.value.code == SESSION_NOT_FOUND


# 功能：验证 closed session 不能继续 send_message
# 设计：先显式 close，再发送消息，断言 session_closed 错误码，覆盖状态机拒绝路径
async def test_closed_session_rejects_message(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    manager = SessionManager(store, lambda: _Runner(), EventBus())  # type: ignore[arg-type]
    session = await manager.create("chat")
    await manager.close(session.id)

    with pytest.raises(HandlerError) as exc:
        await manager.send_message(session.id, "again")
    assert exc.value.code == SESSION_CLOSED


async def test_resume_loads_session_from_store(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    manager1 = SessionManager(store, lambda: _Runner(), EventBus())  # type: ignore[arg-type]
    session = await manager1.create("chat", "keep me")
    await manager1.send_message(session.id, "hello")

    manager2 = SessionManager(store, lambda: _Runner(), EventBus())  # type: ignore[arg-type]
    resumed = await manager2.resume(session.id)
    run_id = await manager2.send_message(session.id, "again")

    assert resumed.id == session.id
    assert store.read_meta(session.id).run_ids[-1] == run_id
    assert store.read_messages(session.id)[-2] == {"role": "user", "content": "again"}


def test_list_sessions_sorted_by_updated_at(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    old = Session(
        id="sess-old",
        mode="chat",
        status="waiting_for_input",
        title="old",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    new = Session(
        id="sess-new",
        mode="chat",
        status="waiting_for_input",
        title="new",
        created_at="2026-01-02T00:00:00+00:00",
        updated_at="2026-01-02T00:00:00+00:00",
    )
    store.write_meta(old)
    store.write_meta(new)

    assert [s.id for s in store.list_meta()] == ["sess-new", "sess-old"]


async def test_session_alias_can_resume_and_send(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    manager = SessionManager(store, lambda: _Runner(), EventBus())  # type: ignore[arg-type]
    session = await manager.create("chat", "project")

    aliased = await manager.set_alias(session.id, "work")
    resumed = await manager.resume("work")
    run_id = await manager.send_message("work", "continue")

    assert aliased.id == session.id
    assert resumed.id == session.id
    assert store.read_meta(session.id).alias == "work"
    assert store.read_meta(session.id).run_ids[-1] == run_id


async def test_session_alias_survives_new_manager(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    manager1 = SessionManager(store, lambda: _Runner(), EventBus())  # type: ignore[arg-type]
    session = await manager1.create("chat", "project")
    await manager1.set_alias(session.id, "work")

    manager2 = SessionManager(store, lambda: _Runner(), EventBus())  # type: ignore[arg-type]
    resumed = await manager2.resume("work")

    assert resumed.id == session.id
    assert resumed.alias == "work"


async def test_session_alias_conflict_rejected(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    manager = SessionManager(store, lambda: _Runner(), EventBus())  # type: ignore[arg-type]
    first = await manager.create("chat", "first")
    second = await manager.create("chat", "second")
    await manager.set_alias(first.id, "work")

    with pytest.raises(HandlerError) as exc:
        await manager.set_alias(second.id, "work")
    assert exc.value.code == SESSION_ALIAS_CONFLICT


async def test_cancel_running_session(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    manager = SessionManager(store, lambda: _SlowRunner(), EventBus())  # type: ignore[arg-type]
    session = await manager.create("chat")
    task = asyncio.create_task(manager.send_message(session.id, "slow"))
    await asyncio.sleep(0)

    assert await manager.cancel(session.id) is True
    with pytest.raises(asyncio.CancelledError):
        await task
