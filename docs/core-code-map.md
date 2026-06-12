# KamaClaude 核心代码地图

这份文档用来回答两个问题：

1. 每个核心代码文件叫什么，负责什么。
2. 程序运行时，这些文件之间按什么链路协作。

范围：`src/kama_claude` 下的运行时代码。`tests`、`__pycache__`、图片和构建缓存不计入核心运行链路。

## 1. 总体分层

```text
用户入口
  -> CLI: src/kama_claude/cli/*
  -> TUI: src/kama_claude/tui/*

本地通信层
  -> JSON-RPC envelope: src/kama_claude/core/bus/envelope.py
  -> command/event schema: src/kama_claude/core/bus/*.py
  -> TCP NDJSON client/server: src/kama_claude/core/transport/*.py

Core daemon
  -> src/kama_claude/core/app.py
  -> config/logging/session/permission/mcp/trace 初始化

Agent 运行时
  -> SessionManager: src/kama_claude/core/session/manager.py
  -> AgentRunner: src/kama_claude/core/runner.py
  -> AgentLoop: src/kama_claude/core/loop.py
  -> ExecutionContext: src/kama_claude/core/context.py

模型与工具
  -> LLM Provider: src/kama_claude/core/llm/*
  -> ToolRegistry / invoke_tool: src/kama_claude/core/tools/*
  -> Builtin tools: src/kama_claude/core/tools/builtin/*
  -> MCP tools: src/kama_claude/core/mcp/*

状态与观测
  -> sessions: src/kama_claude/core/session/*
  -> events: src/kama_claude/core/events/*
  -> trace: src/kama_claude/core/trace/*
  -> compact: src/kama_claude/core/compact/*
```

## 2. 目录树与文件作用

