from __future__ import annotations

from rich.markdown import Markdown
from textual.widget import Widget

from kama_claude.tui.app import (
    KamaTuiApp,
    LLMStreamBlock,
    PermissionSelect,
    SlashCompleteWidget,
    ToolCallBlock,
    _param_summary,
    _preview,
)


# 功能：验证 _preview 超出长度时截断并追加省略号
# 设计：不依赖任何 TUI 组件，纯函数测试
def test_preview_truncates() -> None:
    assert _preview("abcde", 3) == "abc…"
    assert _preview("ab", 5) == "ab"


# 功能：验证工具参数摘要优先展示工具最关键字段
# 设计：覆盖 read_file/bash/note_save 三类常见工具，避免工具块摘要退化成整段 JSON
def test_param_summary_prefers_key_fields() -> None:
    assert _param_summary("read_file", {"path": "README.md"}) == "path='README.md'"
    assert _param_summary("bash", {"command": "echo hi", "timeout": 1}) == "command='echo hi'"
    assert _param_summary("note_save", {"content": "Python 3.12"}) == "content='Python 3.12'"


# 功能：验证 llm.token 事件累积到 LLMStreamBlock，不连续 token 各自新开一块
# 设计：monkey-patch _append 收集追加的 widgets，断言 token 追加到同一块；
#       发送非 token 事件后新 block 被重置，下一个 token 开启新块
def test_llm_tokens_accumulate_in_block() -> None:
    app = KamaTuiApp("127.0.0.1", 9999)
    appended: list[Widget] = []
    app._append = lambda w: appended.append(w)  # type: ignore[method-assign]

    app._handle_event({"type": "llm.token", "token": "Hello", "run_id": "r", "ts": "t"})
    app._handle_event({"type": "llm.token", "token": " world", "run_id": "r", "ts": "t"})

    assert len(appended) == 1  # same block reused
    assert isinstance(appended[0], LLMStreamBlock)
    assert appended[0]._text == "Hello world"  # type: ignore[attr-defined]


# 功能：验证 LLMStreamBlock 结束时会把累积文本渲染为 Rich Markdown
# 设计：直接调用 finalize_markdown，断言 renderable 类型，覆盖 Markdown polish 的核心行为
def test_llm_block_finalize_renders_markdown() -> None:
    block = LLMStreamBlock()
    block.append_token("## Title\n\n- one\n\n```python\nprint('hi')\n```")
    block.finalize_markdown()
    assert isinstance(block.content, Markdown)


# 功能：验证非 token 事件后 _current_llm 被重置，下一个 token 开启新块
# 设计：插入 step.started 中断流，验证之前的 block 被 finalize，之后的 llm.token 创建新 LLMStreamBlock
def test_llm_block_resets_after_non_token_event() -> None:
    app = KamaTuiApp("127.0.0.1", 9999)
    appended: list[Widget] = []
    app._append = lambda w: appended.append(w)  # type: ignore[method-assign]

    app._handle_event({"type": "llm.token", "token": "A", "run_id": "r", "ts": "t"})
    app._handle_event({"type": "step.started", "run_id": "r", "step": 2, "ts": "t"})
    app._handle_event({"type": "llm.token", "token": "B", "run_id": "r", "ts": "t"})

    llm_blocks = [w for w in appended if isinstance(w, LLMStreamBlock)]
    assert len(llm_blocks) == 2
    assert llm_blocks[0]._finalized  # type: ignore[attr-defined]


# 功能：验证 run.started 事件追加 Static widget 且包含 run_id 和 goal
# 设计：monkey-patch _append，断言追加的 widget 的 renderable 包含关键字段
def test_run_started_appends_widget_with_content() -> None:
    app = KamaTuiApp("127.0.0.1", 9999)
    appended: list[Widget] = []
    app._append = lambda w: appended.append(w)  # type: ignore[method-assign]

    app._handle_event({
        "type": "run.started", "run_id": "run-abc", "goal": "do the thing", "ts": "t"
    })

    assert len(appended) == 1
    rendered = appended[0].content
    assert "run-abc" in rendered
    assert "do the thing" in rendered


