from typing import List, Dict, Any, Tuple
from collections import Counter
import re
from .llm_clients.openai_client import OpenAIClient
import numpy as np
from collections import Counter
from difflib import SequenceMatcher
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class OpinionMetrics:
    """
    의견 평가를 위한 메트릭스 시스템
    """
    def __init__(self, openai_client: OpenAIClient):
        self.openai_client = openai_client
    
    def calculate_all_metrics(self, topic: str, opinions: List[str]) -> Dict[str, Any]:
        """
        모든 메트릭스를 계산하여 반환
        """
        return {
            "consistency_score": self.calculate_consistency_score(opinions),
            "logic_score": self.calculate_logic_score(topic, opinions),
            "evidence_score": self.calculate_evidence_score(topic, opinions),
            "neutrality_score": self.calculate_neutrality_score(opinions),
            "consensus_score": self.calculate_consensus_score(opinions),
            "keyword_analysis": self.analyze_keywords(opinions)
        }
    
    def calculate_consistency_score(self, opinions: List[str]) -> float:
        """
        의견들의 일관성 점수 계산
        - 비슷한 주장이 얼마나 많이 반복되는지 측정
        """
        keyword_counter = Counter()  # 키워드 빈도 카운터
        for opinion in opinions:
            # 2글자 이상 단어 추출
            keywords = re.findall(r'\w{2,}', opinion.lower())
            keyword_counter.update(keywords)
        # 상위 키워드 추출
        top_keywords = [item[0] for item in keyword_counter.most_common(10)]
        if not top_keywords:
            return 0.5
        # 상위 키워드가 얼마나 많은 의견에 등장하는지 계산
        keyword_appearance_ratios = []
        for keyword in top_keywords:
            count = sum(1 for opinion in opinions if keyword in opinion.lower())
            ratio = count / len(opinions)
            keyword_appearance_ratios.append(ratio)
        # 상위 키워드의 평균 등장 비율을 일관성 점수로 사용
        return sum(keyword_appearance_ratios) / len(keyword_appearance_ratios) if keyword_appearance_ratios else 0.5
    
    def calculate_logic_score(self, topic: str, opinions: List[str]) -> float:
        """
        의견들의 논리성 점수 계산
        - LLM을 활용하여 각 의견의 논리적 구조를 평가
        """
        if not opinions:
            return 0.5
        # 의견 샘플링 (최대 10개)
        sampled_opinions = opinions[:10] if len(opinions) > 10 else opinions
        total_score = 0
        for opinion in sampled_opinions:
            messages = [
                {"role": "system", "content": "당신은 논리적 구조를 평가하는 AI입니다. 주장이 논리적으로 일관되고 근거가 있는지 평가해야 합니다."},
                {"role": "user", "content": f"다음은 '{topic}'에 관한 의견입니다. 이 의견이 얼마나 논리적으로 구성되어 있는지 0.0부터 1.0 사이의 점수로 평가해주세요. 점수만 숫자로 반환해주세요.\n\n의견: {opinion}"}
            ]
            response = self.openai_client.chat(messages)
            try:
                score = float(response.strip())
                total_score += max(0.0, min(1.0, score))  # 0.0 ~ 1.0 범위로 제한
            except:
                total_score += 0.5  # 기본값
        return total_score / len(sampled_opinions)
    
    def calculate_evidence_score(self, topic: str, opinions: List[str]) -> float:
        """
        의견들의 증거 기반 점수 계산
        - 구체적인 수치, 인용, 참조 등이 포함되어 있는지 평가
        """
        if not opinions:
            return 0.5
        # 의견 샘플링 (최대 10개)
        sampled_opinions = opinions[:10] if len(opinions) > 10 else opinions
        total_score = 0
        for opinion in sampled_opinions:
            # 증거의 특징 탐지
            has_number = bool(re.search(r'\d+', opinion))
            has_quote = bool(re.search(r'["]+.*?["]+', opinion) or "인용" in opinion or "따르면" in opinion)
            has_reference = bool(re.search(r'https?://\S+', opinion) or "연구" in opinion or "보고서" in opinion)
            # 기본 점수 계산
            basic_score = sum([has_number, has_quote, has_reference]) / 3
            # LLM 기반 평가 추가
            messages = [
                {"role": "system", "content": "당신은 주장의 증거를 평가하는 AI입니다. 주장이 얼마나 구체적인 증거에 기반하고 있는지 평가해야 합니다."},
                {"role": "user", "content": f"다음은 '{topic}'에 관한 의견입니다. 이 의견이 얼마나 구체적인 증거(수치, 인용, 참조 등)를 포함하고 있는지 0.0부터 1.0 사이의 점수로 평가해주세요. 점수만 숫자로 반환해주세요.\n\n의견: {opinion}"}
            ]
            response = self.openai_client.chat(messages)
            try:
                llm_score = float(response.strip())
                llm_score = max(0.0, min(1.0, llm_score))  # 0.0 ~ 1.0 범위로 제한
                # 기본 점수와 LLM 점수의 가중 평균
                final_score = 0.3 * basic_score + 0.7 * llm_score
                total_score += final_score
            except:
                total_score += basic_score  # LLM 평가 실패 시 기본 점수만 사용
        return total_score / len(sampled_opinions)
    
    def calculate_neutrality_score(self, opinions: List[str]) -> float:
        """
        의견들의 중립성 점수 계산
        - 감정적 표현, 극단적 표현 등을 탐지
        """
        if not opinions:
            return 0.5
        # 감정적/극단적 표현 키워드 (영어/한국어 혼합 예시)
        emotional_keywords = ["화나다", "짜증", "최악", "최고", "절대", "무조건", "항상", "절대로", 
                    "완전히", "전혀", "끔찍", "환상적", "끝내주는", "말도 안되는", "어이없는"]
        total_score = 0
        for opinion in opinions:
            # 감정적 키워드 포함 여부 확인
            emotional_expression_count = sum(1 for keyword in emotional_keywords if keyword in opinion)
            emotion_score = 1.0 - (emotional_expression_count / len(emotional_keywords) if emotional_expression_count > 0 else 0)
            # 느낌표, 물음표 과다 사용 확인
            excessive_special_chars = len(re.findall(r'[!?]{2,}', opinion)) > 0
            special_chars_score = 0.7 if excessive_special_chars else 1.0
            # 대문자 과다 사용 확인 (한글에는 해당 없음)
            excessive_uppercase = False
            english_match = re.findall(r'[A-Za-z]+', opinion)
            if english_match:
                uppercase_ratio = sum(1 for word in english_match if word.isupper()) / len(english_match)
                excessive_uppercase = uppercase_ratio > 0.3
            uppercase_score = 0.7 if excessive_uppercase else 1.0
            # 최종 점수 계산 (가중 평균)
            neutrality_score = 0.5 * emotion_score + 0.3 * special_chars_score + 0.2 * uppercase_score
            total_score += neutrality_score
        return total_score / len(opinions)
    
    def calculate_consensus_score(self, opinions: List[str]) -> float:
        """
        의견들의 합의도 계산
        - 의견들이 얼마나 비슷한 주장을 하는지 측정
        """
        if len(opinions) <= 1:
            return 1.0
        # LLM을 활용한 합의도 측정
        messages = [
            {"role": "system", "content": "당신은 의견들의 합의도를 평가하는 AI입니다. 의견들이 얼마나 비슷한 주장을 하는지 평가해야 합니다."},
            {"role": "user", "content": f"다음은 의견들입니다. 이 의견들이 얼마나 비슷한 주장을 하는지(합의도) 0.0부터 1.0 사이의 점수로 평가해주세요. 0.0은 완전히 다른 의견들, 1.0은 모두 같은 의견을 의미합니다. 점수만 숫자로 반환해주세요.\n\n의견 목록:\n" + "\n".join([f"- {opinion}" for opinion in opinions[:20]])}
        ]
        response = self.openai_client.chat(messages)
        try:
            score = float(response.strip())
            return max(0.0, min(1.0, score))  # 0.0 ~ 1.0 범위로 제한
        except:
            return 0.5  # 기본값
    
    def analyze_keywords(self, opinions: List[str]) -> Dict[str, int]:
        """
        의견들에서 주요 키워드 추출 및 빈도 분석
        """
        keyword_counter = Counter()  # 키워드 빈도 카운터
        for opinion in opinions:
            # 2글자 이상 단어 추출
            keywords = re.findall(r'\w{2,}', opinion.lower())
            keyword_counter.update(keywords)
        # 불용어 제거 (한국어 기준)
        stopwords = ["있다", "없다", "하다", "되다", "이다", "그리고", "그러나", "또한", "그런데", "하지만"]
        for stopword in stopwords:
            if stopword in keyword_counter:
                del keyword_counter[stopword]
        # 상위 20개 키워드 반환
        return dict(keyword_counter.most_common(20))