```text
src/kama_claude/
|-- __init__.py
|   `-- 包版本等基础信息。
|-- py.typed
|   `-- 声明该包支持类型检查。
|
|-- cli/
|   |-- __init__.py
|   |-- __main__.py
|   |   `-- 允许 python -m kama_claude.cli 启动 CLI。
|   |-- main.py
|   |   `-- kama 命令总入口，解析子命令并分发。
|   `-- commands/
|       |-- __init__.py
|       |-- core.py
|       |   `-- kama core start/status/stop，管理 kama-core 守护进程。
|       |-- ping.py
|       |   `-- kama ping，向 core.ping 发 JSON-RPC 请求验证 daemon 存活。
|       |-- run.py
|       |   `-- kama run --goal，一次性运行 Agent 任务并订阅事件输出。
|       |-- chat.py
|       |   `-- kama chat，多轮会话客户端，发送 session.* 命令并打印事件。
|       |-- session.py
|       |   `-- kama session list/history，查看持久化会话。
|       |-- trace.py
|       |   `-- kama trace，读取 trace 日志并按 run/layer/direction 过滤。
|       `-- version.py
|           `-- 打印版本。
|
|-- tui/
|   |-- __init__.py
|   |-- __main__.py
|   |   `-- kama-tui 入口，设置日志并启动 Textual App。
|   `-- app.py
|       `-- TUI 主界面：聊天输入、事件流展示、工具块、权限选择、slash 补全。
|
`-- core/
    |-- __init__.py
    |-- __main__.py
    |   `-- 允许 python -m kama_claude.core 启动 core。
    |-- app.py
    |   `-- kama-core daemon 主体；初始化配置、事件总线、权限、MCP、SessionManager、SocketServer，并注册所有 RPC handler。
    |-- config.py
    |   `-- 配置模型与加载顺序：默认值、全局/项目 TOML、.env、环境变量。
    |-- context.py
    |   `-- ExecutionContext，保存 run_id、goal、messages、step、结果、system prompt、上下文材料。
    |-- logging_setup.py
    |   `-- 根据配置初始化日志。
    |-- loop.py
    |   `-- AgentLoop，核心 ReAct 循环：调用模型、追加 assistant/tool 消息、执行工具、判断结束、触发 compact。
    |-- runner.py
    |   `-- AgentRunner，组装一次 run 所需依赖：Provider、ToolRegistry、EventWriter、TaskManager、Compactor、Subagent、MCP 工具。
    |-- runs.py
    |   `-- run_id 生成、run 目录和 events.jsonl 路径管理。
    |
    |-- agents/
    |   |-- __init__.py
    |   |-- loader.py
    |   |   `-- 加载 Agent profile，包括模型、系统提示和工具白名单。
    |   `-- builtin/
    |       |-- executor.toml
    |       |-- planner.toml
    |       `-- reviewer.toml
    |           `-- 内置 Agent 角色配置。
    |
    |-- bus/
    |   |-- __init__.py
    |   |-- commands.py
    |   |   `-- JSON-RPC 命令参数/结果模型，如 agent.run、session.send_message、permission.respond。
    |   |-- envelope.py
    |   |   `-- JSON-RPC 请求、成功响应、错误响应、事件推送 envelope。
    |   `-- events.py
    |       `-- 运行事件模型，如 run.started、tool.call_started、permission.requested、llm.token。
    |
    |-- compact/
    |   |-- __init__.py
    |   |-- budget.py
    |   |   `-- tool_result 过长时截断，避免上下文爆炸。
    |   `-- compactor.py
    |       `-- 自动/手动压缩会话上下文，生成摘要并写回 thread。
    |
    |-- events/
    |   |-- __init__.py
    |   |-- bus.py
    |   |   `-- EventBus，内存内发布/订阅事件。
    |   `-- writer.py
    |       `-- EventWriter，把事件写入每次 run 的 events.jsonl。
    |
    |-- llm/
    |   |-- __init__.py
    |   |-- base.py
    |   |   `-- LLMProvider 协议，定义 chat 接口。
    |   |-- provider.py
    |   |   `-- AnthropicProvider、OpenAIProvider 和 create_provider；负责流式 token、工具调用块、usage 解析。
    |   `-- types.py
    |       `-- LlmResponse、ToolCallBlock、UsageStats 等统一返回类型。
    |
    |-- mcp/
    |   |-- __init__.py
    |   |-- client.py
    |   |   `-- MCP JSON-RPC client；连接 stdio/TCP server，initialize、tools/list、tools/call。
    |   |-- server.py
    |   |   `-- McpServerManager；启动配置里的 MCP server，发现工具并缓存。
    |   `-- tool.py
    |       `-- McpTool，把外部 MCP 工具包装成本项目 BaseTool。
    |
    |-- memory/
    |   |-- __init__.py
    |   `-- loader.py
    |       `-- 读取全局/项目 context.md，注入系统提示。
    |
    |-- permissions/
    |   |-- __init__.py
    |   |-- errors.py
    |   |   `-- PermissionDeniedError。
    |   |-- manager.py
    |   |   `-- PermissionManager；根据策略决定 allow/deny/ask，并等待客户端审批。
    |   |-- policy.py
    |   |   `-- 权限策略评估、危险命令判断、参数预览。
    |   `-- storage.py
    |       `-- 读取/保存 ~/.kama/policy.toml 的 always allow/deny 策略。
    |
    |-- session/
    |   |-- __init__.py
    |   |-- manager.py
    |   |   `-- SessionManager；创建/恢复/发送消息/关闭/压缩会话，并调用 AgentRunner。
    |   |-- model.py
    |   |   `-- Session 数据模型。
    |   `-- store.py
    |       `-- SessionStore；meta.json、thread.jsonl、notes、runs 目录的读写。
    |
    |-- skills/
    |   |-- __init__.py
    |   |-- loader.py
    |   |   `-- 解析内置/用户 skill markdown，支持 slash 命令、工具白名单、系统提示覆盖。
    |   `-- builtin/
    |       |-- init.md
    |       |-- orchestrate.md
    |       |-- review.md
    |       `-- summarize.md
    |           `-- 内置 skill 定义。
    |
    |-- subagent/
    |   |-- __init__.py
    |   |-- registry.py
    |   |   `-- 后台子 Agent 任务注册表，用 run_id 查询结果。
    |   `-- tool.py
    |       `-- spawn_agent 和 agent_result 工具，实现子 Agent 派生与结果读取。
    |
    |-- task/
    |   |-- __init__.py
    |   |-- manager.py
    |   |   `-- TaskManager；管理任务清单的增删改查和持久化。
    |   `-- model.py
    |       `-- Task 数据模型。
    |
    |-- tools/
    |   |-- __init__.py
    |   |-- base.py
    |   |   `-- BaseTool 和 ToolResult，所有工具的统一接口。
    |   |-- errors.py
    |   |   `-- RateLimitedError 等工具错误类型。
    |   |-- invocation.py
    |   |   `-- invoke_tool；统一处理工具查找、参数校验、权限审批、超时、重试、事件发布。
    |   |-- registry.py
    |   |   `-- ToolRegistry；注册工具并输出模型需要的 tool schema。
    |   `-- builtin/
    |       |-- __init__.py
    |       |-- bash.py
    |       |   `-- 执行 shell 命令。
    |       |-- list_dir.py
    |       |   `-- 列目录。
    |       |-- read_file.py
    |       |   `-- 读取文件。
    |       |-- write_file.py
    |       |   `-- 写文件。
    |       |-- note_save.py
    |       |   `-- 保存会话 notes。
    |       |-- task_create.py
    |       |   `-- 创建任务。
    |       |-- task_update.py
    |       |   `-- 更新任务状态。
    |       |-- task_list.py
    |       |   `-- 列出任务。
    |       `-- task_get.py
    |           `-- 查看单个任务。
    |
    |-- trace/
    |   |-- __init__.py
    |   |-- provider.py
    |   |   `-- TracingProvider；包裹 LLMProvider，把 LLM 请求/响应写入 trace。
    |   |-- record.py
    |   |   `-- TraceRecord 结构。
    |   `-- writer.py
    |       `-- TraceWriter；异步写 trace NDJSON。
    |
    `-- transport/
        |-- __init__.py
        |-- socket_client.py
        |   `-- CLI/TUI 使用的 TCP JSON-RPC client，支持事件推送分发。
        |-- socket_server.py
        |   `-- core daemon 的 TCP JSON-RPC server，按行读取 NDJSON 并调用 handler。
        `-- ipc_broadcaster.py
            `-- 把 EventBus 事件推送到已订阅的 CLI/TUI 连接。
```

