# 自定义 AI 智能体

[English](README.md)

> **本项目正在积极开发中，预计会存在 Bug、功能不完整及粗糙的地方。错误处理与 try/catch 覆盖将逐步完善。**

一个运行在本地的 AI 智能体，具备持久化记忆、语义搜索、用户画像追踪、工具调用以及微信 ACP 集成 —— 全部通过 Ollama 在你自己的硬件上运行。

---

## 工作原理

- 对话内容以向量嵌入的形式存储在 PostgreSQL 中，支持语义记忆召回
- 后台画像提取器自动从对话中构建结构化的开发者画像
- 智能体可调用工具：执行终端命令、搜索网页、读写文件等
- 通过 ACP（智能体通信协议）接入微信，让你可以直接在微信中与智能体对话

---

## 前置依赖

在开始之前，请先安装以下依赖：

| 依赖 | 用途 |
|---|---|
| [Python 3.10+](https://www.python.org/downloads/) | 运行智能体 |
| [Node.js 18+](https://nodejs.org/) | 运行微信 ACP 桥接服务（`npx wechat-acp`） |
| [Ollama](https://ollama.com/download) | 在本地运行 LLM 和嵌入模型 |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | 运行 PostgreSQL + pgvector 数据库 |

> **`pip install ollama` 是否可以替代安装 Ollama 应用？**
> 不能。`ollama` Python 包（通过 `requirements.txt` 安装）只是一个 HTTP 客户端 SDK，负责让 Python 与 Ollama 服务通信。你仍然需要在本机安装并运行 **Ollama 应用**来加载和运行模型。类比来说，这就像安装了 `psycopg2` 数据库驱动，但并不代表你有了数据库，只是有了连接数据库的能力。

---

## 安装步骤

### 1. 克隆项目并安装 Python 依赖

```bash
git clone <你的仓库地址>
cd custom-agent
pip install -r requirements.txt
```

### 2. 通过 Ollama 拉取模型

先确保 Ollama 正在运行（打开 Ollama 应用或执行 `ollama serve`），然后拉取嵌入模型：

```bash
ollama pull nomic-embed-text
```

**关于主模型（`MODEL`）和画像模型（`PROFILE_MODEL`）：**

- 如果你使用的是**云端模型**（模型名称以 `:cloud` 结尾，例如 `qwen3-coder-next:cloud`），Ollama 会从云端流式加载，**无需提前拉取**，直接在 `.env` 中填写模型名称即可运行。
- 如果你使用的是**本地模型**（名称中没有 `:cloud` 后缀，例如 `qwen2.5-coder:7b`），则必须先拉取：

```bash
ollama pull qwen2.5-coder:7b
```

**关于 `PROFILE_MODEL`**，建议使用轻量级本地模型以获得最佳性能 —— 画像提取只是简单的结构化 JSON 抽取，不需要大模型。推荐选项：

```bash
ollama pull qwen2.5:0.5b     # 最快，占用内存最少
ollama pull llama3.2:1b      # 稍强一些，仍然非常轻量
ollama pull gemma3:1b        # 速度与精度的良好平衡
```

> 为 `PROFILE_MODEL` 使用轻量级本地模型，可以让画像更新真正在后台无感运行，不与主模型争抢资源。

### 3. 启动数据库

```bash
docker compose up -d
```

这将在 **5433 端口**启动一个带有 pgvector 扩展的 PostgreSQL 实例。`init.sql` 文件会在首次运行时自动创建所需的数据库表。

> Windows 用户请使用 Docker Desktop，并在 PowerShell 或 CMD 中执行命令。Mac 用户需要在运行 `docker compose` 前先打开 Docker Desktop。

### 4. 配置环境变量

复制示例环境变量文件并填写你的配置：

```bash
cp .env.exmaple .env
```

编辑 `.env` 文件：

```env
BASE_URL=http://localhost:11434
MODEL=你的模型名称
DATABASE_URL=postgresql://myuser:mypassword@localhost:5433/agent_memory
EMBEDDING_MODEL=nomic-embed-text
PROFILE_MODEL=你的轻量模型名称   # 可选，默认使用 MODEL
```

`PROFILE_MODEL` 用于后台画像提取，推荐使用较小较快的模型，因为这个任务只是结构化的 JSON 抽取。

---

## 运行智能体

### 终端（交互式命令行）

```bash
python3 my_agent_loop.py
```

在 `User>` 提示符后输入消息。输入 `/exit` 退出。

### 微信 ACP

> **已知问题：** 通过微信 ACP 发送的 CLI 命令（如 `/exit`、`/help`）目前无法正常工作。这是已知限制，正在修复中 —— 目前请在终端中使用命令行功能。

按以下步骤启用微信 ACP 桥接：

**1. 更新 `wechat-acp.config.json`**，填入你自己的路径：

```json
{
  "agents": {
    "my-agent": {
      "label": "My Custom Agent",
      "command": "python3",
      "args": ["/你的/绝对/路径/custom-agent/acp_agent.py"]
    }
  },
  "agent": {
    "preset": "my-agent",
    "cwd": "/你的/绝对/路径/custom-agent"
  }
}
```

将 `/你的/绝对/路径/custom-agent` 替换为本项目在你机器上的实际路径：

- **Mac/Linux**：在项目目录中执行 `pwd` 获取路径
- **Windows**：使用正斜杠或转义反斜杠，例如 `C:/Users/yourname/custom-agent`

**2. 启动 ACP 桥接服务：**

```bash
npx wechat-acp wechat-acp.config.json
```

`npx` 需要安装 Node.js 才能使用。执行后将启动 ACP 服务并将你的微信账号接入智能体。

---

## 计划功能

以下功能正在规划或开发中。由于项目仍处于早期阶段，部分功能可能实现不完整或存在问题 —— 错误处理将逐步补充完善。

### 记忆与遗忘
- 遗忘命令 —— 允许用户或智能体通过关键词或 ID 删除特定记忆，避免过时信息污染后续对话
- 完整向量搜索 —— 语义搜索管道已存在但需要调优，将 `top_k` 和历史记录限制暴露为 `.env` 配置项
- 记忆压缩/摘要 —— 当对话历史过长时，将旧对话压缩为单条摘要记录，控制上下文窗口大小
- 主题标签 —— 为记忆打上主题标签，使语义搜索可按范围筛选（例如只搜索与代码相关的记忆）

### 视觉能力
- 通过 ACP 接口接收图片和文件上传
- 将图片传递给支持多模态的 Ollama 模型（如 `llava`、`gemma3`），使用 `images` 字段
- `describe_image` 工具 —— 输入文件路径，返回图片的文字描述
- 通过 `PyMuPDF` 支持 PDF —— 提取文本或将页面渲染为图片传给视觉模型
- 将图片描述以相同的嵌入管道存入记忆

### 更好的记忆系统
- 结构化记忆分层 —— 分离情节记忆（对话）、语义记忆（事实）和程序记忆（用户偏好）
- `search_memory(query)` 工具 —— 让智能体主动查询自己的历史记忆，而不仅依赖被动注入
- `list_recent_memory(n)` 工具 —— 返回最近 n 条记忆的摘要
- 独立的 `profiles` 表 —— 目前用户画像与消息记录混存，将其迁移到独立的表中，便于查询和更新
- `update_profile(key, value)` 工具 —— 当用户明确陈述事实时，智能体可直接更新画像字段

### 多智能体与规划
- 规划智能体 —— 专门的子智能体，在执行前将复杂任务拆解为分步计划
- 并行智能体 —— 使用 `asyncio` 并发启动多个子智能体完成研究或多部分任务，汇总所有结果
- 智能体间记忆共享 —— 子智能体目前无法访问父智能体的记忆，计划在启动时传递相关上下文并将结果写回
- 专业工作智能体 —— 独立的网络研究、代码编写、文件管理等智能体，由规划者统一调度

### 更多工具
- `summarise_url(url)` —— 抓取网页并返回简短摘要
- `download_file(url, dest)` —— 将文件下载到工作目录
- `list_files(path)` —— 递归列出目录结构及文件大小
- `grep(pattern, path)` —— 按正则表达式搜索文件内容
- `run_python(code)` —— 在子进程沙箱中执行 Python 代码片段并返回 stdout/stderr
- `get_time()` —— 返回当前日期和时间
- `set_reminder(message, delay_seconds)` —— 设置一条定时提醒
- `clipboard_read()` / `clipboard_write(text)` —— 与 macOS 剪贴板交互

### CLI 命令
- `/history` —— 在终端打印最近的对话记录
- `/clear` —— 重置上下文而无需重启进程
- `/profile` —— 打印当前存储的用户画像
- `/forget <关键词>` —— 删除匹配关键词的记忆
- `/tools` —— 列出所有可用工具及描述
- `/model <名称>` —— 在会话中途切换模型
- 微信 ACP 命令支持 —— 通过微信发送的 CLI 命令目前无法使用，计划与终端命令行完全对齐

### 体验与可观测性
- 统一 stdout 输出，带 `Assistant>` 前缀，通过 `colorama` 着色（助手绿色、工具调用黄色、错误红色）
- 模型思考期间（首个 token 到达前）显示加载动画
- `MAX_TOOL_DEPTH` 环境变量，限制 `_execute` 的递归深度（目前无上限，工具循环失控会导致栈溢出）
- 将所有工具调用及结果以 JSONL 格式记录到 `logs/` 目录，便于调试和回放
