from .openai_client import OpenAIClient
from .anthropic_client import AnthropicClient
from .google_client import GoogleClient
import os
import dotenv

class LLMClientFactory:

    @staticmethod
    def create_client(provider: str):
        dotenv.load_dotenv()
        openai_api_key = os.getenv("OPENAI_API_KEY")
        anthropic_api_key = os.getenv("CLAUDE_API_KEY")
        google_api_key = os.getenv("GEMINI_API_KEY")
        
        if provider == "openai":
            return OpenAIClient(openai_api_key)
        elif provider == "anthropic":
           return AnthropicClient(anthropic_api_key)
        elif provider == "google":
            return GoogleClient(google_api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")