## 3. 一次 `kama core start` 的链路

```text
pyproject scripts: kama
  -> cli/main.py main()
  -> cli/commands/core.py cmd_core_start(config)
  -> 启动后台进程 kama-core
  -> core/app.py run()
  -> CoreApp.run()
```

`CoreApp.run()` 内部顺序：

```text
config.py get_config()
  -> logging_setup.py setup_logging()
  -> trace/writer.py TraceWriter.start() 可选
  -> permissions/manager.py PermissionManager(...)
  -> transport/ipc_broadcaster.py IpcEventBroadcaster(...)
  -> session/store.py SessionStore(~/.kama/sessions)
  -> llm/provider.py create_provider() 给 compact 使用
  -> mcp/server.py McpServerManager.start_all() 可选启动外部 MCP
  -> session/manager.py SessionManager(...)
  -> transport/socket_server.py SocketServer(...)
  -> server.register(...) 注册 core.ping、agent.run、session.*、permission.respond
  -> SocketServer.start() 监听 host/port
```

这条链路启动的是常驻 daemon。之后 CLI/TUI 都只是客户端，通过 TCP NDJSON 发 JSON-RPC 命令。

## 4. 一次 `kama ping` 的链路

```text
cli/main.py
  -> cli/commands/ping.py cmd_ping()
  -> transport/socket_client.py SocketClient.connect()
  -> SocketClient.send_command("core.ping", {client: "kama"})
  -> core/transport/socket_server.py SocketServer._handle_line()
  -> core/app.py CoreApp._ping_handler()
  -> bus/commands.py PongResult
  -> SocketServer._send(JsonRpcSuccess)
  -> SocketClient._dispatch()
  -> CLI 打印 pong 信息
```

作用：验证 daemon 已启动，并确认 JSON-RPC 通道正常。

## 5. 一次 `kama run --goal ...` 的链路

`kama run` 是一次性任务。客户端发起任务后，core 创建 one_shot session，并异步跑 Agent。

```text
cli/main.py
  -> cli/commands/run.py cmd_run()
  -> SocketClient.connect()
  -> SocketClient.on_event(StdoutPrinter.handle)
  -> send_command("event.subscribe", topics=[...])
  -> send_command("agent.run", {goal})
```

core 侧：

```text
transport/socket_server.py
  -> app.py CoreApp._agent_run_handler()
  -> session/manager.py SessionManager.create(mode="one_shot")
  -> runs.py new_run_id()
  -> asyncio.create_task(SessionManager.send_message(session.id, goal, run_id))
```

真正执行任务：

