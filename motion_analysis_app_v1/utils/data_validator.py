"""
데이터 검증 및 품질 관리 모듈
"""

import pandas as pd
import numpy as np
import os
from typing import List, Dict, Tuple, Optional


class DataValidator:
    """데이터 검증 클래스"""
    
    def __init__(self, min_data_points=10, max_file_size_mb=100):
        self.min_data_points = min_data_points
        self.max_file_size_mb = max_file_size_mb
    
    def validate_file_path(self, file_path: str) -> Tuple[bool, str]:
        """파일 경로 검증"""
        if not isinstance(file_path, str):
            return False, "파일 경로가 문자열이 아닙니다."
        
        if not os.path.exists(file_path):
            return False, f"파일이 존재하지 않습니다: {file_path}"
        
        if not os.path.isfile(file_path):
            return False, f"디렉토리입니다. 파일을 선택해주세요: {file_path}"
        
        # 파일 크기 검증
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            return False, f"파일이 너무 큽니다 ({file_size_mb:.1f}MB > {self.max_file_size_mb}MB)"
        
        # 파일 확장자 검증
        valid_extensions = ['.csv', '.sto', '.txt']
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in valid_extensions:
            return False, f"지원하지 않는 파일 형식입니다: {file_ext}"
        
        return True, "파일 경로가 유효합니다."
    
    def validate_dataframe(self, df: pd.DataFrame, file_path: str = "") -> Tuple[bool, str, Dict]:
        """DataFrame 검증"""
        validation_info = {
            'file_path': file_path,
            'row_count': len(df),
            'column_count': len(df.columns),
            'numeric_columns': [],
            'non_numeric_columns': [],
            'empty_columns': [],
            'columns_with_all_nan': [],
            'memory_usage_mb': 0.0
        }
        
        try:
            # 기본 검증
            if df.empty:
                return False, "데이터프레임이 비어있습니다.", validation_info
            
            if len(df) < self.min_data_points:
                return False, f"데이터 포인트가 너무 적습니다 ({len(df)} < {self.min_data_points})", validation_info
            
            # 메모리 사용량 계산
            validation_info['memory_usage_mb'] = df.memory_usage(deep=True).sum() / (1024 * 1024)
            
            # 컬럼 분석
            for col in df.columns:
                if df[col].isna().all():
                    validation_info['columns_with_all_nan'].append(col)
                elif df[col].dropna().empty:
                    validation_info['empty_columns'].append(col)
                elif pd.api.types.is_numeric_dtype(df[col]):
                    validation_info['numeric_columns'].append(col)
                else:
                    validation_info['non_numeric_columns'].append(col)
            
            # 숫자 컬럼이 하나도 없으면 경고
            if not validation_info['numeric_columns']:
                return False, "분석 가능한 숫자 컬럼이 없습니다.", validation_info
            
            return True, "데이터프레임이 유효합니다.", validation_info
            
        except Exception as e:
            return False, f"데이터프레임 검증 중 오류: {str(e)}", validation_info
    
    def validate_column_data(self, data: pd.Series, column_name: str = "") -> Tuple[bool, str, Dict]:
        """개별 컬럼 데이터 검증"""
        validation_info = {
            'column_name': column_name,
            'total_count': len(data),
            'null_count': data.isna().sum(),
            'unique_count': 0,
            'data_type': str(data.dtype),
            'is_numeric': False,
            'has_infinite': False,
            'value_range': None
        }
        
        try:
            if data.empty:
                return False, f"컬럼 '{column_name}'이 비어있습니다.", validation_info
            
            # 고유값 개수
            validation_info['unique_count'] = data.nunique()
            
            # 숫자 데이터 검증
            if pd.api.types.is_numeric_dtype(data):
                validation_info['is_numeric'] = True
                
                # 무한값 검사
                validation_info['has_infinite'] = np.isinf(data).any()
                
                # 유효한 데이터로 범위 계산
                valid_data = data.dropna()
                if not valid_data.empty:
                    finite_data = valid_data[np.isfinite(valid_data)]
                    if not finite_data.empty:
                        validation_info['value_range'] = (finite_data.min(), finite_data.max())
                
                # 모든 값이 동일한지 확인
                if validation_info['unique_count'] == 1:
                    return False, f"컬럼 '{column_name}'의 모든 값이 동일합니다.", validation_info
            
            # 너무 많은 결측값
            null_percentage = validation_info['null_count'] / validation_info['total_count'] * 100
            if null_percentage > 90:
                return False, f"컬럼 '{column_name}'에 결측값이 너무 많습니다 ({null_percentage:.1f}%)", validation_info
            
            return True, f"컬럼 '{column_name}'이 유효합니다.", validation_info
            
        except Exception as e:
            return False, f"컬럼 '{column_name}' 검증 중 오류: {str(e)}", validation_info
    
    def get_file_encoding(self, file_path: str) -> str:
        """파일 인코딩 감지"""
        encodings = ['utf-8', 'utf-8-sig', 'euc-kr', 'cp949', 'latin1', 'ascii']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1024)  # 첫 1KB만 읽어서 테스트
                return encoding
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        return 'utf-8'  # 기본값
    
    def suggest_header_row(self, file_path: str, max_rows_to_check: int = 20) -> int:
        """헤더 행 자동 감지"""
        try:
            encoding = self.get_file_encoding(file_path)
            
            # 여러 행을 시도해보며 가장 적절한 헤더 행 찾기
            best_header_row = 0
            max_numeric_cols = 0
            
            for header_row in range(min(max_rows_to_check, 10)):
                try:
                    df = pd.read_csv(file_path, header=header_row, nrows=5, encoding=encoding)
                    numeric_cols = sum(1 for col in df.columns if pd.api.types.is_numeric_dtype(df[col]))
                    
                    if numeric_cols > max_numeric_cols:
                        max_numeric_cols = numeric_cols
                        best_header_row = header_row
                        
                except Exception:
                    continue
            
            return best_header_row
            
        except Exception:
            return 0  # 기본값


