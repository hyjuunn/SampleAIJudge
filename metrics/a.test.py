# 평가지표 예시

def simple_score(answer: str) -> int:
    """
    답변의 길이에 따라 점수를 매기는 예시 함수
    """
    return min(len(answer), 100) 