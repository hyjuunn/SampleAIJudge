from anthropic import Anthropic
from typing import List, Dict

class AnthropicClient:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)

    def chat(self, messages, model="claude-3-5-sonnet-20240620", temperature=0):
        """
        Anthropic Claude API 호출

        Returns:
            모델의 응답 내용
        """
        messages, system_prompt = self._convert_openai_messages_to_anthropic_messages(messages)
        response = self.client.messages.create(
            model=model,
            messages=messages,
            system=system_prompt,
            temperature=temperature,
            max_tokens= 8000# required
        )
        #[{"type": "text", "text": "Hi, I'm Claude."}]
        for content_block in response.content:
            if content_block.type == "text":
                return content_block.text
        return ""
    
    def _convert_openai_messages_to_anthropic_messages(self, messages) -> List[Dict]:
        """
        OpenAI 형식의 메세지를 Anthropic Claude API에 맞는 형식으로 변환
        """
        claude_messages = []
        for msg in messages: 
            role = msg["role"]
            content = msg["content"]
            system_prompt = content
            if role == 'system':
                system_prompt = content
                continue
            parts = []
            if isinstance(content, str):
                parts = content
            elif isinstance(content, list):
                # TODO: 나중에 추가
                pass
            
            claude_role = "assistant" if role == "assistant" else "user"
            claude_messages.append({
                "role": claude_role,
                "content": parts
            })
        return claude_messages, system_prompt