class GaitDataValidator(DataValidator):
    """보행 데이터 전용 검증 클래스"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.required_state_cols = ['leg1_r.state', 'leg0_l.state']
        self.valid_state_values = [0, 1, 2, 3, 4]
    
    def validate_gait_data(self, df: pd.DataFrame) -> Tuple[bool, str, Dict]:
        """보행 데이터 특화 검증"""
        base_valid, base_msg, base_info = self.validate_dataframe(df)
        
        gait_info = {
            **base_info,
            'has_time_column': False,
            'available_state_columns': [],
            'gait_variables': {'left': [], 'right': []},
            'potential_cycles': 0
        }
        
        if not base_valid:
            return base_valid, base_msg, gait_info
        
        # Time 컬럼 확인
        time_cols = [col for col in df.columns if 'time' in col.lower()]
        gait_info['has_time_column'] = len(time_cols) > 0
        
        # State 컬럼 확인
        for state_col in self.required_state_cols:
            if state_col in df.columns:
                gait_info['available_state_columns'].append(state_col)
                
                # State 값 검증
                state_data = df[state_col].dropna()
                unique_states = set(state_data.unique())
                
                if not unique_states.issubset(set(self.valid_state_values)):
                    return False, f"잘못된 state 값이 발견됨: {unique_states - set(self.valid_state_values)}", gait_info
        
        # 보행 변수 분류
        for col in gait_info['numeric_columns']:
            if '_r' in col:
                gait_info['gait_variables']['right'].append(col)
            elif '_l' in col:
                gait_info['gait_variables']['left'].append(col)
        
        # 보행 주기 추정
        if gait_info['available_state_columns']:
            state_col = gait_info['available_state_columns'][0]
            cycles = self._estimate_gait_cycles(df[state_col])
            gait_info['potential_cycles'] = len(cycles)
        
        return True, "보행 데이터가 유효합니다.", gait_info
    
    def _estimate_gait_cycles(self, state_data: pd.Series) -> List[int]:
        """보행 주기 추정"""
        try:
            cycles = []
            prev_state = None
            
            for i, current_state in enumerate(state_data):
                if prev_state == 4 and current_state == 0:  # Landing -> EarlyStance
                    cycles.append(i)
                prev_state = current_state
            
            return cycles
        except Exception:
            return []