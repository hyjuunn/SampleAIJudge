import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from ..llm_clients.openai_client import OpenAIClient
import asyncio

class DuplicateChecker:
    def __init__(self, openai_client: OpenAIClient):
        self.openai_client = openai_client

    async def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        OpenAI API를 사용하여 텍스트 임베딩 생성
        """
        try:
            # Create tasks for all embedding requests
            cors = [self.openai_client.create_embedding_async(text) for text in texts]
            
            # Run all embedding requests concurrently
            embeddings = await asyncio.gather(*cors)
            return np.array(embeddings)
        except Exception as e:
            print(f"임베딩 생성 중 오류 발생: {e}")
            raise e
    
    def _deduplicate_opinions(
        self, 
        opinions: List[str], 
        embeddings: np.ndarray,     
        similarity_threshold: float = 0.8
    ) -> Tuple[List[str], np.ndarray, Dict[str, int]]:
        """
        코사인 유사도를 사용하여 매우 유사한 의견들을 통합
        
        Args:
            opinions: 원본 의견 목록
            embeddings: 의견들의 임베딩 벡터
            similarity_threshold: 유사도 임계값
            
        Returns:
            통합된 의견 목록, 통합된 임베딩, 각 의견의 등장 횟수
        """
        # opinions 가 없을 경우
        if not opinions or len(opinions) == 0:
            return [], np.array([]), {}

        # 유사도 매트릭스
        norms = np.linalg.norm(embeddings, axis=1)[:, np.newaxis]
        normalized = embeddings / norms
        similarities = np.dot(normalized, normalized.T)
        
        used_indices = set()
        deduped_opinions = []
        deduped_embeddings = []
        opinion_counts = {}
        
        for i in range(len(opinions)):
            if i in used_indices:
                continue
                
            # i번째 의견과 유사한 의견 찾기
            similar_indices = set([i])
            for j in range(i + 1, len(opinions)):
                if j not in used_indices and similarities[i, j] >= similarity_threshold:
                    similar_indices.add(j)
            
            # 제일 긴 의견 기준으로 통합
            representative_idx = max(similar_indices, key=lambda idx: len(opinions[idx]))
            deduped_opinions.append(opinions[representative_idx])
            deduped_embeddings.append(embeddings[representative_idx])
            opinion_counts[opinions[representative_idx]] = len(similar_indices)
            
            # 사용된 인덱스 기록
            used_indices.update(similar_indices)
        
        return deduped_opinions, np.array(deduped_embeddings), opinion_counts
