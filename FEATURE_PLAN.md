# Feature Roadmap

## 1. Memory & RAG (In Progress)

**Current state:** `db.py` stores messages with embeddings and does semantic search. `_build_messages` retrieves recent history + top-5 semantic matches. Profile update is commented out.

### To Do
- [ ] Re-enable `_update_profile` — currently commented out in `_save_turn`. Wire it back in after assistant turns so the profile grows automatically.
- [ ] Tune `get_recent_history` limit and `semantic_search` top_k — expose them as config values in `.env` so they can be tuned without code changes.
- [ ] Add a `forget` tool — lets the user or agent delete specific memories by ID or keyword so stale facts don't pollute future context.
- [ ] Summarise long history — when the message history exceeds a token budget, run a summarisation pass and store the summary as a single compressed memory record instead of hundreds of individual turns.
- [ ] Tag memories by topic — add a `tags` column to the messages table so semantic search can be scoped (e.g. "search only in code-related memories").

---

## 2. Vision — Images, Photos, Files via ACP

**Goal:** Accept uploaded images or files through the ACP interface and pass them to a vision-capable model.

### Steps
- [ ] Add an `accept_file` tool that receives a file path or base64 blob from ACP and saves it to a temp directory.
- [ ] In `_execute`, detect when a tool result or user message contains an image path and encode it to base64.
- [ ] Add `images` field to the Ollama `chat` call — Ollama's multimodal models (e.g. `llava`, `gemma3`) accept `{"role": "user", "content": "...", "images": ["<base64>"]}`.
- [ ] Add a `describe_image` tool that wraps this — takes a file path, returns a text description.
- [ ] Handle PDFs: use `PyMuPDF` (`fitz`) to extract text and/or render pages as images for vision models.
- [ ] Store image descriptions in memory with the same embedding pipeline as text.

**New dependency:** `pymupdf`, `Pillow`

---

## 3. More Agent Tools

### Web & Research
- [ ] `summarise_url(url)` — fetch a page and return a 3-sentence summary (pipe `fetch_text` through the LLM).
- [ ] `download_file(url, dest)` — download a file to the working directory.

### Code & Dev
- [ ] `list_files(path)` — recursive directory listing with file sizes.
- [ ] `grep(pattern, path)` — search file contents by regex.
- [ ] `run_python(code)` — execute a Python snippet in a subprocess sandbox and return stdout/stderr. Useful for math, data transforms, quick scripts.

### System & Productivity
- [ ] `get_time()` — return current date/time (agents are often confused about this).
- [ ] `set_reminder(message, delay_seconds)` — write a scheduled note (can integrate with ACP push or just print).
- [ ] `clipboard_read()` / `clipboard_write(text)` — interact with the macOS clipboard via `pbpaste`/`pbcopy`.

### Memory Management
- [ ] `search_memory(query)` — expose semantic memory search as an explicit tool so the agent can self-query its own past.
- [ ] `list_recent_memory(n)` — return the last n memory entries as a summary.

---

## 4. User Profile — Richer & Auto-Updating

**Current state:** Profile is a flat JSON blob updated by a prompted LLM call (currently disabled).

### Steps
- [ ] Re-enable profile updates after each assistant turn (see Memory section).
- [ ] Structure the profile schema — define fields like `name`, `preferences`, `expertise_level`, `ongoing_projects`, `timezone` so the LLM extracts into a known shape.
- [ ] Add a `update_profile(key, value)` tool the agent can call directly when the user states a clear fact ("my name is X", "I prefer Python").
- [ ] Add a `show_profile()` tool so the user can see what the agent knows about them.
- [ ] Persist profile separately from messages — currently both live in `messages` table. A dedicated `profiles` table makes it easier to query and update.

---

## 5. Sub-Agent & Planning Improvements

**Current state:** `run_sub_agent` exists but sub-agents share no memory with the parent and have no tool state.

- [ ] Pass relevant memory context when spawning a sub-agent — serialize the top-k semantic memories into the sub-agent's system prompt.
- [ ] Let sub-agents write back results to the parent's memory table.
- [ ] Add a `parallel_agents(prompts: list[str])` tool — spawn N sub-agents concurrently using `asyncio` and return all results. Useful for research tasks.

---

## 6. Streaming Output to Terminal (UX)

**Current state:** Model output is streamed to `stderr` while the user prompt is on `stdout`. This works but the separation is awkward.

- [ ] Unify output to `stdout` with a clear `Assistant>` prefix matching the `User>` prompt.
- [ ] Add colour via `colorama` — green for assistant, yellow for tool calls, red for errors.
- [ ] Show a spinner while the model is thinking (before the first token arrives).

---

## 7. ACP Integration — Richer Message Types

**Current state:** `acp_agent.py` exists. The main loop is separate.

- [ ] Merge ACP agent with the main `Agent` class so ACP messages flow through the same memory/tool pipeline.
- [ ] Handle ACP `file` message type — route uploaded files to the `accept_file` tool (see Vision section).
- [ ] Send structured ACP responses (markdown, file attachments) back rather than plain text.

---

## 8. Config & Observability

- [ ] Add `MAX_TOOL_DEPTH` env var to cap recursion in `_execute` (currently unbounded — a runaway tool loop will stack-overflow).
- [ ] Log every tool call + result to a `logs/` JSONL file for debugging and replay.
- [ ] Add `/history` command to the REPL to print recent conversation turns.
- [ ] Add `/clear` command to reset the in-memory context without restarting.
- [ ] Add `/profile` command to print the current user profile.

---

## Priority Order (Suggested)

| # | Feature | Why first |
|---|---|---|
| 1 | Fix `MAX_TOOL_DEPTH` cap | Safety — prevents crash on runaway loops |
| 2 | Re-enable user profile updates | Already coded, just commented out |
| 3 | `run_python` sandbox tool | High leverage for math/data tasks |
| 4 | Vision / image upload | Core ACP differentiator |
| 5 | Memory forget + search tools | Makes RAG actually useful to the user |
| 6 | Richer profile schema | Better personalisation |
| 7 | Parallel sub-agents | Power user feature |