```text
session/manager.py send_message()
  -> session/store.py append_message(user)
  -> bus/events.py SessionMessageReceivedEvent
  -> skills/loader.py 如果内容以 / 开头，解析 skill
  -> runner.py AgentRunner.run_and_capture()
```

`AgentRunner.run_and_capture()` 组装运行时：

```text
session/store.py read_messages/read_notes 或构造 one-shot history
  -> memory/loader.py 读取 ~/.kama/context.md 和 .kama/context.md
  -> task/manager.py TaskManager(run_path/.tasks)
  -> context.py ExecutionContext(...)
  -> events/writer.py EventWriter(run_path/events.jsonl)
  -> bus/events.py RunStartedEvent
  -> llm/provider.py create_provider()
  -> trace/provider.py TracingProvider 可选包裹 provider
  -> tools/registry.py ToolRegistry
  -> tools/builtin/*.py 注册内置工具
  -> subagent/tool.py 注册 spawn_agent/agent_result
  -> mcp/server.py get_tools() 注册外部 MCP 工具
  -> compact/compactor.py Compactor
  -> loop.py AgentLoop.run(context)
```

`AgentLoop.run()` 是核心 Agent 循环：

```text
while context 未完成:
  -> bus/events.py StepStartedEvent
  -> llm/provider.py provider.chat(messages, tool_schemas, system, bus, run_id, step)
  -> llm/types.py LlmResponse(text, tool_calls, stop_reason, usage)
  -> context.py add_assistant_message(...)

  如果 stop_reason == "tool_use":
    -> tools/invocation.py invoke_tool(...)
    -> tools/registry.py registry.get(tool_name)
    -> tools/base.py BaseTool.invoke(...)
    -> context.py add_tool_result(...)
    -> 下一轮把 tool_result 回填给模型

  如果 stop_reason == "end_turn":
    -> context.mark_success()

  如果 step >= max_steps:
    -> context.mark_failed("exceeded_max_steps")

  如果上下文水位超过阈值:
    -> compact/compactor.py compact(context, provider)

  -> bus/events.py StepFinishedEvent
```

收尾：

```text
runner.py
  -> bus/events.py RunFinishedEvent
  -> session/store.py append_messages(...)

session/manager.py
  -> one_shot session 标记 closed
  -> bus/events.py SessionClosedEvent
  -> session/store.py write_meta(...)

ipc_broadcaster.py
  -> 把 run/tool/llm/session 事件推送给 CLI/TUI
```

## 6. 一次 `kama chat` 的链路

`chat` 和 `run` 共用后半段 Agent 链路，区别是 session 保持为 `chat`，每轮结束后等待下一次用户输入。

```text
cli/main.py
  -> cli/commands/chat.py cmd_chat()
  -> SocketClient.connect()
  -> send_command("session.create", {mode: "chat"}) 或 send_command("session.resume", {session_id})
  -> send_command("event.subscribe", scope={session_id})
  -> 用户输入一行
  -> send_command("session.send_message", {session_id, content})
```

core 侧：

```text
app.py CoreApp._session_send_handler()
  -> session/manager.py SessionManager.send_message()
  -> runner.py AgentRunner.run_and_capture(session=..., store=...)
  -> loop.py AgentLoop.run()
  -> session/store.py append_messages()
  -> session 状态改为 waiting_for_input
  -> bus/events.py SessionWaitingForInputEvent
```

下一轮用户输入时：

```text
session/store.py read_messages(session_id)
  -> 旧 thread 作为 prefill_messages
  -> context.py ExecutionContext(prefill_messages=history)
  -> 模型获得完整历史继续推理
```

## 7. TUI 运行链路

TUI 本质上是更丰富的客户端，核心执行仍在 `kama-core`。

```text
pyproject scripts: kama-tui
  -> tui/__main__.py main()
  -> tui/app.py run(...)
  -> KamaTuiApp
  -> transport/socket_client.py SocketClient.connect()
  -> event.subscribe 订阅事件
  -> session.create / session.resume / session.send_message
```

TUI 事件展示：

```text
SocketClient.run_event_loop()
  -> _dispatch(event)
  -> tui/app.py KamaTuiApp._handle_event(...)
  -> LLMStreamBlock 展示 llm.token
  -> ToolCallBlock 展示 tool.call_started / finished / failed
  -> PermissionBlock + PermissionSelect 展示 permission.requested
```