# 功能：验证 run.finished success 追加包含 "completed" 的 widget
# 设计：monkey-patch _append，检查 rendered 内容包含 completed 和 green
def test_run_finished_success_shows_completed() -> None:
    app = KamaTuiApp("127.0.0.1", 9999)
    appended: list[Widget] = []
    app._append = lambda w: appended.append(w)  # type: ignore[method-assign]

    app._handle_event({
        "type": "run.finished", "run_id": "r", "status": "success", "steps": 3, "ts": "t"
    })

    rendered = appended[0].content
    assert "completed" in rendered
    assert "green" in rendered


# 功能：验证 run.finished failed 追加包含 "failed" 和 red 的 widget
# 设计：与 success 对称，检查颜色标记差异
def test_run_finished_failed_shows_red() -> None:
    app = KamaTuiApp("127.0.0.1", 9999)
    appended: list[Widget] = []
    app._append = lambda w: appended.append(w)  # type: ignore[method-assign]

    app._handle_event({
        "type": "run.finished", "run_id": "r", "status": "failed",
        "steps": 1, "reason": "llm_error", "ts": "t"
    })

    rendered = appended[0].content
    assert "failed" in rendered
    assert "red" in rendered


# 功能：验证 tool.call_started 追加 ToolCallBlock，call_finished 更新其结果
# 设计：直接调用 _handle_event 两次，通过 _pending_tool_blocks 验证状态流转
def test_tool_call_started_and_finished() -> None:
    app = KamaTuiApp("127.0.0.1", 9999)
    appended: list[Widget] = []
    app._append = lambda w: appended.append(w)  # type: ignore[method-assign]

    app._handle_event({
        "type": "tool.call_started",
        "tool_use_id": "uid-1",
        "tool_name": "bash",
        "params": {"command": "echo hi"},
        "run_id": "r", "ts": "t",
    })
    assert "uid-1" in app._pending_tool_blocks  # type: ignore[attr-defined]

    app._handle_event({
        "type": "tool.call_finished",
        "tool_use_id": "uid-1",
        "tool_name": "bash",
        "elapsed_ms": 42,
        "output": "hi",
        "run_id": "r", "ts": "t",
    })
    assert "uid-1" not in app._pending_tool_blocks  # type: ignore[attr-defined]
    block = appended[0]
    assert isinstance(block, ToolCallBlock)
    assert block._finished  # type: ignore[attr-defined]
    assert block._output == "hi"  # type: ignore[attr-defined]


# 功能：验证 note_save 成功完成时工具块摘要显示 remembered
# 设计：直接操作 ToolCallBlock，覆盖 note_save 的特殊低噪声展示策略
def test_note_save_tool_block_shows_remembered() -> None:
    block = ToolCallBlock("note_save", {"content": "Python 3.12"})
    block.set_result("saved", 3)
    assert "remembered" in block._summary()  # type: ignore[attr-defined]


# 功能：验证提交用户输入时会追加 user turn，并进入 busy 状态
# 设计：用 fake client 替代 SocketClient，直接调用 on_chat_text_area_submitted，
#       覆盖 TextArea 清空内容 + 设置 busy 占位符的核心状态迁移
async def test_input_submit_appends_user_turn_and_keeps_prompt_enabled() -> None:
    class _FakeArea:
        def __init__(self) -> None:
            self.disabled = False
            self.border_title = ""
            self.text = "hello"

        def focus(self) -> None:
            pass

    class _FakeEvent:
        def __init__(self, area: _FakeArea) -> None:
            self.value = area.text
            self.text_area = area

    class _FakeClient:
        async def send_command(self, method: str, params: dict) -> dict:
            return {"run_id": "run-1"}

    app = KamaTuiApp("127.0.0.1", 9999)
    appended: list[Widget] = []
    app._append = lambda w: appended.append(w)  # type: ignore[method-assign]
    app._update_header = lambda state: None  # type: ignore[method-assign]
    app._client = _FakeClient()  # type: ignore[assignment]
    app._session_id = "sess-1"

    area = _FakeArea()
    event = _FakeEvent(area)
    await app.on_chat_text_area_submitted(event)  # type: ignore[arg-type]

    assert app._busy  # type: ignore[attr-defined]
    assert not area.disabled
    assert area.text == ""
    assert "queue" in area.border_title.lower()
    assert appended[0].content == "[bold]>[/bold] hello"


