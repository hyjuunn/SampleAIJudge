import asyncio
from typing import List, Dict, Any
import aiohttp
from openai import AsyncOpenAI
from ..llm_clients.openai_client import OpenAIClient
import yaml

class CredibilityCheckerBatch:
    def __init__(self, openai_client: OpenAIClient, batch_size: int = 5):
        """
        Initialize the batch credibility checker
        
        Args:
            openai_client: OpenAI client instance
            batch_size: Number of opinions to process in a single batch (default: 5)
        """
        self.client = openai_client
        self.batch_size = batch_size

    def _chunk_list(self, lst: List[Any], chunk_size: int) -> List[List[Any]]:
        """Helper function to split a list into chunks of specified size"""
        return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

    async def get_factual_info_batch(self, topic_title: str, opinions_batch: List[str], prompt_yaml: Dict) -> str:
        """
        Get factual information for a batch of opinions using a single web search
        """
        try:
            # Create a combined prompt for all opinions in the batch
            system_prompt = prompt_yaml['web_search']['system']
            user_prompt = prompt_yaml['web_search']['user']
            
            # Combine all opinions into a single query
            combined_opinions = "\n".join([f"Opinion {i+1}: {opinion}" for i, opinion in enumerate(opinions_batch)])
            
            # Make a single web search call for the batch
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt.format(
                    topic_title=topic_title,
                    opinion=combined_opinions  # Pass all opinions as one string
                )}
            ]
            
            factual_info = await self.client.web_search_mini_chat(messages=messages)
            print(f"Batch factual info: {factual_info}")
            return factual_info
            
        except Exception as e:
            print(f"Error gathering factual information for batch: {e}")
            return ""

    async def get_credibility_scores_batch(self, topic_title: str, factual_info: str, opinions: List[str], prompt_yaml: Dict) -> List[str]:
        """
        Process all opinions in the batch against the factual info in a single LLM call
        """
        try:
            # Get prompt templates
            system_prompt = prompt_yaml['credibility_scoring']['system']
            user_prompt = prompt_yaml['credibility_scoring']['user']
            
            # Combine all opinions into numbered list
            combined_opinions = "\n".join([f"{i+1}. {opinion}" for i, opinion in enumerate(opinions)])
            
            # Make a single LLM call for all opinions
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt.format(
                    topic_title=topic_title,
                    opinion=combined_opinions,
                    factual_info=factual_info
                )}
            ]
            
            # Get scores for all opinions in one call
            response = await self.client.chat_async(messages=messages)
            print(f"Batch scoring response: {response}")
            
            try:
                # Clean up response if it's wrapped in markdown code block
                import json
                cleaned_response = response
                if "```json" in response:
                    # Extract content between ```json and ```
                    cleaned_response = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    # Extract content between ``` and ```
                    cleaned_response = response.split("```")[1].strip()
                
                # Parse the JSON response
                scores_data = json.loads(cleaned_response)
                
                # Process responses and format results
                scored_opinions = []
                for score_info in scores_data:
                    opinion = score_info["opinion"]
                    score = score_info["score"]
                    if score == -1:
                        scored_opinions.append(f"{opinion} (credibility score unavailable)")
                    else:
                        score = min(10, max(0, int(float(score))))
                        scored_opinions.append(f"{opinion} (credibility score of {score})")
                
                return scored_opinions
                
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"Error parsing scoring response: {e}")
                print(f"Cleaned response was: {cleaned_response}")
                return [f"{op} (scoring failed - invalid response format)" for op in opinions]
            
        except Exception as e:
            print(f"Error getting credibility scores for batch: {e}")
            return [f"{op} (scoring failed)" for op in opinions]

    async def check_credibility(self, topic_title: str, opinions: List[str], prompt_yaml: Dict) -> List[str]:
        """
        Main function to process opinions in batches and return scored results
        """
        if not opinions or len(opinions) == 0:
            return []
        
        all_scored_opinions = []
        
        # Split opinions into batches
        opinion_batches = self._chunk_list(opinions, self.batch_size)
        
        # Process each batch
        for batch in opinion_batches:
            # Get factual information for the batch
            factual_info = await self.get_factual_info_batch(topic_title, batch, prompt_yaml)
            
            if not factual_info:
                all_scored_opinions.extend([f"{op} (fact-checking failed)" for op in batch])
                continue
            
            # Get credibility scores for the batch
            scored_batch = await self.get_credibility_scores_batch(topic_title, factual_info, batch, prompt_yaml)
            all_scored_opinions.extend(scored_batch)
        
        return all_scored_opinions