权限审批：

```text
用户在 TUI 点 allow/deny
  -> tui/app.py PermissionSelect.Decided
  -> SocketClient.send_command("permission.respond", {tool_use_id, decision})
  -> app.py CoreApp._permission_respond_handler()
  -> permissions/manager.py PermissionManager.respond()
  -> tools/invocation.py invoke_tool() 中等待的 Future 被唤醒
  -> 工具继续执行或返回 permission_denied
```

## 8. 工具调用链路

模型不会直接执行工具。它只返回 `tool_use` block，项目把这个 block 送进统一工具调用管线。

```text
llm/provider.py
  -> 把模型响应解析成 llm/types.py ToolCallBlock(id, name, input)
  -> loop.py AgentLoop.run()
  -> tools/invocation.py invoke_tool(registry, tool_call, bus, run_id)
```

`invoke_tool()` 的顺序：

```text
bus/events.py ToolCallStartedEvent
  -> tools/registry.py registry.get(tool_name)
  -> 如果工具有 params_model，先用 pydantic 校验参数
  -> permissions/manager.py check_and_wait(...) 可选权限审批
  -> BaseTool.invoke(params)
  -> 成功：ToolCallFinishedEvent + ToolResult(content)
  -> 失败：ToolCallFailedEvent + ToolResult(is_error=True)
  -> loop.py context.add_tool_result(tool_use_id, result.content)
```

内置工具来自：

```text
tools/builtin/read_file.py
tools/builtin/write_file.py
tools/builtin/list_dir.py
tools/builtin/bash.py
tools/builtin/note_save.py
tools/builtin/task_create.py
tools/builtin/task_update.py
tools/builtin/task_list.py
tools/builtin/task_get.py
```

子 Agent 工具来自：

```text
subagent/tool.py SpawnAgentTool
  -> 创建子 AgentLoop/AgentRunner 风格的后台任务
  -> subagent/registry.py 记录后台任务

subagent/tool.py AgentResultTool
  -> 根据 run_id 读取子 Agent 结果
```

MCP 工具来自：

```text
app.py CoreApp.run()
  -> mcp/server.py McpServerManager.start_all(config.mcp.servers)
  -> mcp/client.py McpClient.connect_stdio/connect_tcp()
  -> initialize
  -> tools/list
  -> mcp/tool.py McpTool(client, server_name, tool_def)

runner.py AgentRunner._build_registry()
  -> mcp_manager.get_tools()
  -> registry.register(mcp_tool)

loop.py tool_use
  -> invocation.py invoke_tool()
  -> mcp/tool.py McpTool.invoke()
  -> mcp/client.py call_tool(name, arguments)
  -> 外部 MCP server 执行真实工具
```

MCP 工具名会被包装成：

```text
{server_name}__{tool_name}
```

例如配置 `name = "demo"` 且 MCP server 暴露 `add`，本地工具名就是 `demo__add`。

## 9. 事件、events.jsonl、trace 的链路

运行事件有两条去向：实时推送给客户端，以及持久化到文件。

```text
业务代码 publish 事件
  -> events/bus.py EventBus.publish(event)
  -> events/writer.py EventWriter 写 run_dir/events.jsonl
  -> transport/ipc_broadcaster.py IpcEventBroadcaster.handle(event)
  -> transport/socket_server.py 当前订阅连接 writer.write(...)
  -> CLI/TUI SocketClient._dispatch(event)
```

trace 是系统级观测，记录 IPC、EventBus、LLM 层：

```text
app.py CoreApp.run()
  -> trace/writer.py TraceWriter.start()
  -> EventBus.subscribe(CoreApp._trace_event_handler)

transport/socket_server.py
  -> 收到命令时写 CLIENT->CORE trace
  -> 返回响应时写 CORE->CLIENT trace

trace/provider.py TracingProvider
  -> LLM 请求前写 CORE->LLM trace
  -> LLM 响应后写 LLM->CORE trace

cli/commands/trace.py
  -> 读取 trace 文件并过滤展示
```

## 10. 上下文与压缩链路

上下文来源：

```text
session/store.py read_messages(session_id)
  -> 历史 thread
session/store.py read_notes(session_id)
  -> note_save 保存的 notes
memory/loader.py load_context_file(~/.kama/context.md)
memory/loader.py load_context_file(.kama/context.md)
```