def calculate_consistency_metrics(results):
    # 결과에서 필요한 정보 추출
    winners = [r.get('win_camp_id') for r in results if r.get('win_camp_id') is not None]
    # win_rate 대신 judgement_percentage에서 승리 진영의 percentage를 추출
    win_rates = []
    for r in results:
        jp = r.get('judgement_percentage')
        if isinstance(jp, list) and jp:
            max_perc = max([x.get('percentage', 0) for x in jp if isinstance(x, dict)])
            win_rates.append(max_perc)
    explanations = [r.get('ai_conclusion', '') for r in results if r.get('ai_conclusion', '') is not None]
    responses = [r.get('response', '') for r in results if r.get('response', '') is not None]

    # 1. 승리 진영 일치율
    if winners:
        try:
            most_common_winner, count = Counter(winners).most_common(1)[0]
            winner_consistency = count / len(winners) if len(winners) > 0 else 0
        except Exception:
            winner_consistency = 0
    else:
        winner_consistency = 0

    # 2. 승률 유사성 (표준편차/평균)
    if win_rates and all(isinstance(x, (int, float)) for x in win_rates):
        try:
            win_rate_std = float(np.std(win_rates))
            win_rate_mean = float(np.mean(win_rates))
            win_rate_similarity = 1 - (win_rate_std / win_rate_mean) if win_rate_mean else 0
        except Exception:
            win_rate_similarity = None
    else:
        win_rate_similarity = None

    # 3. 해설 문장 유사도 (평균 코사인 유사도)
    if len(explanations) > 1 and any(e.strip() for e in explanations):
        try:
            vect = CountVectorizer().fit_transform(explanations)
            sim_matrix = cosine_similarity(vect)
            n = len(explanations)
            sim_sum = sum(sim_matrix[i][j] for i in range(n) for j in range(i+1, n))
            sim_count = n * (n-1) / 2
            explanation_similarity = sim_sum / sim_count if sim_count else 1.0
        except Exception:
            explanation_similarity = 1.0
    else:
        explanation_similarity = 1.0

    # 4. 어휘 다양성 (유니크 토큰/전체 토큰)
    all_tokens = ' '.join(explanations).split()
    if all_tokens:
        try:
            vocab_diversity = len(set(all_tokens)) / len(all_tokens)
        except Exception:
            vocab_diversity = 0
    else:
        vocab_diversity = 0

    # 5. 응답 길이 분포 (평균, 표준편차)
    try:
        lengths = [len(e) for e in explanations if isinstance(e, str)]
        length_mean = float(np.mean(lengths)) if lengths else 0
        length_std = float(np.std(lengths)) if lengths else 0
    except Exception:
        length_mean = 0
        length_std = 0

    return {
        'winner_consistency': winner_consistency,
        'win_rate_similarity': win_rate_similarity,
        'explanation_similarity': explanation_similarity,
        'vocab_diversity': vocab_diversity,
        'length_mean': length_mean,
        'length_std': length_std,
    } 