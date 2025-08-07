"""
개선된 메인 애플리케이션 클래스 v2.0
- 강화된 데이터 검증과 연동
- 향상된 사용자 경험
- 실시간 진행 상황 모니터링
- 포괄적인 에러 처리
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import os
import threading
import time
from typing import List, Dict, Optional, Tuple

# 개선된 모듈들 import
from config.constants import (HEADER_DEFAULT_ROW, VALIDATION_CONFIG, 
                             STATISTICS_CONFIG, GUI_CONFIG, ERROR_MESSAGES, SUCCESS_MESSAGES)
from config.language import get_language, get_message
from utils.data_validator import DataValidator, GaitDataValidator
from utils.gait_analysis import get_leg_and_state_col, find_gait_cycles, resample_cycle, analyze_gait_pattern
from utils.math_utils import calculate_comprehensive_stats
from utils.plot_utils import plot_with_sd, create_statistical_summary_plot, setup_plot_style
from utils.file_utils import format_legend_label, get_clean_variable_name
from src.analysis_engine import (calculate_dynamic_gait_phase_statistics, 
                                analyze_variable_comprehensive)


class MotionAnalysisApp:
    def __init__(self, root, lang=None):
        """
        개선된 애플리케이션 초기화
        """
        self.root = root
        self.lang = lang or get_language('ko')
        
        # 윈도우 설정
        self.root.title(self.lang['app_title'])
        window_size = GUI_CONFIG['window_size']
        self.root.geometry(f"{window_size[0]}x{window_size[1]}")
        
        # 데이터 저장을 위한 변수
        self.dataframes: List[pd.DataFrame] = []
        self.file_paths: List[str] = []
        self.results_data = ""
        self.selected_vars: List[str] = []
        self.graph_vars: List[str] = []
        self.last_fig = None
        self.all_columns: List[str] = []
        self.analysis_results: Dict = {}
        
        # 검증 객체
        self.data_validator = DataValidator()
        self.gait_validator = GaitDataValidator()
        
        # 진행 상황 추적
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar()
        self.status_var.set("준비됨")
        
        # 스타일 설정
        self._setup_styles()
        
        # GUI 생성
        self._create_gui()
        
        # 플롯 스타일 설정
        setup_plot_style()
    
    def _setup_styles(self):
        """스타일 설정"""
        style = ttk.Style(self.root)
        style.theme_use(GUI_CONFIG.get('theme', 'clam'))
        
        # 폰트 설정
        font_family = GUI_CONFIG.get('font_family', 'Malgun Gothic')
        font_size = GUI_CONFIG.get('font_size', 10)
        
        style.configure('Title.TLabel', font=(font_family, font_size + 2, 'bold'))
        style.configure('Status.TLabel', font=(font_family, font_size - 1))
    
    def _create_gui(self):
        """컴팩트한 GUI 레이아웃 생성"""
        # 메인 컨테이너
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 1. 상단 - 파일 선택 및 진행 상황 (한 줄로 통합)
        self._create_header_section(main_container)
        
        # 2. 메인 - 작업 영역 (좌측: 변수 선택, 우측: 결과)
        self._create_main_work_area(main_container)
        
        # 3. 하단 - 버튼 영역 (컴팩트하게)
        self._create_compact_button_section(main_container)
        
        # 이벤트 바인딩
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def _create_header_section(self, parent):
        """상단 헤더 영역 (파일 선택 + 진행 상황)"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 좌측: 파일 선택
        file_frame = ttk.LabelFrame(header_frame, text=self.lang['select_file'], padding="5")
        file_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # 파일 선택 버튼과 정보를 한 줄로
        file_top_frame = ttk.Frame(file_frame)
        file_top_frame.pack(fill=tk.X, pady=(0, 3))
        
        self.load_button = ttk.Button(file_top_frame, text=self.lang['open_file'], 
                                     command=self.load_files)
        self.load_button.pack(side=tk.LEFT)
        
        self.file_info_var = tk.StringVar()
        self.file_info_label = ttk.Label(file_top_frame, textvariable=self.file_info_var,
                                        style='Status.TLabel')
        self.file_info_label.pack(side=tk.RIGHT)
        
        # 파일명 표시
        self.file_label = ttk.Label(file_frame, text=self.lang['file_not_selected'], 
                                   foreground="grey", style='Status.TLabel')
        self.file_label.pack(anchor=tk.W)
        
        # 우측: 진행 상황 (더 컴팩트하게)
        progress_frame = ttk.LabelFrame(header_frame, text="진행 상황", padding="5")
        progress_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # 진행률 바와 상태를 한 줄로
        progress_top_frame = ttk.Frame(progress_frame)
        progress_top_frame.pack(fill=tk.X)
        
        self.progress_bar = ttk.Progressbar(progress_top_frame, variable=self.progress_var,
                                           maximum=100, length=200)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.status_label = ttk.Label(progress_top_frame, textvariable=self.status_var,
                                     style='Status.TLabel', width=15)
        self.status_label.pack(side=tk.RIGHT)
    
    def _create_main_work_area(self, parent):
        """메인 작업 영역"""
        work_frame = ttk.Frame(parent)
        work_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 좌측 - 변수 선택 영역
        self._create_variable_section(work_frame)
        
        # 우측 - 결과 표시 영역
        self._create_results_section(work_frame)
    
    def _create_variable_section(self, parent):
        """컴팩트한 변수 선택 영역"""
        var_container = ttk.Frame(parent)
        var_container.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        
        # 상단: 변수 선택과 검색을 한 프레임에
        vars_frame = ttk.LabelFrame(var_container, text="변수 관리", padding="5")
        vars_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 3))
        
        # 검색 기능 (더 컴팩트하게)
        search_frame = ttk.Frame(vars_frame)
        search_frame.pack(fill=tk.X, pady=(0, 3))
        
        ttk.Label(search_frame, text="검색:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self._on_search_change)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=18)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))
        
        # 변수 목록 (높이 줄임)
        list_frame = ttk.Frame(vars_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.var_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, 
                                     exportselection=False, width=22, height=8)
        self.var_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        var_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, 
                                     command=self.var_listbox.yview)
        var_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.var_listbox.config(yscrollcommand=var_scrollbar.set)
        
        # 변수 관리 버튼 (더 컴팩트하게)
        var_btn_frame = ttk.Frame(vars_frame)
        var_btn_frame.pack(fill=tk.X, pady=(3, 0))
        
        ttk.Button(var_btn_frame, text="→ 선택",
                  command=self.add_to_select_list).pack(fill=tk.X)
        
        # 중간: 선택된 변수 목록
        select_frame = ttk.LabelFrame(var_container, text="선택된 변수", padding="5")
        select_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 3))
        
        self.select_listbox = tk.Listbox(select_frame, selectmode=tk.MULTIPLE,
                                        exportselection=False, width=22, height=5)
        self.select_listbox.pack(fill=tk.BOTH, expand=True)
        
        select_btn_frame = ttk.Frame(select_frame)
        select_btn_frame.pack(fill=tk.X, pady=(3, 0))
        
        # 버튼을 가로로 배치
        ttk.Button(select_btn_frame, text="삭제",
                  command=self.remove_from_select_list).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(select_btn_frame, text="→ 그래프",
                  command=self.add_to_graph_list).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 하단: 그래프 변수 목록
        graph_frame = ttk.LabelFrame(var_container, text="그래프 변수", padding="5")
        graph_frame.pack(fill=tk.BOTH, expand=True)
        
        self.graph_listbox = tk.Listbox(graph_frame, selectmode=tk.MULTIPLE,
                                       exportselection=False, width=22, height=4)
        self.graph_listbox.pack(fill=tk.BOTH, expand=True)
        
        graph_btn_frame = ttk.Frame(graph_frame)
        graph_btn_frame.pack(fill=tk.X, pady=(3, 0))
        
        # 그래프 버튼들을 2x2 그리드로 배치
        btn_grid = ttk.Frame(graph_btn_frame)
        btn_grid.pack(fill=tk.X)
        
        ttk.Button(btn_grid, text="삭제",
                  command=self.remove_from_graph_list).grid(row=0, column=0, sticky="ew", padx=(0, 2))
        ttk.Button(btn_grid, text="그래프",
                  command=self.plot_graph).grid(row=0, column=1, sticky="ew")
        ttk.Button(btn_grid, text="정규화",
                  command=self.plot_normalized_gait_graph).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 0))
        
        btn_grid.grid_columnconfigure(0, weight=1)
        btn_grid.grid_columnconfigure(1, weight=1)
    
    def _create_results_section(self, parent):
        """결과 표시 영역"""
        results_container = ttk.Frame(parent)
        results_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 탭 구성
        notebook = ttk.Notebook(results_container)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 분석 결과 탭
        results_frame = ttk.Frame(notebook)
        notebook.add(results_frame, text=self.lang['analysis_result'])
        
        self.results_text = tk.Text(results_frame, wrap=tk.WORD, state=tk.DISABLED,
                                   font=('Consolas', 9))
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        results_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL,
                                         command=self.results_text.yview)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_text.config(yscrollcommand=results_scrollbar.set)
        
        # 데이터 품질 탭
        quality_frame = ttk.Frame(notebook)
        notebook.add(quality_frame, text=self.lang['data_quality'])
        
        self.quality_text = tk.Text(quality_frame, wrap=tk.WORD, state=tk.DISABLED,
                                   font=('Consolas', 9))
        self.quality_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        quality_scrollbar = ttk.Scrollbar(quality_frame, orient=tk.VERTICAL,
                                         command=self.quality_text.yview)
        quality_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.quality_text.config(yscrollcommand=quality_scrollbar.set)
    
    def _create_compact_button_section(self, parent):
        """컴팩트한 버튼 영역"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        # 좌측: 분석 버튼
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)
        
        self.analyze_button = ttk.Button(left_frame, text=self.lang['run_analysis'],
                                        command=self.run_analysis_thread, state=tk.DISABLED)
        self.analyze_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 중간: 저장 버튼들
        middle_frame = ttk.Frame(button_frame)
        middle_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.save_button = ttk.Button(middle_frame, text=self.lang['save_result'],
                                     command=self.save_results, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(middle_frame, text="그래프 저장",
                  command=self.save_graphs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(middle_frame, text="정규화 저장",
                  command=self.save_normalized_graphs).pack(side=tk.LEFT)
        
        # 우측: 상태 표시 (상태바 대신)
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side=tk.RIGHT)
        
        self.status_bar_var = tk.StringVar()
        self.status_bar_var.set("준비됨")
        
        ttk.Label(right_frame, textvariable=self.status_bar_var,
                 style='Status.TLabel').pack(side=tk.RIGHT, padx=(10, 0))
    
    def _on_search_change(self, *args):
        """검색어 변경 시 호출"""
        search_text = self.search_var.get().lower()
        self.var_listbox.delete(0, tk.END)
        
        for col in self.all_columns:
            if search_text in col.lower():
                self.var_listbox.insert(tk.END, col)
    
    def _update_progress(self, value: float, message: str = ""):
        """진행 상황 업데이트"""
        self.progress_var.set(value)
        if message:
            self.status_var.set(message)
            self.status_bar_var.set(message)
        self.root.update_idletasks()
    
    def _set_text_content(self, text_widget, content: str):
        """텍스트 위젯 내용 설정"""
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)
        text_widget.insert(tk.END, content)
        text_widget.config(state=tk.DISABLED)
    
    def load_files(self):
        """개선된 파일 로딩"""
        lang = self.lang
        
        # 파일 선택
        file_types = [
            (lang['csv_file'], "*.csv"),
            ("STO 파일", "*.sto"),
            ("텍스트 파일", "*.txt"),
            (lang['all_file'], "*.*")
        ]
        
        self.file_paths = filedialog.askopenfilenames(
            title=lang['open_file'],
            filetypes=file_types
        )
        
        if not self.file_paths:
            return
        
        # 진행 상황 초기화
        self._update_progress(0, self.lang['loading_file'])
        
        try:
            self.dataframes = []
            columns_set = None
            validation_results = []
            
            total_files = len(self.file_paths)
            
            for i, path in enumerate(self.file_paths):
                # 진행 상황 업데이트
                progress = (i / total_files) * 50  # 로딩은 전체의 50%
                self._update_progress(progress, f"파일 로딩 중: {os.path.basename(path)}")
                
                # 파일 경로 검증
                is_valid_path, path_msg = self.data_validator.validate_file_path(path)
                if not is_valid_path:
                    messagebox.showerror(lang['file_error'], path_msg)
                    continue
                
                try:
                    # 헤더 행 자동 감지
                    suggested_header = self.data_validator.suggest_header_row(path)
                    header_row = suggested_header if suggested_header is not None else HEADER_DEFAULT_ROW - 1
                    
                    # 인코딩 감지
                    encoding = self.data_validator.get_file_encoding(path)
                    
                    # 파일 읽기
                    df = pd.read_csv(path, header=header_row, sep=r'\s*,\s*|\t', 
                                   engine='python', encoding=encoding)
                    
                    # 데이터프레임 검증
                    is_valid_df, df_msg, df_info = self.data_validator.validate_dataframe(df, path)
                    validation_results.append({
                        'file': os.path.basename(path),
                        'valid': is_valid_df,
                        'message': df_msg,
                        'info': df_info
                    })
                    
                    if is_valid_df:
                        self.dataframes.append(df)
                        
                        # 공통 컬럼 계산
                        current_cols = set([col for col in df.columns if col.lower() != 'time'])
                        if columns_set is None:
                            columns_set = current_cols
                        else:
                            columns_set &= current_cols
                    else:
                        messagebox.showwarning(lang['file_error'], 
                                             f"{os.path.basename(path)}: {df_msg}")
                
                except Exception as e:
                    error_msg = f"파일 '{os.path.basename(path)}' 로딩 실패: {str(e)}"
                    validation_results.append({
                        'file': os.path.basename(path),
                        'valid': False,
                        'message': error_msg,
                        'info': {}
                    })
                    messagebox.showerror(lang['file_error'], error_msg)
            
            # 로딩 완료 처리
            self._update_progress(75, self.lang['validating_data'])
            
            if not self.dataframes:
                messagebox.showerror(lang['file_error'], "로딩된 파일이 없습니다.")
                self._update_progress(0, "오류 발생")
                return
            
            # 변수 목록 업데이트
            self.all_columns = sorted(list(columns_set)) if columns_set else []
            self.var_listbox.delete(0, tk.END)
            for col in self.all_columns:
                self.var_listbox.insert(tk.END, col)
            
            # UI 업데이트
            file_names = [os.path.basename(p) for p in self.file_paths]
            self.file_label.config(text=f"{len(file_names)}개 파일: {', '.join(file_names[:3])}{'...' if len(file_names) > 3 else ''}")
            self.file_info_var.set(f"총 {len(self.all_columns)}개 변수")
            
            # 버튼 상태 업데이트
            self.analyze_button.config(state=tk.NORMAL)
            self.save_button.config(state=tk.DISABLED)
            
            # 결과 텍스트 초기화
            self._set_text_content(self.results_text, self.lang['file_loaded'])
            
            # 데이터 품질 정보 표시
            self._display_validation_results(validation_results)
            
            # 목록 초기화
            self.select_listbox.delete(0, tk.END)
            self.graph_listbox.delete(0, tk.END)
            
            self._update_progress(100, f"{len(self.dataframes)}개 파일 로딩 완료")
            
            # 잠시 후 진행률 초기화
            self.root.after(2000, lambda: self._update_progress(0, "준비됨"))
            
        except Exception as e:
            error_msg = f"파일 로딩 중 오류: {str(e)}"
            messagebox.showerror(lang['file_error'], error_msg)
            self._update_progress(0, "오류 발생")
            self.dataframes = []
            self.analyze_button.config(state=tk.DISABLED)
    
    def _display_validation_results(self, validation_results: List[Dict]):
        """데이터 검증 결과 표시"""
        quality_content = "=== 데이터 검증 결과 ===\n\n"
        
        for result in validation_results:
            quality_content += f"파일: {result['file']}\n"
            quality_content += f"상태: {'✓ 유효' if result['valid'] else '✗ 오류'}\n"
            quality_content += f"메시지: {result['message']}\n"
            
            if result['info']:
                info = result['info']
                quality_content += f"  - 행 수: {info.get('row_count', 'N/A')}\n"
                quality_content += f"  - 컬럼 수: {info.get('column_count', 'N/A')}\n"
                quality_content += f"  - 숫자 컬럼: {len(info.get('numeric_columns', []))}\n"
                quality_content += f"  - 메모리 사용: {info.get('memory_usage_mb', 0):.1f}MB\n"
            
            quality_content += "-" * 50 + "\n\n"
        
        self._set_text_content(self.quality_text, quality_content)
    
    def add_to_select_list(self):
        """선택 목록에 추가"""
        selected = self.var_listbox.curselection()
        for i in selected:
            var = self.var_listbox.get(i)
            if var not in self.select_listbox.get(0, tk.END):
                self.select_listbox.insert(tk.END, var)
        self.var_listbox.selection_clear(0, tk.END)
    
    def remove_from_select_list(self):
        """선택 목록에서 제거"""
        selected = list(self.select_listbox.curselection())[::-1]
        for i in selected:
            self.select_listbox.delete(i)
    
    def add_to_graph_list(self):
        """그래프 목록에 추가"""
        selected = self.select_listbox.curselection()
        for i in selected:
            var = self.select_listbox.get(i)
            if var not in self.graph_listbox.get(0, tk.END):
                self.graph_listbox.insert(tk.END, var)
    
    def remove_from_graph_list(self):
        """그래프 목록에서 제거"""
        selected = list(self.graph_listbox.curselection())[::-1]
        for i in selected:
            self.graph_listbox.delete(i)
    
    def run_analysis_thread(self):
        """분석 실행 (별도 스레드)"""
        self.analyze_button.config(state=tk.DISABLED)
        threading.Thread(target=self.analyze_data, daemon=True).start()
    
    def analyze_data(self):
        """개선된 데이터 분석"""
        try:
            lang = self.lang
            self._update_progress(0, lang['analysis_progress'])
            
            selected_vars = list(self.select_listbox.get(0, tk.END))
            if not selected_vars:
                messagebox.showwarning(lang['select_error'], lang['select_error'])
                return
            
            if not self.dataframes:
                messagebox.showwarning(lang['data_error'], lang['data_error'])
                return
            
            self.results_data = ""
            self.analysis_results = {}
            
            total_variables = len(selected_vars) * len(self.dataframes)
            current_var = 0
            
            for file_idx, (path, df) in enumerate(zip(self.file_paths, self.dataframes)):
                file_name = os.path.basename(path)
                self.results_data += f"{'='*60}\n"
                self.results_data += f"파일: {file_name}\n"
                self.results_data += f"{'='*60}\n\n"
                
                # 보행 데이터 검증
                gait_valid, gait_msg, gait_info = self.gait_validator.validate_gait_data(df)
                if gait_valid:
                    self.results_data += f"보행 데이터 검증: ✓ 통과\n"
                    self.results_data += f"  - 발견된 보행 주기: {gait_info.get('potential_cycles', 0)}개\n"
                    self.results_data += f"  - 좌측 변수: {len(gait_info.get('gait_variables', {}).get('left', []))}개\n"
                    self.results_data += f"  - 우측 변수: {len(gait_info.get('gait_variables', {}).get('right', []))}개\n\n"
                else:
                    self.results_data += f"보행 데이터 검증: ✗ 실패 - {gait_msg}\n\n"
                
                for var in selected_vars:
                    current_var += 1
                    progress = (current_var / total_variables) * 100
                    self._update_progress(progress, f"분석 중: {var} ({current_var}/{total_variables})")
                    
                    try:
                        if var not in df.columns:
                            self.results_data += f"변수: {var}\n"
                            self.results_data += f"  ✗ 오류: {lang['var_not_exist']}\n\n"
                            continue
                        
                        if not pd.api.types.is_numeric_dtype(df[var]):
                            self.results_data += f"변수: {var}\n"
                            self.results_data += f"  ✗ 오류: {lang['not_numeric']}\n\n"
                            continue
                        
                        # 포괄적 변수 분석
                        data_arr = df[var].values
                        
                        # 보행 관련 데이터 준비
                        leg_label, state_col = get_leg_and_state_col(var)
                        cycles = None
                        state_arr = None
                        
                        if leg_label and state_col and state_col in df.columns:
                            state_arr = df[state_col].values
                            cycles = find_gait_cycles(state_arr)
                        
                        # 종합 분석 실행
                        analysis_result = analyze_variable_comprehensive(
                            data_arr, state_arr, cycles, var
                        )
                        
                        # 결과 저장
                        analysis_key = f"{file_name}_{var}"
                        self.analysis_results[analysis_key] = analysis_result
                        
                        # 결과 텍스트 생성
                        self._format_analysis_result(analysis_result, file_name)
                        
                    except Exception as e:
                        self.results_data += f"변수 '{var}' 분석 중 오류: {str(e)}\n\n"
                
                self.results_data += "\n"
            
            # 분석 완료
            self._update_progress(100, lang['analysis_done'])
            self._set_text_content(self.results_text, self.results_data)
            self.save_button.config(state=tk.NORMAL)
            
            # 잠시 후 진행률 초기화
            self.root.after(2000, lambda: self._update_progress(0, "분석 완료"))
            
        except Exception as e:
            error_msg = f"분석 중 오류: {str(e)}"
            messagebox.showerror("분석 오류", error_msg)
            self._update_progress(0, "오류 발생")
        finally:
            self.analyze_button.config(state=tk.NORMAL)
    
    def _format_analysis_result(self, analysis_result: Dict, file_name: str):
        """분석 결과 포맷팅"""
        var_name = analysis_result['variable_name']
        
        self.results_data += f"변수: {var_name}\n"
        
        # 데이터 품질 정보
        quality = analysis_result.get('data_quality', {})
        self.results_data += f"  [데이터 품질: {quality.get('grade', 'Unknown')}]\n"
        self.results_data += f"  - 전체 데이터 포인트: {quality.get('total_points', 0):,}개\n"
        self.results_data += f"  - 유효 데이터 포인트: {quality.get('valid_points', 0):,}개\n"
        self.results_data += f"  - 완성도: {quality.get('completeness', 0):.1f}%\n"
        
        # 전체 통계
        overall_stats = analysis_result.get('overall_statistics', {})
        if overall_stats.get('count', 0) > 0:
            self.results_data += f"  \n  [전체 데이터 통계]\n"
            self.results_data += f"  - 평균: {overall_stats.get('mean', np.nan):.6f}\n"
            self.results_data += f"  - 표준편차: {overall_stats.get('std', np.nan):.6f}\n"
            self.results_data += f"  - 최댓값: {overall_stats.get('max', np.nan):.6f}\n"
            self.results_data += f"  - 최솟값: {overall_stats.get('min', np.nan):.6f}\n"
            self.results_data += f"  - 중앙값: {overall_stats.get('median', np.nan):.6f}\n"
            
            # 백분위수 정보
            if 'q25' in overall_stats and 'q75' in overall_stats:
                self.results_data += f"  - 25% 백분위수: {overall_stats.get('q25', np.nan):.6f}\n"
                self.results_data += f"  - 75% 백분위수: {overall_stats.get('q75', np.nan):.6f}\n"
                self.results_data += f"  - IQR: {overall_stats.get('iqr', np.nan):.6f}\n"
        
        # 보행 단계별 통계
        gait_stats = analysis_result.get('gait_phase_statistics', {})
        if gait_stats:
            self.results_data += f"  \n  [보행 단계별 통계]\n"
            self.results_data += f"  - 분석된 보행 주기: {list(gait_stats.values())[0].get('cycle_count', 0)}개\n\n"
            
            # 상태 순서대로 표시
            state_order = ['EarlyStance', 'LateStance', 'Liftoff', 'Swing', 'Landing']
            for phase_name in state_order:
                if phase_name in gait_stats:
                    stats = gait_stats[phase_name]
                    self.results_data += f"  [{phase_name}]\n"
                    self.results_data += f"    - 평균: {stats.get('mean', np.nan):.6f}\n"
                    self.results_data += f"    - 표준편차: {stats.get('std', np.nan):.6f}\n"
                    self.results_data += f"    - 최댓값: {stats.get('max', np.nan):.6f}\n"
                    self.results_data += f"    - 최솟값: {stats.get('min', np.nan):.6f}\n"
                    self.results_data += f"    - 데이터 포인트: {stats.get('count', 0)}개\n"
                    self.results_data += f"    - 데이터 커버리지: {stats.get('data_coverage', 0):.1f}%\n\n"
        
        # 분석 노트
        notes = analysis_result.get('analysis_notes', [])
        if notes:
            self.results_data += f"  [분석 노트]\n"
            for note in notes:
                self.results_data += f"  - {note}\n"
        
        # 품질 점수
        quality_score = analysis_result.get('quality_score', 0)
        self.results_data += f"  \n  [분석 품질 점수: {quality_score:.1f}/100]\n"
        
        self.results_data += "-" * 60 + "\n\n"
    
    def plot_graph(self):
        """개선된 그래프 그리기"""
        vars_to_plot = list(self.graph_listbox.get(0, tk.END))
        if not vars_to_plot:
            messagebox.showwarning(self.lang['graph_error'], self.lang['graph_error'])
            return
        
        if not self.dataframes:
            messagebox.showwarning(self.lang['data_error'], self.lang['data_error'])
            return
        
        self._update_progress(0, self.lang['generating_plots'])
        
        try:
            ddof = STATISTICS_CONFIG.get('ddof', 0)
            
            for i, var in enumerate(vars_to_plot):
                progress = (i / len(vars_to_plot)) * 100
                self._update_progress(progress, f"그래프 생성 중: {var}")
                
                fig, ax = plt.subplots(figsize=(10, 6))
                
                for path, df in zip(self.file_paths, self.dataframes):
                    if var not in df.columns:
                        continue
                    
                    data = df[var].values
                    x = np.arange(len(data))
                    
                    # 개선된 범례 라벨
                    filename = os.path.basename(path)
                    legend_label = format_legend_label(filename)
                    
                    plot_with_sd(ax, x, data, legend_label, ddof=ddof)
                
                # 범례 설정 개선
                ax.legend(loc='upper right', frameon=True, fancybox=True, shadow=True, 
                         framealpha=0.9, fontsize=10)
                
                # 제목과 축 라벨 개선
                clean_var_name = get_clean_variable_name(var)
                ax.set_title(clean_var_name, fontsize=16, fontweight='bold', pad=20)
                ax.set_xlabel("Frame/Index", fontsize=12, fontweight='bold')
                ax.set_ylabel("Value", fontsize=12, fontweight='bold')
                ax.grid(True, alpha=0.3, linestyle='--')
                
                plt.tight_layout()
                
                # 새 창에서 표시
                self._show_plot_window(fig, f"Graph: {clean_var_name}")
                
            self._update_progress(100, "그래프 생성 완료")
            self.root.after(2000, lambda: self._update_progress(0, "준비됨"))
            
        except Exception as e:
            messagebox.showerror("그래프 오류", f"그래프 생성 중 오류: {str(e)}")
            self._update_progress(0, "오류 발생")
    
    def plot_normalized_gait_graph(self):
        """개선된 정규화된 보행 그래프"""
        vars_to_plot = list(self.graph_listbox.get(0, tk.END))
        if not vars_to_plot:
            messagebox.showwarning(self.lang['graph_error'], self.lang['graph_error'])
            return
        
        if not self.dataframes:
            messagebox.showwarning(self.lang['data_error'], self.lang['data_error'])
            return
        
        self._update_progress(0, "정규화 그래프 생성 중...")
        
        try:
            for i, var in enumerate(vars_to_plot):
                progress = (i / len(vars_to_plot)) * 100
                self._update_progress(progress, f"정규화 그래프: {var}")
                
                leg_label, state_col = get_leg_and_state_col(var)
                if not leg_label or not state_col:
                    continue
                
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # 색상 팔레트 설정
                colors = plt.cm.Set1(np.linspace(0, 1, len(self.dataframes)))
                
                for color_idx, (path, df) in enumerate(zip(self.file_paths, self.dataframes)):
                    if var not in df.columns or state_col not in df.columns:
                        continue
                    
                    state_arr = df[state_col].values
                    data_arr = df[var].values
                    cycles = find_gait_cycles(state_arr)
                    
                    if len(cycles) < 2:
                        continue
                    
                    # 정규화된 주기들 생성
                    norm_cycles = []
                    for j in range(len(cycles)-1):
                        seg = resample_cycle(data_arr, cycles[j], cycles[j+1])
                        if not np.isnan(seg).all():
                            norm_cycles.append(seg)
                    
                    if norm_cycles:
                        norm_cycles = np.array(norm_cycles)
                        mean_wave = np.nanmean(norm_cycles, axis=0)
                        std_wave = np.nanstd(norm_cycles, axis=0)
                        
                        x = np.linspace(0, 100, len(mean_wave))
                        
                        # 개선된 범례 라벨
                        filename = os.path.basename(path)
                        legend_label = format_legend_label(filename)
                        
                        # 색상 지정
                        color = colors[color_idx]
                        
                        # 메인 라인 (더 굵게)
                        ax.plot(x, mean_wave, label=legend_label, linewidth=1.0, color=color)
                        
                        # 신뢰구간 (±2SD) - 범례에서 제외
                        ax.fill_between(x, mean_wave-2*std_wave, mean_wave+2*std_wave, 
                                       alpha=0.15, color=color)
                
                # 범례 설정 개선 (우측 하단으로 이동하고 크기 증가)
                ax.legend(loc='lower right', frameon=True, fancybox=True, shadow=True, 
                         framealpha=0.9, fontsize=14)
                
                # 제목과 축 라벨 개선
                clean_var_name = get_clean_variable_name(var)
                ax.set_title(clean_var_name, fontsize=16, fontweight='bold', pad=20)
                ax.set_xlabel("Gait Cycle (%)", fontsize=16, fontweight='bold')
                ax.set_ylabel("Value", fontsize=16, fontweight='bold')
                
                # 그리드 개선
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.set_xlim(0, 100)
                
                # 축 눈금 개선 (크기 증가)
                ax.tick_params(axis='both', which='major', labelsize=14)
                
                plt.tight_layout()
                
                # 새 창에서 표시
                self._show_plot_window(fig, f"Normalized Gait Graph: {clean_var_name}")
            
            self._update_progress(100, "정규화 그래프 완료")
            self.root.after(2000, lambda: self._update_progress(0, "준비됨"))
            
        except Exception as e:
            messagebox.showerror("그래프 오류", f"정규화 그래프 생성 중 오류: {str(e)}")
            self._update_progress(0, "오류 발생")
    
    def _show_plot_window(self, fig, title):
        """그래프를 새 창에서 표시"""
        top = tk.Toplevel(self.root)
        top.title(title)
        top.geometry("800x600")
        
        canvas = FigureCanvasTkAgg(fig, master=top)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 툴바 추가
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar = NavigationToolbar2Tk(canvas, top)
        toolbar.update()
        
        self.last_fig = fig
        
        # 창 닫힐 때 figure 해제
        def on_close():
            plt.close(fig)
            top.destroy()
        
        top.protocol("WM_DELETE_WINDOW", on_close)
    
    def save_results(self):
        """개선된 결과 저장"""
        selected_vars = list(self.select_listbox.get(0, tk.END))
        if not selected_vars:
            messagebox.showwarning(self.lang['save_error'], self.lang['save_error'])
            return
        
        if not self.dataframes:
            messagebox.showwarning(self.lang['data_error'], self.lang['data_error'])
            return
        
        save_path = filedialog.asksaveasfilename(
            title=self.lang['save_title'],
            defaultextension=".csv",
            filetypes=[
                (self.lang['csv_file'], "*.csv"),
                ("Excel 파일", "*.xlsx"),
                (self.lang['all_file'], "*.*")
            ]
        )
        
        if not save_path:
            return
        
        self._update_progress(0, self.lang['saving_results'])
        
        try:
            all_stats = []
            
            for path, df in zip(self.file_paths, self.dataframes):
                file_name = os.path.basename(path)
                
                for var in selected_vars:
                    analysis_key = f"{file_name}_{var}"
                    
                    if analysis_key in self.analysis_results:
                        analysis_result = self.analysis_results[analysis_key]
                        
                        # 전체 통계
                        overall_stats = analysis_result.get('overall_statistics', {})
                        quality = analysis_result.get('data_quality', {})
                        
                        basic_row = {
                            "파일명": file_name,
                            "변수명": var,
                            "분석유형": "전체 데이터",
                            "평균": overall_stats.get('mean', np.nan),
                            "표준편차": overall_stats.get('std', np.nan),
                            "최댓값": overall_stats.get('max', np.nan),
                            "최솟값": overall_stats.get('min', np.nan),
                            "중앙값": overall_stats.get('median', np.nan),
                            "데이터수": overall_stats.get('count', 0),
                            "데이터품질": quality.get('grade', 'Unknown'),
                            "완성도": quality.get('completeness', 0),
                            "품질점수": analysis_result.get('quality_score', 0)
                        }
                        all_stats.append(basic_row)
                        
                        # 보행 단계별 통계
                        gait_stats = analysis_result.get('gait_phase_statistics', {})
                        if gait_stats:
                            state_order = ['EarlyStance', 'LateStance', 'Liftoff', 'Swing', 'Landing']
                            for phase_name in state_order:
                                if phase_name in gait_stats:
                                    stats = gait_stats[phase_name]
                                    phase_row = {
                                        "파일명": file_name,
                                        "변수명": var,
                                        "분석유형": f"보행단계 - {phase_name}",
                                        "평균": stats.get('mean', np.nan),
                                        "표준편차": stats.get('std', np.nan),
                                        "최댓값": stats.get('max', np.nan),
                                        "최솟값": stats.get('min', np.nan),
                                        "중앙값": stats.get('median', np.nan),
                                        "데이터수": stats.get('count', 0),
                                        "데이터품질": "N/A",
                                        "완성도": stats.get('data_coverage', 0),
                                        "품질점수": "N/A"
                                    }
                                    all_stats.append(phase_row)
            
            # 저장
            df_results = pd.DataFrame(all_stats)
            
            if save_path.endswith('.xlsx'):
                df_results.to_excel(save_path, index=False)
            else:
                df_results.to_csv(save_path, index=False, encoding='utf-8-sig')
            
            self._update_progress(100, "저장 완료")
            messagebox.showinfo(self.lang['save_success'], 
                               f"{self.lang['save_success']}\n{save_path}")
            
            self.root.after(2000, lambda: self._update_progress(0, "준비됨"))
            
        except Exception as e:
            messagebox.showerror(self.lang['save_fail'], 
                               f"{self.lang['save_fail']}\n{str(e)}")
            self._update_progress(0, "오류 발생")
    
    def save_graphs(self):
        """그래프 저장"""
        graph_vars = list(self.graph_listbox.get(0, tk.END))
        if not graph_vars:
            messagebox.showwarning(self.lang['graph_error'], self.lang['graph_error'])
            return
        
        if not self.dataframes:
            messagebox.showwarning(self.lang['data_error'], self.lang['data_error'])
            return
        
        save_dir = filedialog.askdirectory(title='그래프 저장 폴더 선택')
        if not save_dir:
            return
        
        self._update_progress(0, "그래프 저장 중...")
        
        try:
            ddof = STATISTICS_CONFIG.get('ddof', 0)
            
            for i, var in enumerate(graph_vars):
                progress = (i / len(graph_vars)) * 100
                self._update_progress(progress, f"그래프 저장: {var}")
                
                fig, ax = plt.subplots(figsize=(10, 6))
                
                for path, df in zip(self.file_paths, self.dataframes):
                    if var not in df.columns:
                        continue
                    
                    data = df[var].values
                    x = np.arange(len(data))
                    
                    # 개선된 범례 라벨
                    filename = os.path.basename(path)
                    legend_label = format_legend_label(filename)
                    
                    plot_with_sd(ax, x, data, legend_label, ddof=ddof)
                
                # 범례 설정 개선
                ax.legend(loc='upper right', frameon=True, fancybox=True, shadow=True, 
                         framealpha=0.9, fontsize=10)
                
                # 제목과 축 라벨 개선
                clean_var_name = get_clean_variable_name(var)
                ax.set_title(clean_var_name, fontsize=16, fontweight='bold', pad=20)
                ax.set_xlabel("Frame/Index", fontsize=12, fontweight='bold')
                ax.set_ylabel("Value", fontsize=12, fontweight='bold')
                ax.grid(True, alpha=0.3, linestyle='--')
                
                plt.tight_layout()
                
                img_path = os.path.join(save_dir, f"{clean_var_name}_graph.png")
                fig.savefig(img_path, dpi=300, bbox_inches='tight')
                plt.close(fig)
            
            self._update_progress(100, "그래프 저장 완료")
            messagebox.showinfo('저장 완료', f'그래프가 저장되었습니다: {save_dir}')
            
            self.root.after(2000, lambda: self._update_progress(0, "준비됨"))
            
        except Exception as e:
            messagebox.showerror('저장 실패', f"그래프 저장 중 오류: {str(e)}")
            self._update_progress(0, "오류 발생")
    
    def save_normalized_graphs(self):
        """정규화 그래프 저장"""
        graph_vars = list(self.graph_listbox.get(0, tk.END))
        if not graph_vars:
            messagebox.showwarning(self.lang['graph_error'], self.lang['graph_error'])
            return
        
        if not self.dataframes:
            messagebox.showwarning(self.lang['data_error'], self.lang['data_error'])
            return
        
        save_dir = filedialog.askdirectory(title='정규화 그래프 저장 폴더 선택')
        if not save_dir:
            return
        
        self._update_progress(0, "정규화 그래프 저장 중...")
        
        try:
            saved_count = 0
            
            for i, var in enumerate(graph_vars):
                progress = (i / len(graph_vars)) * 100
                self._update_progress(progress, f"정규화 그래프 저장: {var}")
                
                leg_label, state_col = get_leg_and_state_col(var)
                if not leg_label or not state_col:
                    continue
                
                fig, ax = plt.subplots(figsize=(10, 6))
                has_data = False
                
                for path, df in zip(self.file_paths, self.dataframes):
                    if var not in df.columns or state_col not in df.columns:
                        continue
                    
                    state_arr = df[state_col].values
                    data_arr = df[var].values
                    cycles = find_gait_cycles(state_arr)
                    
                    if len(cycles) < 2:
                        continue
                    
                    norm_cycles = []
                    for j in range(len(cycles)-1):
                        seg = resample_cycle(data_arr, cycles[j], cycles[j+1])
                        if not np.isnan(seg).all():
                            norm_cycles.append(seg)
                    
                    if norm_cycles:
                        norm_cycles = np.array(norm_cycles)
                        mean_wave = np.nanmean(norm_cycles, axis=0)
                        std_wave = np.nanstd(norm_cycles, axis=0)
                        
                        x = np.linspace(0, 100, len(mean_wave))
                        
                        # 개선된 범례 라벨
                        filename = os.path.basename(path)
                        legend_label = format_legend_label(filename)
                        
                        ax.plot(x, mean_wave, label=legend_label, linewidth=1.0)
                        ax.fill_between(x, mean_wave-2*std_wave, mean_wave+2*std_wave, 
                                       alpha=0.15)
                        has_data = True
                
                if has_data:
                    # 범례 설정 개선 (우측 하단으로 이동하고 크기 증가)
                    ax.legend(loc='lower right', frameon=True, fancybox=True, shadow=True, 
                             framealpha=0.9, fontsize=14)
                    
                    # 제목과 축 라벨 개선
                    clean_var_name = get_clean_variable_name(var)
                    ax.set_title(clean_var_name, fontsize=16, fontweight='bold', pad=20)
                    ax.set_xlabel("Gait Cycle (%)", fontsize=16, fontweight='bold')
                    ax.set_ylabel("Value", fontsize=16, fontweight='bold')
                    
                    # 그리드 개선
                    ax.grid(True, alpha=0.3, linestyle='--')
                    ax.set_xlim(0, 100)
                    
                    # 축 눈금 개선 (크기 증가)
                    ax.tick_params(axis='both', which='major', labelsize=14)
                    
                    plt.tight_layout()
                    
                    img_path = os.path.join(save_dir, f"{clean_var_name}_normalized_graph.png")
                    fig.savefig(img_path, dpi=300, bbox_inches='tight')
                    saved_count += 1
                
                plt.close(fig)
            
            self._update_progress(100, "정규화 그래프 저장 완료")
            messagebox.showinfo('저장 완료', 
                               f'정규화 그래프 {saved_count}개가 저장되었습니다: {save_dir}')
            
            self.root.after(2000, lambda: self._update_progress(0, "준비됨"))
            
        except Exception as e:
            messagebox.showerror('저장 실패', f"정규화 그래프 저장 중 오류: {str(e)}")
            self._update_progress(0, "오류 발생")
    
    def on_close(self):
        """애플리케이션 종료"""
        try:
            # 열린 matplotlib 창들 정리
            plt.close('all')
            
            # 메인 윈도우 종료
            self.root.destroy()
            
        except Exception as e:
            print(f"종료 중 오류: {e}")
        
        finally:
            # 강제 종료
            os._exit(0)