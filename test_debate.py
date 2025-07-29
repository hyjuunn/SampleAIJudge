from lib.oracle_mvp_ai.strategies.final_debate import JudgeAfterDebate
from lib.oracle_mvp_ai.llm_clients.factory import LLMClientFactory
import json

def test_debate():
    # Initialize the judge
    openai_client = LLMClientFactory.create_client("openai")
    judge = JudgeAfterDebate()

    # Test messages
    messages = [
        {
            'role': 'system',
            'content': """You are an impartial judge who evaluates debates based on the quality of arguments and evidence.
Your role is to analyze the strength of reasoning and factual support, not just credibility scores.
Return a JSON object with camp_id (of the winning camp), percentages for each camp, and detailed reasoning.
IMPORTANT: You must ONLY evaluate opinions that were actually submitted. Never make up or imagine opinions that weren't provided.
CRITICAL: You must always declare a winner. Even in very close cases, find small details to differentiate and avoid exact ties.
"""
        },
        {
            'role': 'user',
            'content': """Analyze the opinions from each camp and determine:
1. The winning camp (you MUST choose one - no ties allowed)
2. The persuasion percentage for each camp in integer (must sum to 100%, no equal percentages allowed)
3. Detailed reasoning for the percentages

Base your evaluation ONLY on the provided opinions using:
1. Quality of reasoning and logic
2. Strength of factual evidence
3. Balanced consideration of different viewpoints
4. Depth of analysis

Avoid being swayed by:
- Emotional arguments without substance
- Claims without evidence
- Simple majority of opinions
- Just the credibility scores alone

Rules:
- Do not talk about the credibility scores in your explanation.
- If there are no opinions, assign percentages based on what you personally think is the more likely to win.
- When there are no opinions, your reason must start with "제출된 의견이 없어 AI의 주관적 판단으로는" and only discuss the topic itself, not any arguments.
- Percentages must sum to 100% and be rounded to nearest integer.
- You MUST ensure one camp has a higher percentage than others - no ties allowed.
- Even if the difference is minimal (e.g. 51% vs 49%), you must make a decision.

Provide a detailed explanation in Korean that includes the percentage breakdown for each camp.
Return ONLY a JSON object in this format:
{"camp_id":"<winning_camp_id>","reason":"<camp1>가 <X>프로, <camp2>가 <Y>프로의 비중으로 평가되었습니다. <detailed explanation based ONLY on submitted opinions OR clear statement about no opinions>","percentage": [{"camp_id":"<camp1_id>", "percentage":<camp1_percentage>}, {"camp_id":"<camp2_id>", "percentage":<camp2_percentage>}, {"camp_id":"<camp3_id>", "percentage":<camp3_percentage>}, ...]}
DO NOT include ```json or ``` around your response.

Topic: 오타니가 배트 가지고 은가누랑 싸우면 오타니가 이깁니다.
Opinions with credibility scores: 오타니 camp opinions:
1. 오타니가 이겨 (credibility score of 0)
2. 오타니는 은가누를 배트로 때려서 이길 수 있습니다. (credibility score of 1)
3. 오타니는 은가누보다 키가 크고 근육량이 더 많아서 이길 수 있습니다. (credibility score of 0)

은가누 camp opinions:
1. 은가누가 이겨 (credibility score of 0)
2. 은가누는 오타니의 배트를 뺏어서 이길 수 있습니다. (credibility score of 1)
3. 은가누는 오타니랑 키가 같고 근육량이 더 많아서 이길 수 있습니다. (credibility score of 0)
Available camps: 오타니 (ID: 68775014a64d6b51065d49b3)
은가누 (ID: 68775014a64d6b51065d49b4)"""
        }
    ]

    # Run the debate
    result = judge.debate(messages)
    
    # Print results in a formatted way
    print("\n=== Final Result ===")
    if result["final_state"] == "agreement":
        print("Debate reached consensus!")
    elif result["final_state"] == "immediate_agreement":
        print("Judges agreed immediately!")
    else:
        print("Debate reached max turns without consensus")
    
    print("\nFinal Judgment:")
    try:
        if isinstance(result["consensus"], str):
            consensus = json.loads(result["consensus"])
        else:
            consensus = result["consensus"]
        
        print(f"\nWinning Camp: {consensus['camp_id']}")
        print(f"Reason: {consensus['reason']}")
        print("\nPercentages:")
        for p in consensus['percentage']:
            print(f"Camp {p['camp_id']}: {p['percentage']}%")
    except Exception as e:
        print(f"Error parsing result: {e}")
        print("Raw consensus:", result["consensus"])

if __name__ == "__main__":
    test_debate()
    