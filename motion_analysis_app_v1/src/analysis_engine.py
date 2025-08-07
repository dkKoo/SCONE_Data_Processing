"""
개선된 분석 엔진 모듈
- 더 안전한 데이터 처리
- 향상된 보행 단계별 통계 계산
- 포괄적인 에러 처리
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from config.constants import RESAMPLE_POINTS, STATISTICS_CONFIG
from utils.math_utils import calculate_comprehensive_stats, validate_data
from utils.gait_analysis import (find_state_transitions, get_state_name, 
                                validate_state_data, validate_gait_cycles)


def calculate_dynamic_gait_phase_statistics(data_arr: np.ndarray, 
                                          state_arr: np.ndarray, 
                                          cycles: List[int]) -> Dict[str, Dict]:
    """
    개선된 실제 leg.state 데이터를 기반으로 각 보행 단계별 통계 계산
    
    Args:
        data_arr: 분석할 데이터 배열
        state_arr: 보행 상태 배열
        cycles: 보행 주기 시작점들
        
    Returns:
        dict: 각 단계별 통계 딕셔너리
    """
    # 기본 검증
    if len(cycles) < STATISTICS_CONFIG.get('min_cycles_required', 2):
        return {}
    
    # 보행 주기 유효성 검증
    is_valid_cycles, cycle_msg = validate_gait_cycles(cycles, len(data_arr))
    if not is_valid_cycles:
        print(f"보행 주기 검증 실패: {cycle_msg}")
        return {}
    
    # 상태 데이터 검증
    is_valid_state, state_msg, clean_state = validate_state_data(state_arr)
    if not is_valid_state:
        print(f"상태 데이터 검증 실패: {state_msg}")
        return {}
    
    try:
        # 각 보행 주기를 정규화하여 리샘플링
        normalized_data_cycles = []
        normalized_state_cycles = []
        
        for i in range(len(cycles)-1):
            cycle_start = cycles[i]
            cycle_end = cycles[i+1]
            
            # 인덱스 범위 확인
            if cycle_end >= len(data_arr) or cycle_start < 0:
                continue
                
            cycle_data = data_arr[cycle_start:cycle_end]
            cycle_state = clean_state[cycle_start:cycle_end]
            
            if len(cycle_data) >= 2:
                # 데이터를 0-100% 구간으로 정규화
                normalized_data = np.interp(
                    np.linspace(0, len(cycle_data)-1, RESAMPLE_POINTS),
                    np.arange(len(cycle_data)),
                    cycle_data
                )
                
                # state도 동일하게 정규화 (가장 가까운 값으로 매핑)
                normalized_state = np.round(np.interp(
                    np.linspace(0, len(cycle_state)-1, RESAMPLE_POINTS),
                    np.arange(len(cycle_state)),
                    cycle_state
                )).astype(int)
                
                # 상태 값 범위 제한 (0-4)
                normalized_state = np.clip(normalized_state, 0, 4)
                
                normalized_data_cycles.append(normalized_data)
                normalized_state_cycles.append(normalized_state)
        
        if not normalized_data_cycles:
            return {}
        
        # 모든 보행 주기에서 각 state별 데이터 수집
        phase_data = {}
        
        for cycle_idx, (data_cycle, state_cycle) in enumerate(zip(normalized_data_cycles, normalized_state_cycles)):
            # 현재 주기에서 state 전환 지점 찾기
            state_transitions = find_state_transitions(state_cycle)
            
            # 각 state별로 데이터 수집
            for state_name, ranges in state_transitions.items():
                if state_name not in phase_data:
                    phase_data[state_name] = []
                
                # 해당 state의 모든 구간에서 데이터 수집
                for start_idx, end_idx in ranges:
                    if start_idx <= end_idx < len(data_cycle):
                        phase_values = data_cycle[start_idx:end_idx+1]
                        # 유효한 값만 추가
                        valid_values = validate_data(phase_values)
                        if len(valid_values) > 0:
                            phase_data[state_name].extend(valid_values)
        
        # 각 단계별 포괄적 통계 계산
        phase_stats = {}
        ddof = STATISTICS_CONFIG.get('ddof', 0)
        remove_outliers = STATISTICS_CONFIG.get('remove_outliers', False)
        
        for state_name, data_points in phase_data.items():
            if data_points and len(data_points) > 0:
                # 포괄적인 통계 계산
                comprehensive_stats = calculate_comprehensive_stats(
                    data_points, 
                    ddof=ddof,
                    remove_outliers=remove_outliers,
                    include_percentiles=True
                )
                
                # 보행 특화 정보 추가
                comprehensive_stats.update({
                    'cycle_count': len(normalized_data_cycles),
                    'phase_name': state_name,
                    'data_coverage': len(data_points) / (len(normalized_data_cycles) * RESAMPLE_POINTS) * 100
                })
                
                phase_stats[state_name] = comprehensive_stats
            else:
                # 데이터가 없는 경우
                phase_stats[state_name] = {
                    'mean': np.nan,
                    'std': np.nan,
                    'max': np.nan,
                    'min': np.nan,
                    'median': np.nan,
                    'count': 0,
                    'cycle_count': len(normalized_data_cycles),
                    'phase_name': state_name,
                    'data_coverage': 0.0,
                    'total_count': 0,
                    'valid_count': 0,
                    'nan_count': 0,
                    'inf_count': 0,
                    'finite_percentage': 0.0
                }
        
        return phase_stats
        
    except Exception as e:
        print(f"보행 단계별 통계 계산 오류: {str(e)}")
        return {}


def calculate_overall_statistics(data_arr: np.ndarray, 
                               variable_name: str = "") -> Dict[str, any]:
    """
    전체 데이터에 대한 포괄적 통계 계산
    
    Args:
        data_arr: 분석할 데이터 배열
        variable_name: 변수명
        
    Returns:
        dict: 통계 결과
    """
    try:
        ddof = STATISTICS_CONFIG.get('ddof', 0)
        remove_outliers = STATISTICS_CONFIG.get('remove_outliers', False)
        
        # 포괄적 통계 계산
        stats = calculate_comprehensive_stats(
            data_arr, 
            ddof=ddof,
            remove_outliers=remove_outliers,
            include_percentiles=True
        )
        
        # 추가 정보
        stats.update({
            'variable_name': variable_name,
            'analysis_type': 'overall',
            'outliers_removed': remove_outliers,
            'ddof_used': ddof
        })
        
        return stats
        
    except Exception as e:
        print(f"전체 통계 계산 오류: {str(e)}")
        return {
            'variable_name': variable_name,
            'analysis_type': 'overall',
            'error': str(e),
            'mean': np.nan,
            'std': np.nan,
            'max': np.nan,
            'min': np.nan,
            'count': 0
        }


def analyze_variable_comprehensive(data_arr: np.ndarray, 
                                 state_arr: Optional[np.ndarray] = None,
                                 cycles: Optional[List[int]] = None,
                                 variable_name: str = "") -> Dict[str, any]:
    """
    변수에 대한 종합적인 분석
    
    Args:
        data_arr: 분석할 데이터 배열
        state_arr: 보행 상태 배열 (선택사항)
        cycles: 보행 주기 (선택사항)
        variable_name: 변수명
        
    Returns:
        dict: 종합 분석 결과
    """
    analysis_result = {
        'variable_name': variable_name,
        'overall_statistics': {},
        'gait_phase_statistics': {},
        'data_quality': {},
        'analysis_notes': []
    }
    
    try:
        # 1. 전체 통계 계산
        analysis_result['overall_statistics'] = calculate_overall_statistics(
            data_arr, variable_name
        )
        
        # 2. 데이터 품질 평가
        analysis_result['data_quality'] = evaluate_data_quality(data_arr)
        
        # 3. 보행 단계별 분석 (가능한 경우)
        if state_arr is not None and cycles is not None:
            try:
                phase_stats = calculate_dynamic_gait_phase_statistics(
                    data_arr, state_arr, cycles
                )
                analysis_result['gait_phase_statistics'] = phase_stats
                
                if phase_stats:
                    analysis_result['analysis_notes'].append(
                        f"보행 단계별 분석 완료: {len(phase_stats)}개 단계"
                    )
                else:
                    analysis_result['analysis_notes'].append(
                        "보행 단계별 분석 실패: 유효한 주기 없음"
                    )
            except Exception as e:
                analysis_result['analysis_notes'].append(
                    f"보행 단계별 분석 오류: {str(e)}"
                )
        
        # 4. 분석 품질 평가
        quality_score = assess_analysis_quality(analysis_result)
        analysis_result['quality_score'] = quality_score
        
        return analysis_result
        
    except Exception as e:
        analysis_result['error'] = str(e)
        analysis_result['analysis_notes'].append(f"분석 중 오류 발생: {str(e)}")
        return analysis_result


def evaluate_data_quality(data_arr: np.ndarray) -> Dict[str, any]:
    """
    데이터 품질 평가
    
    Returns:
        dict: 품질 평가 결과
    """
    try:
        data_clean = validate_data(data_arr)
        total_count = len(data_arr)
        valid_count = len(data_clean)
        
        quality_metrics = {
            'total_points': total_count,
            'valid_points': valid_count,
            'completeness': (valid_count / total_count * 100) if total_count > 0 else 0,
            'variability': np.std(data_clean) / np.mean(data_clean) if len(data_clean) > 0 and np.mean(data_clean) != 0 else np.nan,
            'range_ratio': (np.max(data_clean) - np.min(data_clean)) / np.mean(data_clean) if len(data_clean) > 0 and np.mean(data_clean) != 0 else np.nan
        }
        
        # 품질 등급 결정
        if quality_metrics['completeness'] >= 95:
            quality_metrics['grade'] = 'Excellent'
        elif quality_metrics['completeness'] >= 80:
            quality_metrics['grade'] = 'Good'
        elif quality_metrics['completeness'] >= 60:
            quality_metrics['grade'] = 'Fair'
        else:
            quality_metrics['grade'] = 'Poor'
        
        return quality_metrics
        
    except Exception as e:
        return {
            'error': str(e),
            'grade': 'Unknown',
            'total_points': len(data_arr),
            'valid_points': 0,
            'completeness': 0
        }


def assess_analysis_quality(analysis_result: Dict) -> float:
    """
    분석 품질 점수 계산 (0-100)
    
    Returns:
        float: 품질 점수
    """
    try:
        score = 0.0
        max_score = 100.0
        
        # 데이터 완성도 (40점)
        data_quality = analysis_result.get('data_quality', {})
        completeness = data_quality.get('completeness', 0)
        score += min(40, completeness * 0.4)
        
        # 통계 유효성 (30점)
        overall_stats = analysis_result.get('overall_statistics', {})
        if overall_stats.get('count', 0) > 10:
            score += 15
        if not np.isnan(overall_stats.get('mean', np.nan)):
            score += 15
        
        # 보행 분석 가능성 (30점)
        gait_stats = analysis_result.get('gait_phase_statistics', {})
        if gait_stats:
            valid_phases = sum(1 for phase in gait_stats.values() 
                             if phase.get('count', 0) > 0)
            score += min(30, valid_phases * 6)
        
        return min(max_score, score)
        
    except Exception:
        return 0.0