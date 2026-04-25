from ollama import Client
from typing import List, Dict, Optional
from common.config import config
from run_bash import tools, tool_handler, all_tools
from to_do import ToDoManager

class Agent:
    def __init__(self, config:config, tools: Optional[List] = tools):
        self.config = config
        self.tools = tools
        self.todo_manager = ToDoManager()
    
    def run(self, messages: List[Dict]) -> List[Dict]:
        prompt =  [{'role': 'assistant',
                           'content': self.config.system_prompt                     
                         }]
        client = Client(
            host=self.config.base_url
        )
        response = client.chat(
                            model = self.config.model,
                            messages = prompt + messages,
                            tools = self.tools
                            )
        messages = messages + [{'role': 'assistant',
                            'content': response.message.content}]
        
        if not response.message.tool_calls:
            return messages
        
        for tool_call in response.message.tool_calls:
            tool_call_id = tool_call.get('id')
            name = tool_call.function.name
            args = tool_call.function.arguments
            
            tool = tool_handler.get(name)
            result = tool(**args)
            
            messages.append({'role': 'tool', 'content': result, 'tool_call_id':tool_call_id })
            
            if name == 'to_do':
                print("\n=== CURRENT TASK LIST ===")
                print(result)
                print("=========================\n")
        
        return self.run(messages)

if __name__ == '__main__':
    agent = Agent(config(), tools=all_tools)
    history = []
    try:
        while True:
            i = input("User>")
            history.append({'role':'user', 'content': i})
            history = agent.run(history)
            print("AI>" + history[-1].get('content'))
    except KeyboardInterrupt:
            print("\nExiting... ")