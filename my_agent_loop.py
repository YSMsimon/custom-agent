from ollama import Client
from typing import List, Dict, Optional
from common.config import config
from run_bash import tools, tool_handler, all_tools
from to_do import ToDoManager
from db import DB
import json
import re
import sys
import threading


class Agent:
    def __init__(self, cfg: config, tools: Optional[List] = tools, db: DB = None, user_id: str = 'default_user'):
        self.config = cfg
        self.tools = tools
        self.todo_manager = ToDoManager()
        self.db = db
        self.user_id = user_id
        self.client = Client(host=cfg.base_url)
        self._system_prompt = ''
        self._last_user_message = ''

    def get_embedding(self, text: str) -> list:
        response = self.client.embeddings(model=self.config.embedding_model, prompt=text)
        embedding = response.embedding
        return embedding

    def _build_system_prompt(self) -> str:
        profile = self.db.get_user_profile(self.user_id)
        profile_text = json.dumps(profile, indent=2) if profile else "No profile yet."
        return self.config.system_prompt.format(user_profile=profile_text)

    def _build_messages(self, user_message: str) -> List[Dict]:
        
        history, recent_ids = self.db.get_recent_history(self.user_id, limit=10000)

        embedding = self.get_embedding(user_message)
        
        memories = self.db.semantic_search(
            embedding, top_k=5, user_id=self.user_id, exclude_ids=recent_ids
        )

        messages = list(history)

        """
        if memories:
            rag_lines = "\n".join(f"[{m['role']}]: {m['content']}" for m in memories)
            messages.append({'role': 'system', 'content': f"Relevant past context:\n{rag_lines}"})
        """
        self._save_turn({'role': 'user', 'content': user_message})
        messages.append({'role': 'user', 'content': user_message})
        return messages

    def _update_profile(self, user_message: str, assistant_response: str):
        existing = self.db.get_user_profile(self.user_id)
        schema_example = json.dumps({
            "identity": {
                "name": "string or null",
                "nickname": "string or null",
                "age": "number or null",
                "location": "string or null",
                "timezone": "string or null",
                "occupation": "string or null",
                "education": "string or null"
            },

            "professional_profile": {
                "job_title": "string or null",
                "experience_years": "number or null",
                "background_summary": "string",
                "skills": [
                    {
                        "name": "Python",
                        "level": "beginner/intermediate/advanced",
                        "years": 2
                    }
                ],
                "languages": ["python", "typescript", "go"],
                "frameworks": ["fastapi", "react", "spring boot"],
                "tools": ["docker", "git", "postgresql"]
            },

            "online_presence": {
                "github_username": "string or null",
                "github_repos": [
                    {
                        "name": "receipt-tracker",
                        "description": "AI receipt parser app",
                        "url": "string"
                    }
                ],
                "website": "string or null",
                "linkedin": "string or null",
                "youtube_channel": "string or null",
                "twitter": "string or null"
            },

            "current_projects": [
                {
                    "name": "Trading Bot",
                    "description": "Solana multi-wallet bot",
                    "status": "active",
                    "tech_stack": ["python", "solana", "react"],
                    "goals": ["wallet management", "automated trading"]
                }
            ],

            "learning_profile": {
                "learning_goals": [
                    "Learn React with TypeScript",
                    "Understand vector databases"
                ],
                "current_focus": "agent development",
                "preferred_learning_style": [
                    "hands-on examples",
                    "step-by-step breakdowns"
                ],
                "difficulty_preference": "beginner-friendly but production-focused"
            },

            "interests": {
                "technical": ["LLMs", "RAG", "agent memory", "backend systems"],
                "business": ["startups", "fintech"],
                "personal": ["fitness", "photography"]
            },

            "preferences": {
                "editor": "vscode",
                "os": "mac",
                "communication_style": "concise but technical",
                "response_format": ["examples", "code", "architecture diagrams"],
                "likes": ["clean code", "project-based learning"],
                "dislikes": ["too much theory"]
            },

            "behavioral_patterns": {
                "common_questions": [
                    "backend architecture",
                    "database design",
                    "AI agent implementation"
                ],
                "frequent_topics": ["FastAPI", "PostgreSQL", "React"],
                "project_stage": "building MVPs"
            },

            "constraints": {
                "budget": "low/free tools preferred",
                "hardware": "MacBook",
                "deployment_targets": ["local", "cloud", "mobile"]
            },

            "conversation_memory": {
                "last_active_topics": [
                    "vector database memory",
                    "React TypeScript",
                    "GitHub collaboration"
                ],
                "saved_context": [
                    "working on receipt tracker",
                    "learning Spring Boot"
                ]
            },

            "goals": {
                "short_term": [
                    "Build fullstack apps",
                    "Learn agent architecture"
                ],
                "long_term": [
                    "Become freelance developer",
                    "Launch SaaS products"
                ]
            },

            "metadata": {
                "profile_version": "1.0",
                "created_at": "ISO datetime",
                "updated_at": "ISO datetime"
            }
        }, indent = 2)

        base_prompt = f"""
        You are a structured memory/profile extraction engine.

        Your task:
        Update the user's profile JSON using ONLY explicit facts stated by the user
        in the provided conversation.

        CORE RULES:
        1. Extract ONLY information directly stated by the user.
        2. Never infer, assume, guess, or deduce missing details.
        - Example:
            User says "I use FastAPI" -> allowed: add "FastAPI"
            User says "I build APIs" -> NOT allowed: infer FastAPI
        3. Preserve all existing fields unless explicitly updated.
        4. If the user explicitly corrects previous information, overwrite it.
        5. If user explicitly says unknown/none/null, set field to null.
        6. Do not remove fields unless explicitly contradicted or nulled.
        7. Ignore assistant suggestions unless user confirmed them.
        8. Output ONLY valid raw JSON.
        9. No markdown, explanations, comments, or code fences.

        MERGING RULES:
        - Strings: overwrite only when explicitly updated.
        - Lists:
            - append unique new items
            - do not duplicate existing values
        - Objects:
            - recursively merge fields
        - Arrays of objects:
            - merge by "name" when possible

        PROFILE SCHEMA:
        {schema_example}

        EXISTING PROFILE:
        {json.dumps(existing, indent=2)}

        CURRENT CONVERSATION:
        USER: {user_message}
        ASSISTANT: {assistant_response}

        UPDATED PROFILE JSON:
        """

        messages = [{'role': 'user', 'content': base_prompt}]
        max_retries = 3
        for _ in range(max_retries):
            resp = self.client.chat(model=self.config.profile_model, messages=messages)
            text = resp.message.content.strip()
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
            if match:
                text = match.group(1).strip()
            try:
                self.db.update_user_profile(self.user_id, json.loads(text))
                return
            except json.JSONDecodeError as e:
                error_feedback = (
                    f"Your previous response failed JSON parsing.\n"
                    f"Error: {e}\n"
                    f"Occurred at character position: {e.pos if hasattr(e, 'pos') else 'unknown'}\n"
                    f"Raw response that failed:\n{text}\n\n"
                    f"Fix the JSON and return only a valid JSON object matching this schema:\n{schema_example}"
                )
                messages.append({'role': 'assistant', 'content': resp.message.content})
                messages.append({'role': 'user', 'content': error_feedback})

    def _save_turn(self, new_messages: Dict):
        role = new_messages.get('role')
        content = new_messages.get('content')
        embedding = self.get_embedding(content)
        tool_call_id = new_messages.get('tool_call_id')
        self.db.add_message(self.user_id, role, content, embedding, tool_call_id)

        if role == 'user':
            self._last_user_message = content
        elif role == 'assistant' and self._last_user_message:
            threading.Thread(
                target=self._update_profile,
                args=(self._last_user_message, content),
                daemon=True
            ).start()

    def run(self, user_message: str) -> str:
        self._system_prompt = self._build_system_prompt()
        messages = self._build_messages(user_message)
        final_messages = self._execute(messages)
        for msg in reversed(final_messages):
            if isinstance(msg, dict) and msg.get('role') == 'assistant':
                return msg.get('content', '')
        return ''

    def _execute(self, messages: List[Dict]) -> List[Dict]:
        response = self.client.chat(
            model=self.config.model,
            messages=[{'role': 'system', 'content': self._system_prompt}] + messages,
            tools=self.tools,
            stream=True
        )

        full_content = ''
        tool_calls = None
        for chunk in response:
            if chunk.message.content:
                full_content += chunk.message.content
                print(chunk.message.content, end='', flush=True, file=sys.stderr)
            if chunk.message.tool_calls:
                tool_calls = chunk.message.tool_calls
        print(file=sys.stderr)

        self._save_turn({'role': 'assistant', 'content': full_content})
        messages = messages + [{'role': 'assistant', 'content': full_content}]

        if not tool_calls:
            return messages

        for tool_call in tool_calls:
            tool_call_id = getattr(tool_call, 'id', None)
            name = tool_call.function.name
            args = tool_call.function.arguments
            result = tool_handler[name](**args)
            self._save_turn({'role': 'tool', 'content': f"Name: {name}, Arguments: {args}, Result: {result}", 'tool_call_id': tool_call_id})
            messages.append({'role': 'tool', 'content': f"Name: {name}, Arguments: {args}, Result: {result}", 'tool_call_id': tool_call_id})
        return self._execute(messages)


if __name__ == '__main__':
    db = DB()
    cfg = config()
    agent = Agent(cfg, tools=all_tools, db=db)
    try:
        while True:
            user_input = input("User> ")
            if user_input == "/help":
                pass
            if user_input == "/exit":
                print("Exiting...")
                break
            agent.run(user_input)
    except KeyboardInterrupt:
        print("\nExiting...")
        db.close()
