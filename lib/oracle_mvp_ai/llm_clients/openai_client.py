import openai
from openai import OpenAI, AsyncOpenAI
from typing import List, Dict
import os

class OpenAIClient:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.async_client = AsyncOpenAI(api_key=api_key)

    def chat(self, messages, model="gpt-4o", temperature=0, seed=42):
        """
        OpenAI API 호출
            
        Returns:
            모델의 응답 내용
        """
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            seed=seed
        )
        return response.choices[0].message.content 

    async def chat_async(self, messages, model="gpt-4o", temperature=0, seed=42):
        response = await self.async_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            seed=seed
        )
        return response.choices[0].message.content 

    def create_embedding(self, text: str, model: str = "text-embedding-3-small") -> list:
        """
        텍스트의 임베딩 벡터 생성 (동기 버전)
        
        Args:
            text: 임베딩을 생성할 텍스트
            model: 사용할 임베딩 모델
            
        Returns:
            임베딩 벡터
        """
        response = self.client.embeddings.create(
            model=model,
            input=text,
            encoding_format="float"
        )
        return response.data[0].embedding 

    async def create_embedding_async(self, text: str, model: str = "text-embedding-3-small") -> list:
        """
        텍스트의 임베딩 벡터 생성 (비동기 버전)
        
        Args:
            text: 임베딩을 생성할 텍스트
            model: 사용할 임베딩 모델
            
        Returns:
            임베딩 벡터
        """
        response = await self.async_client.embeddings.create(
            model=model,
            input=text,
            encoding_format="float"
        )
        return response.data[0].embedding 

    async def web_search_chat(self, messages, model: str = "gpt-4o-search-preview"):
        try:
            response = await self.async_client.chat.completions.create(
                model=model,
                messages=messages,
                web_search_options={}
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Web search error: {e}")
            raise e

    async def web_search_mini_chat(self, messages, model: str = "gpt-4o-mini-search-preview"):
        try:
            response = await self.async_client.chat.completions.create(
                model=model,
                messages=messages,
                web_search_options={}
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Web search error: {e}")
            raise e