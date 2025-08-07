"""
파일 관련 유틸리티 함수들
"""

import os
import re
from typing import Optional


def extract_percentage_from_filename(filename: str) -> Optional[str]:
    """
    파일명에서 백분율 추출
    
    예시:
    - "0.2.csv" -> "20%"
    - "0.4.csv" -> "40%"
    - "0.6.csv" -> "60%"
    - "1.0.csv" -> "100%"
    - "normal.csv" -> "normal"
    """
    try:
        # 파일명에서 확장자 제거
        basename = os.path.splitext(filename)[0]
        
        # 소수점 숫자 패턴 찾기 (예: 0.2, 0.4, 1.0)
        decimal_pattern = r'^(\d+\.\d+)$'
        match = re.match(decimal_pattern, basename)
        
        if match:
            decimal_value = float(match.group(1))
            # 소수점을 백분율로 변환
            percentage = int(decimal_value * 100)
            return f"{percentage}%"
        
        # 정수 패턴 찾기 (예: 20, 40, 60)
        integer_pattern = r'^(\d+)$'
        match = re.match(integer_pattern, basename)
        
        if match:
            integer_value = int(match.group(1))
            # 이미 백분율이라고 가정
            if integer_value <= 100:
                return f"{integer_value}%"
        
        # 백분율이 명시적으로 포함된 경우 (예: "20%", "40%")
        percentage_pattern = r'(\d+)%'
        match = re.search(percentage_pattern, basename)
        
        if match:
            return f"{match.group(1)}%"
        
        # 패턴이 매치되지 않으면 원본 파일명 반환
        return basename
        
    except Exception:
        return os.path.splitext(filename)[0]


def format_legend_label(filename: str) -> str:
    """
    범례 라벨 포맷팅
    
    Args:
        filename: 파일명
        
    Returns:
        포맷팅된 범례 라벨
    """
    return extract_percentage_from_filename(filename) or os.path.splitext(filename)[0]


def get_clean_variable_name(var_name: str) -> str:
    """
    변수명을 그래프 제목에 적합하게 정리
    
    Args:
        var_name: 원본 변수명
        
    Returns:
        정리된 변수명
    """
    # 특수문자나 공백 정리
    clean_name = var_name.replace('_', ' ').replace('-', ' ')
    
    # 첫 글자 대문자화
    clean_name = clean_name.title()
    
    # 다시 언더스코어로 변환 (일관성 유지)
    clean_name = var_name
    
    return clean_name