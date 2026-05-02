# Custom AI Agent

[中文版](README_CN.md)

> **This project is actively in development. Expect bugs, incomplete features, and rough edges. Error handling and try/catch coverage will be improved over time.**

A local AI agent with persistent memory, semantic search, user profile tracking, tool use, and WeChat ACP integration — all running on your own hardware via Ollama.

---

## How it works

- Conversations are stored in PostgreSQL with vector embeddings for semantic memory recall
- A background profile extractor builds a structured developer profile from your conversations automatically
- The agent can use tools: run bash commands, search the web, read/write files, and more
- Connects to WeChat via ACP (Agent Communication Protocol) so you can chat with your agent through WeChat

---

## Prerequisites

Install these before anything else:

| Dependency | Why |
|---|---|
| [Python 3.10+](https://www.python.org/downloads/) | Runs the agent |
| [Node.js 18+](https://nodejs.org/) | Required to run the WeChat ACP bridge (`npx wechat-acp`) |
| [Ollama](https://ollama.com/download) | Serves the LLM and embedding models locally |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Runs the PostgreSQL + pgvector database |

> **Does `pip install ollama` replace installing Ollama?**
> No. The `ollama` Python package (installed via `requirements.txt`) is just an HTTP client SDK — it lets Python talk to the Ollama server. You still need the **Ollama application** installed and running on your machine to actually load and serve models. Think of it like installing the `psycopg2` database driver — it doesn't give you a database, it just lets you connect to one.

---

## Setup

### 1. Clone and install Python dependencies

```bash
git clone <your-repo-url>
cd custom-agent
pip install -r requirements.txt
```

### 2. Pull models via Ollama

Make sure Ollama is running first (open the Ollama app or run `ollama serve`), then pull the embedding model:

```bash
ollama pull nomic-embed-text
```

**For your main model (`MODEL`) and profile model (`PROFILE_MODEL`):**

- If you are using a **cloud model** (model name ends in `:cloud`, e.g. `qwen3-coder-next:cloud`), Ollama streams it from the cloud — no pull needed, just set the name in `.env` and run.
- If you are using a **local model** (no `:cloud` suffix, e.g. `qwen2.5-coder:7b`), you must pull it first:

```bash
ollama pull qwen2.5-coder:7b
```

**For `PROFILE_MODEL`**, use a lightweight local model for best performance — profile extraction is simple structured JSON work that does not need a large model. Recommended options:

```bash
ollama pull qwen2.5:0.5b     # fastest, minimal RAM
ollama pull llama3.2:1b      # slightly more capable, still very light
ollama pull gemma3:1b        # good balance of speed and accuracy
```

> Using a lightweight local model for `PROFILE_MODEL` keeps profile updates truly non-blocking in the background without competing for resources with your main model.

### 3. Start the database

```bash
docker compose up -d
```

This starts a PostgreSQL instance with the pgvector extension on **port 5433**. The `init.sql` file sets up the required tables automatically on first run.

> On Windows, use Docker Desktop and run the command in PowerShell or CMD. On Mac, Docker Desktop must be open before running `docker compose`.

### 4. Configure environment variables

Copy the example env file and fill in your values:

```bash
cp .env.exmaple .env
```

Edit `.env`:

```env
BASE_URL=http://localhost:11434
MODEL=your-model-name
DATABASE_URL=postgresql://myuser:mypassword@localhost:5433/agent_memory
EMBEDDING_MODEL=nomic-embed-text
PROFILE_MODEL=your-lighter-model-name   # optional, falls back to MODEL
```

The `PROFILE_MODEL` is used for background profile extraction — a smaller/faster model works well here since it's just structured JSON extraction.

---

## Running the agent

### Terminal (REPL)

```bash
python3 my_agent_loop.py
```

Type your messages at the `User>` prompt. Use `/exit` to quit.

### WeChat ACP

> **Known issue:** CLI commands (e.g. `/exit`, `/help`) do not currently work when sent through the WeChat ACP interface. This is a known limitation being worked on — for now, use the terminal REPL for commands.

Enable the WeChat ACP bridge so you can chat with your agent through WeChat:

**1. Update `wechat-acp.config.json`** with your own paths:

```json
{
  "agents": {
    "my-agent": {
      "label": "My Custom Agent",
      "command": "python3",
      "args": ["/YOUR/ABSOLUTE/PATH/custom-agent/acp_agent.py"]
    }
  },
  "agent": {
    "preset": "my-agent",
    "cwd": "/YOUR/ABSOLUTE/PATH/custom-agent"
  }
}
```

Replace `/YOUR/ABSOLUTE/PATH/custom-agent` with the actual path to this project on your machine.

- On **Mac/Linux**: run `pwd` inside the project folder to get the path
- On **Windows**: use forward slashes or escape backslashes, e.g. `C:/Users/yourname/custom-agent`

**2. Start the ACP bridge:**

```bash
npx wechat-acp wechat-acp.config.json
```

Node.js must be installed for `npx` to work. This will launch the ACP server and connect your WeChat account to the agent.

---

## Planned features

The following features are planned or actively in development. Since this project is still early-stage, expect partial implementations and things that don't work perfectly yet — try/catch and error handling will be added progressively.

### Memory & Forget
- Forget command — let the user or agent delete specific memories by keyword or ID so stale facts stop polluting future context
- Full vector search — the semantic search pipeline exists but needs tuning: expose `top_k` and history limit as `.env` config values
- Memory compaction / summarisation — when conversation history gets too long, compress old turns into a single summary record to keep the context window manageable
- Topic tagging — tag memories by subject so semantic search can be scoped (e.g. only search code-related memories)

### Vision
- Accept image and file uploads through the ACP interface
- Pass images to multimodal Ollama models (e.g. `llava`, `gemma3`) using the `images` field in the chat call
- `describe_image` tool — takes a file path, returns a text description
- PDF support via `PyMuPDF` — extract text or render pages as images for vision models
- Store image descriptions in memory with the same embedding pipeline as text

### Better Memory System
- Structured memory categories — separate episodic (conversations), semantic (facts), and procedural (how the user likes things done) memory layers
- `search_memory(query)` tool — let the agent explicitly query its own past instead of only injecting memories passively
- `list_recent_memory(n)` tool — return the last n memory entries as a summary
- Dedicated `profiles` table — currently the user profile lives alongside messages; move it to its own table for cleaner querying and updates
- `update_profile(key, value)` tool — agent can directly update profile fields when the user states a clear fact

### Multi-Agent & Planning
- Planning agent — a dedicated sub-agent that breaks complex tasks into a step-by-step plan before execution
- Parallel agents — spawn N sub-agents concurrently using `asyncio` for research or multi-part tasks, collect all results
- Memory-sharing between agents — sub-agents currently have no access to the parent's memory; pass relevant context on spawn and write results back
- Specialised worker agents — separate agents for web research, code writing, file management, etc., orchestrated by a planner

### More Tools
- `summarise_url(url)` — fetch a page and return a short summary
- `download_file(url, dest)` — download a file to the working directory
- `list_files(path)` — recursive directory listing with file sizes
- `grep(pattern, path)` — search file contents by regex
- `run_python(code)` — execute a Python snippet in a subprocess sandbox and return stdout/stderr
- `get_time()` — return current date/time
- `set_reminder(message, delay_seconds)` — schedule a note
- `clipboard_read()` / `clipboard_write(text)` — interact with the macOS clipboard

### CLI Commands
- `/history` — print recent conversation turns in the terminal
- `/clear` — reset the in-memory context without restarting the process
- `/profile` — print the current user profile as stored
- `/forget <keyword>` — delete memories matching a keyword
- `/tools` — list all available tools and their descriptions
- `/model <name>` — switch the active model mid-session
- WeChat ACP command support — CLI commands sent through WeChat currently do not work; full parity with the terminal REPL is planned

### UX & Observability
- Unified stdout output with `Assistant>` prefix, colour coding via `colorama` (green for assistant, yellow for tool calls, red for errors)
- Spinner while the model is thinking before the first token arrives
- `MAX_TOOL_DEPTH` env var to cap recursion in `_execute` (currently unbounded — a runaway tool loop will stack overflow)
- JSONL tool call logging to `logs/` for debugging and replay
