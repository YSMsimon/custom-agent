from ollama import Client
from typing import List, Dict, Optional
from common.config import config
from run_bash import tools, tool_handler, all_tools
from to_do import ToDoManager
from db import DB
import json
import re


class Agent:
    def __init__(self, cfg: config, tools: Optional[List] = tools, db: DB = None, user_id: str = 'default_user'):
        self.config = cfg
        self.tools = tools
        self.todo_manager = ToDoManager()
        self.db = db
        self.user_id = user_id
        self.client = Client(host=cfg.base_url)
        self._system_prompt = ''

    def get_embedding(self, text: str) -> list:
        response = self.client.embeddings(model=self.config.embedding_model, prompt=text)
        return response.embedding

    def _build_system_prompt(self) -> str:
        profile = self.db.get_user_profile(self.user_id)
        profile_text = json.dumps(profile, indent=2) if profile else "No profile yet."
        return self.config.system_prompt.format(user_profile=profile_text)

    def _build_messages(self, user_message: str) -> List[Dict]:
        
        history, recent_ids = self.db.get_recent_history(self.user_id, limit=10)

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
        prompt = (
            "Extract any factual preferences or personal details the user stated in this exchange. "
            "Merge them into the existing profile JSON. Only include facts explicitly stated by the user. "
            "Return only valid JSON, no commentary.\n"
            f"Existing profile: {json.dumps(existing)}\n"
            f"User: {user_message}\nAssistant: {assistant_response}"
        )
        resp = self.client.chat(
            model=self.config.model,
            messages=[{'role': 'user', 'content': prompt}]
        )
        text = resp.message.content.strip()
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if match:
            text = match.group(1).strip()
        try:
            self.db.update_user_profile(self.user_id, json.loads(text))
        except json.JSONDecodeError:
            pass

    def _save_turn(self, new_messages: Dict):
        role = new_messages.get('role')
        content = new_messages.get('content')
        embedding = self.get_embedding(content) if role in ('user', 'assistant') else None
        tool_call_id = new_messages.get('tool_call_id')
        self.db.add_message(self.user_id, role, content, embedding, tool_call_id)
        
        #self._update_profile(user_message, final_assistant)

    def run(self, user_message: str) -> str:
        self._system_prompt = self._build_system_prompt()
        messages = self._build_messages(user_message)
        self._execute(messages)
        return

    def _execute(self, messages: List[Dict]) -> List[Dict]:
        response = self.client.chat(
            model=self.config.model,
            messages=messages,
            tools=self.tools,
            stream=True
        )

        full_content = ''
        tool_calls = None
        for chunk in response:
            if chunk.message.content:
                full_content += chunk.message.content
                print(chunk.message.content, end='', flush=True)
            if chunk.message.tool_calls:
                tool_calls = chunk.message.tool_calls
        print()

        self._save_turn({'role': 'assistant', 'content': full_content})
        messages = messages + [{'role': 'assistant', 'content': full_content}]

        if not tool_calls:
            return messages

        for tool_call in tool_calls:
            tool_call_id = getattr(tool_call, 'id', None)
            name = tool_call.function.name
            args = tool_call.function.arguments
            result = tool_handler[name](**args)
            self._save_turn({'role': 'tool', 'content': result, 'tool_call_id': tool_call_id})
            messages.append({'role': 'tool', 'content': result, 'tool_call_id': tool_call_id})
            if name == 'to_do':
                print("\n=== CURRENT TASK LIST ===")
                print(result)
                print("=========================\n")

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