# 功能：验证未知事件类型不抛异常也不追加任何 widget
# 设计：发送 type 为 unknown 的事件，断言 appended 为空
def test_unknown_event_silently_ignored() -> None:
    app = KamaTuiApp("127.0.0.1", 9999)
    appended: list[Widget] = []
    app._append = lambda w: appended.append(w)  # type: ignore[method-assign]

    app._handle_event({"type": "some.unknown.type", "run_id": "r", "ts": "t"})
    assert appended == []


def test_slash_complete_clamps_stale_cursor() -> None:
    widget = SlashCompleteWidget([("one", ""), ("two", "")])
    widget._cursor = 99  # type: ignore[attr-defined]
    selected: list[str] = []
    widget.post_message = lambda msg: selected.append(msg.skill_name)  # type: ignore[method-assign]

    widget.select_current()

    assert selected == ["two"]


def test_permission_select_clamps_stale_cursor_on_enter() -> None:
    widget = PermissionSelect("tool-1")
    widget._cursor = 99  # type: ignore[attr-defined]
    decisions: list[str] = []
    widget._pick = lambda decision: decisions.append(decision)  # type: ignore[method-assign]

    class _Event:
        key = "enter"
        character = None

        def stop(self) -> None:
            pass

    widget.on_key(_Event())  # type: ignore[arg-type]

    assert decisions == ["always_deny"]


async def test_input_submit_while_busy_queues_message() -> None:
    class _FakeArea:
        def __init__(self) -> None:
            self.disabled = False
            self.border_title = ""
            self.text = "queued guidance"

        def focus(self) -> None:
            pass

    class _FakeEvent:
        def __init__(self, area: _FakeArea) -> None:
            self.value = area.text
            self.text_area = area

    app = KamaTuiApp("127.0.0.1", 9999)
    appended: list[Widget] = []
    app._append = lambda w: appended.append(w)  # type: ignore[method-assign]
    app._client = object()  # type: ignore[assignment]
    app._session_id = "sess-1"
    app._busy = True

    area = _FakeArea()
    await app.on_chat_text_area_submitted(_FakeEvent(area))  # type: ignore[arg-type]

    assert area.text == ""
    assert app._queued_messages == ["queued guidance"]  # type: ignore[attr-defined]
    assert "queued #1" in appended[0].content


def test_waiting_for_input_sends_next_queued_message() -> None:
    app = KamaTuiApp("127.0.0.1", 9999)
    appended: list[Widget] = []
    started: list[str] = []
    app._append = lambda w: appended.append(w)  # type: ignore[method-assign]
    app._update_header = lambda state: None  # type: ignore[method-assign]
    def _fake_run_worker(coro, **kwargs):
        coro.close()
        started.append("worker")

    app.run_worker = _fake_run_worker  # type: ignore[method-assign]
    app._queued_messages = ["/skill guide"]  # type: ignore[attr-defined]
    app._busy = True

    app._handle_event({"type": "session.waiting_for_input", "session_id": "sess-1"})

    assert app._busy  # type: ignore[attr-defined]
    assert app._queued_messages == []  # type: ignore[attr-defined]
    assert started == ["worker"]
    assert appended[-1].content == "[bold]>[/bold] /skill guide"


async def test_now_command_interrupts_and_queues_front() -> None:
    class _FakeArea:
        def __init__(self) -> None:
            self.disabled = False
            self.border_title = ""
            self.text = "/now focus on tests"

        def focus(self) -> None:
            pass

    class _FakeEvent:
        def __init__(self, area: _FakeArea) -> None:
            self.value = area.text
            self.text_area = area

    app = KamaTuiApp("127.0.0.1", 9999)
    appended: list[Widget] = []
    workers: list[str] = []
    app._append = lambda w: appended.append(w)  # type: ignore[method-assign]

    def _fake_run_worker(coro, **kwargs):
        coro.close()
        workers.append(kwargs.get("name", ""))

    app.run_worker = _fake_run_worker  # type: ignore[method-assign]
    app._client = object()  # type: ignore[assignment]
    app._session_id = "sess-1"
    app._busy = True
    app._queued_messages = ["later"]  # type: ignore[attr-defined]

    area = _FakeArea()
    await app.on_chat_text_area_submitted(_FakeEvent(area))  # type: ignore[arg-type]

    assert area.text == ""
    assert app._queued_messages == ["focus on tests", "later"]  # type: ignore[attr-defined]
    assert workers == ["cancel_for_now"]
    assert "interrupt + guide" in appended[0].content
