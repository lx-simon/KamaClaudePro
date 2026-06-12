# 最小 MCP 工具扩展模板

MCP，全称是 Model Context Protocol，可以把它理解成“给 AI 客户端外挂能力的统一插口”。模型本身不会真的读文件、查数据库、调接口；它只会发出一个结构化的 `tool_use` 意图。MCP Server 负责把这些意图变成真实代码执行，再把结果返回给客户端。

最小闭环只有三步：

1. 客户端启动 MCP Server，并发送 `initialize` 握手。
2. 客户端调用 `tools/list`，发现这个 Server 提供哪些工具。
3. 模型需要工具时，客户端调用 `tools/call`，Server 执行函数并返回结果。

这个目录里的 `server.py` 是一个最小可复刻模板，暴露了三个工具：

- `hello`: 输入名字，返回问候语。
- `add`: 输入 `a` 和 `b`，返回两数之和。
- `now`: 返回当前本地时间。

## 直接测试

在 PowerShell 中运行：

```powershell
python examples/mcp_minimal/server.py
```

然后手动输入一行 JSON，例如：

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
```

你会看到 Server 返回工具列表。

也可以测试工具调用：

```json
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"add","arguments":{"a":2,"b":3}}}
```

返回结果里会包含文本 `5`。

## 接入 KamaClaudePro

这个项目支持在 `.kama/config.toml` 中配置 stdio MCP Server。加上这一段：

```toml
[mcp]
servers = [
  { name = "demo", transport = "stdio", command = "python", args = ["examples/mcp_minimal/server.py"] }
]
```

启动后，客户端会发现这些工具，并用 `server名__工具名` 注册到本地工具表里。所以上面的三个工具会变成：

- `demo__hello`
- `demo__add`
- `demo__now`

你之后对模型说“用 demo 的 add 工具算 2+3”，它就可以通过 MCP 调到这个 Server。

## 怎么改成你自己的工具

复制 `server.py` 后，通常只改三处：

1. 在 `TOOLS` 里声明工具名、描述和 `inputSchema`。
2. 写一个同名处理函数，比如 `def search(args): ...`。
3. 在 `HANDLERS` 里把工具名绑定到函数。

例如新增一个 `multiply`：

```python
TOOLS["multiply"] = {
    "name": "multiply",
    "description": "Multiply two numbers.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
        "required": ["a", "b"],
    },
}


def multiply(args):
    return str(float(args["a"]) * float(args["b"]))


HANDLERS["multiply"] = multiply
```

## 这个模板故意很小

它使用的是本项目当前 MCP client 支持的“每行一个 JSON-RPC 消息”的 stdio 形式，方便你看懂和复刻。正式 MCP SDK/标准传输常见的是 `Content-Length` 头格式；如果要兼容更多客户端，比如 Claude Desktop 的官方 MCP SDK，下一步可以把工具函数保留，替换掉底层收发协议。
