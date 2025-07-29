from typing import List, Dict, Any
from ..llm_clients.factory import LLMClientFactory
import time
import yaml
import json


class JudgeAfterDebate:
    # for now I will just use openai client only
    def __init__(self):
        self.openai_client = LLMClientFactory.create_client("openai")
        self.max_turns = 20

    def debate(self, messages):
        """
        Make final judgement through debate between two AI agents.
        Process:
        1. Both judges make independent initial judgments
        2. Compare and discuss differences
        3. Reach consensus through debate
        4. Return final consensus in required JSON format
        """
        # Get independent initial judgments from both judges
        response_a = self.openai_client.chat(messages, temperature=0.1)
        response_b = self.openai_client.chat(messages, temperature=0.1)
        
        print("\n--------------------------------")
        print(f"AI Judge A initial judgment:\n{response_a}")
        print("\n--------------------------------")
        print(f"AI Judge B initial judgment:\n{response_b}")
        print("\n--------------------------------")

        # Initialize message histories for debate
        messages_a = messages.copy()
        messages_b = messages.copy()
        messages_a.append({"role": "assistant", "content": response_a})
        messages_b.append({"role": "assistant", "content": response_b})

        # Start debate about differences
        debate_instruction = f"""
당신과 판사 B의 초기 판결이 다릅니다.

당신의 판결:
{response_a}

판사 B의 판결:
{response_b}

판사 B의 판결에 대해 의견을 제시해주세요.

1. 먼저 '[반론]' 또는 '[동의]'로 시작하는 짧은 설명을 작성하세요.
2. 그 다음 줄에 JSON 형식의 판결문을 작성하세요.
3. 의견이 다른 경우에는 너무 쉽게 동의하지 마세요.

예시 형식:
[반론] 판사 B의 비율은 너무 극단적입니다. 실제 차이는 더 작다고 봅니다.
{{"camp_id": "...", "reason": "...", "percentage": [...]}}

또는:
[동의] 판사 B의 분석이 정확합니다. 제시된 근거와 비율에 동의합니다.
{{"camp_id": "...", "reason": "...", "percentage": [...]}}

응답 시 주의사항:
- 동의/반론 이유를 구체적으로 설명하세요
- 다른 판사의 분석을 직접 인용하지 말고 자신만의 표현으로 작성하세요
- 비율 조정이 필요한 경우 그 이유를 명확히 설명하세요
"""
        messages_a.append({"role": "user", "content": debate_instruction})

        debate_instruction_b = f"""
당신의 판결:
{response_b}

판사 A가 당신의 판결에 대해 다음과 같이 응답했습니다:
{response_a}

판사 A의 응답에 대해 판단해주세요.

1. 먼저 '[반론]' 또는 '[동의]'로 시작하는 짧은 설명을 작성하세요.
2. 그 다음 줄에 JSON 형식의 판결문을 작성하세요.
3. 의견이 다른 경우에는 너무 쉽게 동의하지 마세요.

예시 형식:
[반론] 판사 A의 분석에 동의할 수 없습니다. 그 이유는...
{{"camp_id": "...", "reason": "...", "percentage": [...]}}

또는:
[동의] 판사 A의 분석이 타당합니다. 특히...
{{"camp_id": "...", "reason": "...", "percentage": [...]}}

응답 시 주의사항:
- 동의/반론 이유를 구체적으로 설명하세요
- 다른 판사의 분석을 직접 인용하지 말고 자신만의 표현으로 작성하세요
- 비율 조정이 필요한 경우 그 이유를 명확히 설명하세요
"""
        messages_b.append({"role": "user", "content": debate_instruction_b})

        messages_a.append({"role": "user", "content": f"판사 B의 의견입니다:\n{response_b}"})
        messages_b.append({"role": "user", "content": f"판사 A의 의견입니다:\n{response_a}"})

        turn_count = 0
        last_response = None
        previous_response = None  # Track previous response to check for repetition
        while turn_count < self.max_turns:
            response_a = self.openai_client.chat(messages_a, temperature=0.1)
            print("\n--------------------------------")
            print(f"AI Judge A: {response_a}")
            print("--------------------------------")

            # Check if we're in a loop
            if response_a == previous_response:
                print("✅ 토론 종료 - 판사들이 같은 결론에 도달했습니다")
                return {
                    "final_state": "agreement",
                    "consensus": response_a
                }

            if response_a.startswith("[동의]"):
                last_response = response_a
                messages_b.append({"role": "user", "content": f"판사 A가 다음과 같이 응답했습니다:\n{response_a}\n이 의견에 동의하시나요?"})
                response_b = self.openai_client.chat(messages_b, temperature=0.1)
                print("\n--------------------------------")
                print(f"AI Judge B: {response_b}")
                print("--------------------------------")
                
                if response_b.startswith("[동의]"):
                    print("✅ 토론 종료 - 판사들이 합의에 도달했습니다")
                    # Extract JSON from the response by finding the first '{'
                    json_start = response_b.find("{")
                    if json_start != -1:
                        consensus = response_b[json_start:]
                    else:
                        consensus = response_b.replace("[동의] ", "")
                    return {
                        "final_state": "agreement",
                        "consensus": consensus
                    }
            else:
                last_response = response_a

            messages_b.append({"role": "user", "content": f"판사 A의 의견입니다:\n{response_a}"})
            response_b = self.openai_client.chat(messages_b, temperature=0.1)
            print("\n--------------------------------")
            print(f"AI Judge B: {response_b}")
            print("--------------------------------")

            if response_b.startswith("[동의]"):
                print("✅ 토론 종료 - 판사들이 합의에 도달했습니다")
                # Extract JSON from the response by finding the first '{'
                json_start = response_b.find("{")
                if json_start != -1:
                    consensus = response_b[json_start:]
                else:
                    consensus = response_b.replace("[동의] ", "")
                return {
                    "final_state": "agreement",
                    "consensus": consensus
                }
            
            previous_response = response_b  # Update previous response
            last_response = response_b
            messages_a.append({"role": "user", "content": f"판사 B의 의견입니다:\n{response_b}"})
            turn_count += 1
            time.sleep(1)

        print("⚠️ 토론 종료 - 최대 턴수 도달")
        # Extract JSON from the last response
        json_start = last_response.find("{")
        if json_start != -1:
            consensus = last_response[json_start:]
        else:
            consensus = last_response
        return {
            "final_state": "max_turns_reached",
            "consensus": consensus
        }