import numpy as np
from typing import List

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    두 벡터 간의 코사인 유사도를 계산합니다.
    """
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)
    dot_product = np.dot(vec1_np, vec2_np)
    norm_a = np.linalg.norm(vec1_np)
    norm_b = np.linalg.norm(vec2_np)
    similarity = dot_product / (norm_a * norm_b)
    return float(similarity)

def sigmoid_mapping(score: float, k: float = 0.1, x0: float = 50.0) -> float:
    """
    시그모이드 함수를 사용하여 점수를 비선형적으로 매핑합니다.
    score: 0-100 스케일의 원본 점수
    k: 곡선의 가파른 정도를 조절하는 파라미터 (클수록 가파름)
    x0: 곡선의 중간점 (변곡점)을 조절하는 파라미터
    """
    # 점수를 0-1 스케일로 정규화 (0-100 -> 0-1)
    normalized_score = score / 100.0
    
    # 시그모이드 함수 적용 (입력값을 -6 ~ 6 범위로 매핑하여 시그모이드의 유효 구간 활용)
    # x0를 0-1 스케일에 맞춰 변환
    mapped_score = 1 / (1 + np.exp(-k * (normalized_score * 100 - x0)))
    
    # 다시 0-100 스케일로 변환
    return float(mapped_score * 100)
