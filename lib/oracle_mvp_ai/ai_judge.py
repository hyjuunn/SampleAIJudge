import numpy as np
from bson import ObjectId
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from .checker.duplicate_checker import DuplicateChecker
from .checker.credibility_checker import CredibilityChecker
from .checker.credibility_checker_batch import CredibilityCheckerBatch
from .llm_clients.factory import LLMClientFactory
from .strategies.final_debate import JudgeAfterDebate
import yaml
import json


class AiJudge:
    def __init__(self, api_key: str):
        self.openai_client = LLMClientFactory.create_client("openai")
        self.google_client = LLMClientFactory.create_client("google")
        self.anthropic_client = LLMClientFactory.create_client("anthropic")
        self.duplicate_checker = DuplicateChecker(self.openai_client)
        self.credibility_checker = CredibilityChecker(self.openai_client)
        self.credibility_checker_batch = CredibilityCheckerBatch(self.openai_client)
        self.prompt_metadata_dir = Path(__file__).parent / "prompt_metadata"
        # 의견이 없을 경우 판결 방지 옵션
        self.prevent_judgement_without_opinion = False
        self.output_judgement_percentage = True
        self.group_opinions_by_camp = False
        # 최종 판결 모델 선택 (openai, google, anthropic)
        self.final_judgement_provider = "openai"
        # 토론 옵션 (openai 사용)
        self.judge_after_debate = True
        # 신뢰도 점수 배치 처리 옵션
        self.batch_credibility_check = True

    def _process_input_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        입력 JSON 데이터를 처리하여 AI 판사 시스템에 필요한 형태로 변환
        
        Args:
            data: 다음 형식의 JSON 데이터
            {
                "topic": {
                    "_id": <ObjectId>,
                    "title": <str>,
                    "description": <str>,
                    "camps": [
                        {
                            "id": <ObjectId>,
                            "name": <str>
                        },
                        ...
                    ],
                    "posts": [
                        {
                            "user_id": <ObjectId>,
                            "camp_id": <ObjectId>,  # Optional field
                            "msg": <str>
                        },
                        ...
                    ],
                },
            }
            
        Returns:
            처리된 데이터
        """
        # 주제 정보 추출
        topic = data.get("topic", {})
        title = topic.get("title", "")
        description = topic.get("description", "")
        
        # 주제 제목과 설명을 결합
        topic_info = f"{title}"
        if description:
            topic_info += f": {description}"
            
        # 진영 정보 추출
        camps = topic.get("camps", [])
        camp_names = [camp.get("name", "") for camp in camps]
        camp_ids = [camp.get("id", "") for camp in camps]
        
        # 의견 추출
        opinions_info = topic.get("posts", [])
        
        # 진영 정보가 있는지 확인
        has_camp_ids = any("camp_id" in opinion for opinion in opinions_info)
        
        if has_camp_ids and self.group_opinions_by_camp:
            # 진영 정보가 있고 진영별 그룹화 옵션이 켜져있으면 진영정보 포함
            posts_with_camps = [(str(opinion.get("msg", "")), str(opinion.get("camp_id", ""))) for opinion in opinions_info]
            result = {
                "topic_id": topic.get("_id", ""),
                "topic": topic_info,
                "camps": camp_names,
                "camp_ids": camp_ids,
                "posts_with_camps": posts_with_camps,
                "prompt_file": self._select_prompt_file(topic_info, camp_names)
            }
        else:
            # If no camp_ids or grouping is disabled, use the old format
            posts = [opinion.get("msg", "") for opinion in opinions_info]
            result = {
                "topic_id": topic.get("_id", ""),
                "topic": topic_info,
                "camps": camp_names,
                "camp_ids": camp_ids,
                "posts": posts,
                "prompt_file": self._select_prompt_file(topic_info, camp_names)
            }
            
        return result

    def _select_prompt_file(self, topic: str, camps: List[str]) -> str:
        """
        주제와 진영 정보에 따라 적절한 프롬프트 메타데이터 파일 선택
        우선은 프롬프트 고정
        """
        if self.batch_credibility_check:
            prompt_file = "v_2_1_1.yaml"
        else:
            prompt_file = "v_2_0_2.yaml"
        return prompt_file

    def _organize_opinions_by_camp(self, scored_opinions: List[str], original_posts_with_camps: List[Tuple[str, str]], camp_ids: List[str]) -> Dict[str, List[str]]:
        """
        캠프별 의견 그룹화
        
        Args:
            scored_opinions: 신뢰도 검사 후 의견 리스트
            original_posts_with_camps: 원본 의견 리스트와 캠프 아이디 리스트 (튜플 리스트)
            camp_ids: 캠프 아이디 리스트
            
        Returns:
            점수가 부여된 의견을 캠프별로 그룹화한 딕셔너리
        """
        # 캠프별 의견 그룹화를 위한 딕셔너리 초기화
        camp_opinions = {str(camp_id): [] for camp_id in camp_ids}
        
        # 원본 의견과 캠프 아이디 매핑
        opinion_to_camp = {opinion: camp_id for opinion, camp_id in original_posts_with_camps}
        
        # 신뢰도 검사 후 의견 리스트를 캠프별로 그룹화
        for scored_opinion in scored_opinions:
            # 신뢰도 점수 제거 후 원본 의견 추출
            original_text = scored_opinion.split(" (credibility score of ")[0]
            camp_id = opinion_to_camp.get(original_text, None)
            
            if camp_id and camp_id in camp_opinions:
                camp_opinions[camp_id].append(scored_opinion)
            else:
                # 캠프 아이디가 없으면 모든 캠프에 그룹화
                for camp_id in camp_ids:
                    camp_opinions[str(camp_id)].append(scored_opinion)
        
        return camp_opinions

    async def judge(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        입력 데이터를 처리하고 AI 판사 시스템에 전달
        """
        processed_data = self._process_input_data(data)
        prompt_file = processed_data["prompt_file"]
        topic = processed_data["topic"]
        
        # Handle both old and new formats
        if "posts_with_camps" in processed_data:
            posts_with_camps = processed_data["posts_with_camps"]
            posts = [post for post, _ in posts_with_camps]
        else:
            posts = processed_data["posts"]
            posts_with_camps = None
        
        if not posts and self.prevent_judgement_without_opinion: 
            return {
                #백엔드 요청 파라미터
                "topic_id": processed_data["topic_id"],
                "win_camp_id": None,
                "ai_conclusion": "의견이 등록되지 않아 판결을 내릴 수 없습니다.",
                "metadata": {
                    "used_prompt_uris": [prompt_file]
                }
            }
        
        camps = processed_data["camps"]
        camp_ids = processed_data["camp_ids"]

        prompt_path = Path(self.prompt_metadata_dir) / prompt_file

        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_yaml = yaml.safe_load(f)

        # 의미 비슷한 의견 통합하기
        embeddings = await self.duplicate_checker.create_embeddings(posts)
        
        # 중복 의견 제거
        deduped_opinions, deduped_embeddings, opinion_counts = self.duplicate_checker._deduplicate_opinions(
            posts,
            embeddings,
            similarity_threshold=0.73
        )
        
        print(f"\nAfter deduplication: {len(deduped_opinions)} unique opinions")
        print("\nDuplicate groups found:")
        for opinion, count in opinion_counts.items():
            if count > 0:
                print(f"\nOpinion appeared {count} times: {opinion[:100]}...")
        
        # 신뢰도 검사
        print("\nChecking credibility of unique opinions...")
        if self.batch_credibility_check:
            scored_opinions = await self.credibility_checker_batch.check_credibility(topic, deduped_opinions, prompt_yaml)
        else:
            scored_opinions = self.credibility_checker.check_credibility(topic, deduped_opinions, prompt_yaml)
        
        print("\nScored opinions:")
        for opinion in scored_opinions:
            print(f"\n{opinion}")

        # 그룹화 옵션이 켜져있고 진영 정보가 있으면 의견 그룹화
        if self.group_opinions_by_camp and posts_with_camps:
            camp_opinions = self._organize_opinions_by_camp(scored_opinions, posts_with_camps, camp_ids)
            # 캠프별 의견 리스트 포맷팅
            opinions_list = "\n\n".join([
                f"{camps[camp_ids.index(str(camp_id))]} camp opinions:\n" + 
                "\n".join([f"{i+1}. {opinion}" for i, opinion in enumerate(opinions)])
                for camp_id, opinions in camp_opinions.items() if opinions
            ])
        else:
            opinions_list = "\n".join([f"{i+1}. {opinion}" for i, opinion in enumerate(scored_opinions)])
        
        print(f"\nopinions_list:\n {opinions_list}")

        # 최종 판결
        final_judgement = self._make_final_judgment(topic, opinions_list, prompt_yaml, camps, camp_ids)
        print(f"\nFinal judgement: {final_judgement}")

        win_camp_id = final_judgement.get("camp_id", "")
        ai_conclusion = final_judgement.get("reason", "")
        percentage = final_judgement.get("percentage", "")
        # 결과 반환
        result = {
            "topic_id": processed_data["topic_id"],
            "win_camp_id": win_camp_id,
            "ai_conclusion": ai_conclusion,
            "metadata": {
                "used_prompt_uris": [prompt_file]
            }
        }
        if self.output_judgement_percentage:
            result["judgement_percentage"] = percentage
        return result
    
    def _make_final_judgment(self, topic: str, opinions_list: str, prompt_yaml: Dict, camps: List[str], camp_ids: List[str]) -> Dict[str, str]:
        """
        최종 판결 도출
        """
        # 프롬프트 추출
        system_content = prompt_yaml.get("final_judgment", {}).get("system", "")
        user_template = prompt_yaml.get("final_judgment", {}).get("user", "")
        
        # 캠프 정보 포맷팅 - 각 캠프의 이름과 ID를 포함
        # camp_ids를 모두 str로 변환
        camp_ids = [str(camp_id) for camp_id in camp_ids]
        camps_info = "\n".join([f"{camp} (ID: {camp_id})" for camp, camp_id in zip(camps, camp_ids)])
        user_template = user_template.replace("{topic}", topic).replace("{opinions}", opinions_list).replace("{camps}", camps_info)
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_template} 
        ]
        print(f"\nmessages:\n {messages}")

        try:
            if self.final_judgement_provider == "openai":
                print("\n--------------------------------")
                print("Using GPT-4o for final judgement")
                if (self.judge_after_debate):
                    print("\n--------------------------------")
                    print("Using GPT-4o for final judgement with debate")
                    response = JudgeAfterDebate().debate(messages)
                    consensus = response.get("consensus", "")
                    response = consensus[consensus.find("{"):]
                else:
                    response = self.openai_client.chat(messages, temperature=0)
            elif self.final_judgement_provider == "google":
                print("\n--------------------------------")
                print("Using Gemini-2.5-pro for final judgement")
                response = self.google_client.chat(messages, temperature=0)
            elif self.final_judgement_provider == "anthropic":
                print("\n--------------------------------")
                print("Using Claude-3.5-sonnet for final judgement")
                response = self.anthropic_client.chat(messages, temperature=0)
            else:
                raise ValueError(f"Unsupported provider: {self.final_judgement_provider}")
            
            # Clean up the response - remove any leading/trailing whitespace and quotes
            response = response.strip().strip('"').strip("'")
            
            print(f"\nResponse: {response}")
            # If the response starts with a single quote and ends with a double quote (or vice versa),
            # remove the outer quotes
            if (response.startswith("'") and response.endswith('"')) or \
               (response.startswith('"') and response.endswith("'")):
                response = response[1:-1]
            
            try:
                # Try to parse the response as JSON
                judgment = json.loads(response)
                
                # Validate the judgment format
                if not isinstance(judgment, dict):
                    print(f"Invalid judgment format (not a dictionary): {judgment}")
                    raise ValueError("Judgment must be a dictionary")
                
                # Clean up the camp_id value - remove any extra quotes and spaces
                camp_id = judgment.get("camp_id", "")
                camp_id = str(camp_id).strip('"').strip("'").strip()
                reason = str(judgment.get("reason", "판결 이유가 제공되지 않았습니다.")).strip()
                percentage = judgment.get("percentage", [])
                
                # Validate the camp_id
                if not camp_id:
                    print("Empty camp_id received")
                    camp_id = camp_ids[0]  # Default to first camp
                elif camp_id not in camp_ids:
                    print(f"Invalid camp_id received: {camp_id}")
                    print(f"Available camp_ids: {camp_ids}")
                    # Try to match by removing any extra quotes or spaces
                    cleaned_camp_id = camp_id.strip('"').strip("'").strip()
                    if cleaned_camp_id in camp_ids:
                        camp_id = cleaned_camp_id
                    else:
                        camp_id = camp_ids[0]  # Default to first camp
                
                # Validate and format percentage array
                if not isinstance(percentage, list):
                    print(f"Invalid percentage format (not a list): {percentage}")
                    percentage = [{"camp_id": str(cid), "percentage": 100 // len(camps) + (100 % len(camps) if i == 0 else 0)} 
                                for i, cid in enumerate(camp_ids)]
                else:
                    # Convert any simple number array to complex structure
                    if percentage and isinstance(percentage[0], (int, float)):
                        percentage = [{"camp_id": str(cid), "percentage": pct} 
                                    for cid, pct in zip(camp_ids, percentage)]
                    # Validate each percentage entry
                    valid_percentage = True
                    for entry in percentage:
                        if not isinstance(entry, dict) or "camp_id" not in entry or "percentage" not in entry:
                            valid_percentage = False
                            break
                    if not valid_percentage or len(percentage) != len(camps):
                        print(f"Invalid percentage structure or length mismatch: {percentage}")
                        percentage = [{"camp_id": str(cid), "percentage": 100 // len(camps) + (100 % len(camps) if i == 0 else 0)} 
                                    for i, cid in enumerate(camp_ids)]
                    else:
                        # camp_id를 모두 str로 변환
                        for entry in percentage:
                            entry["camp_id"] = str(entry["camp_id"])
                
                return {
                    "camp_id": camp_id,
                    "reason": reason,
                    "percentage": percentage
                }
                
            except json.JSONDecodeError as e:
                print(f"JSON 파싱 오류: {e}")
                print(f"Raw response: {response}")
                # Try to extract camp_id and reason using string manipulation
                try:
                    import re
                    camp_id_match = re.search(r'"camp_id"\s*:\s*"([^\"]+)"', response)
                    reason_match = re.search(r'"reason"\s*:\s*"([^\"]+)"', response)
                    percentage_match = re.search(r'"percentage"\s*:\s*(\[[^\]]+\])', response)
                    
                    camp_id = camp_id_match.group(1).strip() if camp_id_match else camp_ids[0]
                    camp_id = str(camp_id)
                    reason = reason_match.group(1).strip() if reason_match else "판결을 파싱할 수 없습니다."
                    
                    try:
                        if percentage_match:
                            percentage_data = json.loads(percentage_match.group(1))
                            if percentage_data and isinstance(percentage_data[0], dict):
                                # camp_id를 str로 변환
                                for entry in percentage_data:
                                    entry["camp_id"] = str(entry["camp_id"])
                                percentage = percentage_data
                            else:
                                percentage = [{"camp_id": str(cid), "percentage": pct} 
                                            for cid, pct in zip(camp_ids, percentage_data)]
                        else:
                            percentage = [{"camp_id": str(cid), "percentage": 100 // len(camps) + (100 % len(camps) if i == 0 else 0)} 
                                        for i, cid in enumerate(camp_ids)]
                    except:
                        percentage = [{"camp_id": str(cid), "percentage": 100 // len(camps) + (100 % len(camps) if i == 0 else 0)} 
                                    for i, cid in enumerate(camp_ids)]
                    
                    if camp_id in camp_ids:
                        return {
                            "camp_id": camp_id,
                            "reason": reason,
                            "percentage": percentage
                        }
                except Exception as e:
                    print(f"String manipulation failed: {e}")
                
                return {
                    "camp_id": camp_ids[0],  # Default to first camp
                    "reason": "판결을 파싱할 수 없습니다.",
                    "percentage": [{"camp_id": str(cid), "percentage": 100 // len(camps) + (100 % len(camps) if i == 0 else 0)} 
                                 for i, cid in enumerate(camp_ids)]
                }
        except Exception as e:
            print(f"최종 판결 오류: {e}")
            return {
                "camp_id": camp_ids[0],  # Default to first camp
                "reason": f"판결 도출 중 오류가 발생했습니다: {str(e)}",
                "percentage": [{"camp_id": str(cid), "percentage": 100 // len(camps) + (100 % len(camps) if i == 0 else 0)} 
                             for i, cid in enumerate(camp_ids)]
            }
        

        
    