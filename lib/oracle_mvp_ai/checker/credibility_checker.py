import asyncio
from typing import List, Dict, Any
import aiohttp
from openai import AsyncOpenAI
from ..llm_clients.openai_client import OpenAIClient
import yaml

class CredibilityChecker:
    def __init__(self, openai_client: OpenAIClient):
        self.client = openai_client

    async def get_factual_info(self, topic_title: str, opinions: List[str], prompt_yaml: Dict) -> List[str]:
        """
        Get factual information for all opinions using web search
        """
        try:
            # Create tasks for all web searches with topic context using prompt template
            system_prompt = prompt_yaml['web_search']['system']
            user_prompt = prompt_yaml['web_search']['user']
            cors = [
                self.client.web_search_mini_chat(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt.format(
                            topic_title=topic_title,
                            opinion=opinion
                        )}
                    ]
                ) for opinion in opinions
            ]
            
            # Run all web searches concurrently
            factual_info = await asyncio.gather(*cors)
            for info in factual_info:
                print(info)
            return factual_info
            
        except Exception as e:
            print(f"Error gathering factual information: {e}")
            return []

    async def get_credibility_score(self, topic_title: str, factual_info: List[str], opinions: List[str], prompt_yaml: Dict) -> List[str]:
        """
        Process each opinion-fact pair and return formatted strings with credibility scores
        """
        try:
            # Get prompt templates
            system_prompt = prompt_yaml['credibility_scoring']['system']
            user_prompt = prompt_yaml['credibility_scoring']['user']
            
            # Create tasks for all credibility scoring requests
            cors = []
            for info, opinion in zip(factual_info, opinions):
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt.format(
                        topic_title=topic_title,
                        opinion=opinion,
                        factual_info=info
                    )}
                ]
                cors.append(self.client.chat_async(messages=messages))
            
            # Run all scoring requests concurrently
            scores = await asyncio.gather(*cors)
            print(scores)
            # Process responses and format results
            scored_opinions = []
            for score_text, opinion in zip(scores, opinions):
                try:
                    if score_text == -1:
                        scored_opinions.append(f"{opinion} (credibility score unavailable)")
                        continue
                    score = min(10, max(0, int(float(score_text.strip()))))
                    scored_opinions.append(f"{opinion} (credibility score of {score})")
                except ValueError:
                    scored_opinions.append(f"{opinion} (credibility score unavailable)")
            
            return scored_opinions
            
        except Exception as e:
            print(f"Error getting credibility scores: {e}")
            return [f"{op} (scoring failed)" for op in opinions]

    async def check_credibility(self, topic_title: str, opinions: List[str], prompt_yaml: Dict) -> List[str]:
        """
        Main function to process opinions and return scored results
        """
        # opinions 가 없을 경우
        if not opinions or len(opinions) == 0:
            return []
        
        # First get factual information for all opinions
        factual_info = await self.get_factual_info(topic_title, opinions, prompt_yaml)
        
        if not factual_info:
            return [f"{op} (fact-checking failed)" for op in opinions]
        
        # Then get credibility scores and format results
        return await self.get_credibility_score(topic_title, factual_info, opinions, prompt_yaml)
