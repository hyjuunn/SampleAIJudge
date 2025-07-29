import google.generativeai as genai
from typing import List, Dict

class GoogleClient:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
    
    def chat(self, messages, model="gemini-2.5-pro", temperature=0):
        """
        Google Gemini API 호출
        
        Returns:
            모델의 응답 내용
        """
        contents = self._convert_openai_messages_to_gemini_contents(messages)
        genai_model = genai.GenerativeModel(
            model_name=model,
            generation_config=genai.GenerationConfig(
                temperature=temperature
            )
        )
        response = genai_model.generate_content(
            contents=contents
        )
        return response.text
    
    def _convert_openai_messages_to_gemini_contents(self, messages) -> List[Dict]:
        """
        OpenAI 형식의 메시지를 Google Gemini API에 맞는 형식으로 변환
        """
        gemini_contents = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            parts = []
            if isinstance(content, str):
                parts.append({"text": content})
            elif isinstance(content, list):
                # TODO: 나중에 추가
                pass

            gemini_role = "model" if role == "assistant" else "user"
            gemini_contents.append({
                "role": gemini_role,
                "parts": parts
            })
        return gemini_contents