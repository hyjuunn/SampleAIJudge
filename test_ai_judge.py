import json
import os
from lib.oracle_mvp_ai.ai_judge import AiJudge
from lib.oracle_mvp_ai.llm_clients.openai_client import OpenAIClient
from lib.oracle_mvp_ai.llm_clients.google_client import GoogleClient
from dotenv import load_dotenv
import asyncio
from bson import ObjectId

def main():
    # .env 파일에서 환경 변수 로드
    load_dotenv()
    
    # OpenAI API 키 설정 (환경 변수에서 가져오거나 직접 설정)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY 환경 변수를 설정해주세요.")
        return
    
    anthropic_api_key = os.environ.get("CLAUDE_API_KEY")
    if not anthropic_api_key:
        print("ClAUDE_API_KEY 환경 변수를 설정해주세요.")
        return
    
    google_api_key = os.environ.get("GEMINI_API_KEY")
    if not google_api_key:
        print("GEMINI_API_KEY 환경 변수를 설정해주세요.")
        return

    # AI Judge 초기화
    ai_judge = AiJudge(api_key=google_api_key)
    
    # 테스트 데이터 준비
    test_data = {
  "topic": {
    "_id": ObjectId("68775014a64d6b51065d49b5"),
    "camps": [
      {
        "id": ObjectId("68775014a64d6b51065d49b3"),
        "name": "오타니"
      },
      {
        "id": ObjectId("68775014a64d6b51065d49b4"),
        "name": "은가누"
      }
    ],
    "description": "나무 배트를 든 오타니와 UFC 헤비급 전 챔피언 은가누가 생사를 건 결투를 합니다. \n 조건:\n- 오타니는 은가누를 ‘야구공’으로 인식하며 시즌 마지막 경기 오타니의 누적 홈런 개수는 ‘59개’ 입니다. \n- 은가누는 오타니를 불구대천의 원수라고 생각합니다.\n- 두 사람에게 도덕적인 잣대는 없다고 가정합니다.\n\n오랜 논쟁이 있는 이 대결, 어떻게 생각하시나요?",
    "posts": [
      {
        "user_id": ObjectId("686e76de0891e597ccadaa6b"),
        "camp_id": ObjectId("68775014a64d6b51065d49b3"),
        "msg": "오타니 승리",
        "topic_id": ObjectId("68775014a64d6b51065d49b5")
      },
      {
        "user_id": ObjectId("686e369c9637751aa448048f"),
        "camp_id": ObjectId("68775014a64d6b51065d49b4"),
        "msg": "은가누 승리",
        "topic_id": ObjectId("68775014a64d6b51065d49b5")
      }
    ],
    "title": "나무 배트를 든 오타니 vs 그냥 은가누"
  }
}
    
    print("AI Judge 테스트 시작...")
    
    try:
        # AI Judge 실행
        result = asyncio.run(ai_judge.judge(test_data))
        
        # 결과 출력
        print("\n===== AI Judge 판결 결과 =====\n")
        print(f"주제 ID: {result['topic_id']}")
        print(f"진영 ID: {result['win_camp_id']}")
        print(f"AI 결론: {result['ai_conclusion']}")
        print(f"사용된 프롬프트: {result['metadata']['used_prompt_uris']}")
        if "judgement_percentage" in result:
            print(f"판결 비율: {result['judgement_percentage']}")

    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    main() 