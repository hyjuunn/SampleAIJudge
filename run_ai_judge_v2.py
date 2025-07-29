import os
import dotenv
import json
from lib.oracle_mvp_ai.ai_judge import AiJudge

import asyncio

def main():
    # Load dataset
    with open('dataset/v2/messi_ronaldo.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Get API key
    dotenv.load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY environment variable not set')

    # Create judge
    judge = AiJudge(api_key=api_key)

    # Run async judge
    async def run_judge():
        result = await judge.judge(data)
        print('\nFinal result:')
        print(json.dumps(result, ensure_ascii=False, indent=2))

    asyncio.run(run_judge())

if __name__ == '__main__':
    main() 