进入模型前：

```text
context.py ExecutionContext.system_prompt(...)
  -> 合并默认系统提示
  -> 合并全局 context
  -> 合并项目 context
  -> 合并 session notes
  -> 可选 skill system_prompt_override
```

压缩触发：

```text
loop.py AgentLoop.run()
  -> response.usage.context_pct >= config.compaction.auto_threshold
  -> compact/compactor.py Compactor.compact(context, provider)
  -> 用 LLM 总结历史
  -> context.messages 替换成摘要继续下一轮
```

手动压缩：

```text
CLI/TUI 发送 session.compact
  -> app.py CoreApp._session_compact_handler()
  -> session/manager.py SessionManager.compact()
  -> compact/compactor.py compact_messages(...)
  -> session/store.py write_compacted(...)
```

## 11. 权限审批链路

权限系统只在工具执行前介入。

```text
loop.py AgentLoop.run()
  -> invocation.py invoke_tool(..., permission_manager)
  -> permissions/manager.py check_and_wait(...)
  -> permissions/policy.py evaluate(tool_name, params, policy)
  -> permissions/storage.py load_policy_file(~/.kama/policy.toml)
```

结果分三类：

```text
auto_allow / allow_once / allow_always
  -> 发布 PermissionGrantedEvent
  -> 继续执行工具

auto_deny / deny_once / deny_always
  -> 发布 PermissionDeniedEvent
  -> 返回 permission_denied tool_result

ask
  -> 发布 PermissionRequestedEvent
  -> CLI/TUI 通过 permission.respond 回答
  -> PermissionManager.respond() 唤醒等待中的工具调用
```

## 12. 配置加载链路

```text
core/config.py get_config()
  -> 默认 dataclass 值
  -> ~/.kama/config.toml
  -> .kama/config.toml
  -> .env
  -> KAMA_* 环境变量覆盖
```

关键配置影响：

```text
core.host / core.port
  -> SocketServer 和 SocketClient 连接地址

llm.provider / llm.default_model
  -> create_provider()

agent.max_steps
  -> ExecutionContext.max_steps

trace.enabled / trace.file / trace.include_llm_payload
  -> TraceWriter 和 TracingProvider

permission.timeout_s
  -> PermissionManager 等待审批超时时间

compaction.auto_threshold / tool_result_limit / tool_result_keep
  -> AgentLoop 自动压缩和 tool_result 截断

mcp.servers
  -> McpServerManager.start_all()
```

## 13. 最常用的读代码路线

如果你想看“Agent 怎么跑起来”，按这个顺序读：

```text
src/kama_claude/cli/commands/run.py
src/kama_claude/core/app.py
src/kama_claude/core/session/manager.py
src/kama_claude/core/runner.py
src/kama_claude/core/loop.py
src/kama_claude/core/llm/provider.py
src/kama_claude/core/tools/invocation.py
```

如果你想看“工具怎么扩展”，按这个顺序读：

```text
src/kama_claude/core/tools/base.py
src/kama_claude/core/tools/registry.py
src/kama_claude/core/tools/invocation.py
src/kama_claude/core/tools/builtin/read_file.py
src/kama_claude/core/runner.py
```

如果你想看“MCP 怎么接进来”，按这个顺序读：

```text
src/kama_claude/core/config.py
src/kama_claude/core/app.py
src/kama_claude/core/mcp/server.py
src/kama_claude/core/mcp/client.py
src/kama_claude/core/mcp/tool.py
src/kama_claude/core/runner.py
```

如果你想看“TUI 怎么实时显示过程”，按这个顺序读：

```text
src/kama_claude/tui/__main__.py
src/kama_claude/tui/app.py
src/kama_claude/core/transport/socket_client.py
src/kama_claude/core/transport/ipc_broadcaster.py
src/kama_claude/core/bus/events.py
```

## 14. 一句话主链路

```text
用户输入
  -> CLI/TUI
  -> SocketClient
  -> SocketServer
  -> CoreApp handler
  -> SessionManager
  -> AgentRunner
  -> AgentLoop
  -> LLMProvider
  -> ToolRegistry/invoke_tool/PermissionManager
  -> ToolResult 回填 ExecutionContext
  -> EventBus
  -> EventWriter + IpcEventBroadcaster + TraceWriter
  -> CLI/TUI 实时展示
```
