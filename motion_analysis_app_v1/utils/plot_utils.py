"""
개선된 플롯 관련 유틸리티 함수들
- 일관된 통계 계산
- 더 나은 시각화 옵션
- 에러 처리 강화
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, Tuple, List
from config.constants import SD_RANGE
from utils.math_utils import validate_data, safe_mean, safe_std


def plot_with_sd(ax, x, data, label, sd=SD_RANGE, ddof=0, alpha=0.2, 
                 line_color=None, fill_color=None, remove_outliers=False):
    """
    개선된 평균과 표준편차 영역을 포함한 선 그래프 그리기
    
    Args:
        ax: matplotlib axes 객체
        x: x축 데이터
        data: y축 데이터
        label: 범례 라벨
        sd: 표준편차 범위 (기본 2SD)
        ddof: 자유도 (0=모집단, 1=표본)
        alpha: 투명도
        line_color: 라인 색상
        fill_color: 채우기 색상
        remove_outliers: 이상값 제거 여부
    
    Returns:
        그려진 line 객체
    """
    try:
        # 데이터 검증 및 정리
        clean_data = validate_data(data, remove_outliers=remove_outliers)
        
        if len(clean_data) == 0:
            # 빈 데이터인 경우 경고 표시
            ax.text(0.5, 0.5, f'No valid data for {label}', 
                   transform=ax.transAxes, ha='center', va='center',
                   bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
            return None
        
        # 통계값 계산 (일관된 ddof 사용)
        mean_val = safe_mean(clean_data, remove_outliers=remove_outliers)
        std_val = safe_std(clean_data, ddof=ddof, remove_outliers=remove_outliers)
        
        if np.isnan(mean_val) or np.isnan(std_val):
            # 통계값을 계산할 수 없는 경우
            line = ax.plot(x, data, label=f'{label} (no stats)', 
                          color=line_color, alpha=0.7)
            return line[0] if line else None
        
        # 메인 라인 그리기
        line = ax.plot(x, data, label=label, color=line_color)
        line_color_actual = line[0].get_color() if line else 'blue'
        
        # 표준편차 영역 그리기 (데이터 길이에 맞춰)
        if len(x) == len(data):
            upper_bound = data + sd * std_val
            lower_bound = data - sd * std_val
            
            fill_color_actual = fill_color if fill_color else line_color_actual
            ax.fill_between(x, lower_bound, upper_bound, 
                           alpha=alpha, color=fill_color_actual,
                           label=f'{label} ±{sd}SD' if sd != SD_RANGE else None)
        
        return line[0] if line else None
        
    except Exception as e:
        print(f"plot_with_sd 오류: {str(e)}")
        # 오류 발생 시 기본 플롯
        try:
            line = ax.plot(x, data, label=f'{label} (error)', alpha=0.5)
            return line[0] if line else None
        except:
            return None


def plot_comparison_with_stats(ax, datasets, labels, x_data=None, 
                              show_confidence=True, ddof=0, remove_outliers=False):
    """
    여러 데이터셋 비교 플롯 (통계 정보 포함)
    
    Args:
        ax: matplotlib axes 객체
        datasets: 데이터셋 리스트
        labels: 라벨 리스트
        x_data: x축 데이터 (None이면 인덱스 사용)
        show_confidence: 신뢰구간 표시 여부
        ddof: 자유도
        remove_outliers: 이상값 제거 여부
    """
    colors = plt.cm.Set1(np.linspace(0, 1, len(datasets)))
    
    for i, (data, label) in enumerate(zip(datasets, labels)):
        if x_data is None:
            x = np.arange(len(data))
        else:
            x = x_data
            
        plot_with_sd(ax, x, data, label, 
                    line_color=colors[i], 
                    ddof=ddof,
                    remove_outliers=remove_outliers)
    
    ax.legend()
    ax.grid(True, alpha=0.3)


def create_statistical_summary_plot(data_dict, title="Statistical Summary", 
                                   figsize=(12, 8), ddof=0, remove_outliers=False):
    """
    통계 요약 플롯 생성
    
    Args:
        data_dict: {변수명: 데이터} 딕셔너리
        title: 플롯 제목
        figsize: 그림 크기
        ddof: 자유도
        remove_outliers: 이상값 제거 여부
    
    Returns:
        fig, axes: matplotlib 객체들
    """
    n_vars = len(data_dict)
    if n_vars == 0:
        return None, None
    
    # 서브플롯 레이아웃 계산
    cols = min(3, n_vars)
    rows = (n_vars + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=figsize)
    if n_vars == 1:
        axes = [axes]
    elif rows == 1:
        axes = axes.flatten() if hasattr(axes, 'flatten') else [axes]
    else:
        axes = axes.flatten()
    
    for i, (var_name, data) in enumerate(data_dict.items()):
        if i >= len(axes):
            break
            
        ax = axes[i]
        
        # 히스토그램과 통계 정보
        clean_data = validate_data(data, remove_outliers=remove_outliers)
        
        if len(clean_data) > 0:
            ax.hist(clean_data, bins=30, alpha=0.7, density=True)
            
            # 통계 정보 텍스트
            mean_val = safe_mean(clean_data)
            std_val = safe_std(clean_data, ddof=ddof)
            
            stats_text = f'Mean: {mean_val:.3f}\nStd: {std_val:.3f}\nN: {len(clean_data)}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   verticalalignment='top', fontsize=8,
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        else:
            ax.text(0.5, 0.5, 'No valid data', transform=ax.transAxes, 
                   ha='center', va='center')
        
        ax.set_title(var_name, fontsize=10)
        ax.set_xlabel('Value')
        ax.set_ylabel('Density')
    
    # 빈 서브플롯 숨기기
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)
    
    plt.suptitle(title, fontsize=14)
    plt.tight_layout()
    
    return fig, axes


def setup_plot_style():
    """플롯 스타일 설정"""
    plt.style.use('default')
    plt.rcParams.update({
        'font.size': 10,
        'axes.titlesize': 12,
        'axes.labelsize': 10,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 9,
        'figure.titlesize': 14,
        'lines.linewidth': 1.5,
        'axes.grid': True,
        'grid.alpha': 0.3
    })


def save_plot_safely(fig, filepath, dpi=300, bbox_inches='tight'):
    """안전한 플롯 저장"""
    try:
        fig.savefig(filepath, dpi=dpi, bbox_inches=bbox_inches, 
                   facecolor='white', edgecolor='none')
        return True, f"플롯이 저장되었습니다: {filepath}"
    except Exception as e:
        return False, f"플롯 저장 실패: {str(e)}"


def create_gait_cycle_plot(ax, normalized_cycles, x_percent, label, 
                          show_individual=False, alpha_individual=0.1):
    """
    보행 주기 플롯 생성
    
    Args:
        ax: matplotlib axes
        normalized_cycles: 정규화된 보행 주기 데이터 (2D array)
        x_percent: 0-100% x축 데이터
        label: 라벨
        show_individual: 개별 주기 표시 여부
        alpha_individual: 개별 주기 투명도
    """
    if len(normalized_cycles) == 0:
        return
    
    # 개별 주기 표시 (옵션)
    if show_individual:
        for cycle in normalized_cycles:
            ax.plot(x_percent, cycle, alpha=alpha_individual, color='gray')
    
    # 평균과 표준편차
    mean_cycle = np.nanmean(normalized_cycles, axis=0)
    std_cycle = np.nanstd(normalized_cycles, axis=0)
    
    # 메인 라인
    ax.plot(x_percent, mean_cycle, label=label, linewidth=2)
    
    # 신뢰구간
    ax.fill_between(x_percent, 
                    mean_cycle - 2*std_cycle, 
                    mean_cycle + 2*std_cycle, 
                    alpha=0.2, label=f'{label} ±2SD')
    
    ax.set_xlabel('Gait Cycle (%)')
    ax.set_ylabel('Value')
    ax.legend()
    ax.grid(True, alpha=0.3)