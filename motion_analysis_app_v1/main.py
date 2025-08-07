"""
개선된 동작 데이터 분석기 메인 실행 파일 v2.0
- 향상된 에러 처리
- 더 나은 시스템 호환성
- 개선된 폰트 설정
"""

import tkinter as tk
import matplotlib
import sys
import os
import warnings
from pathlib import Path

# 경로 설정 - 더 안전한 방법
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from src.motion_analysis_app import MotionAnalysisApp
    from config.constants import GUI_CONFIG
    from config.language import get_language
except ImportError as e:
    print(f"모듈 import 오류: {e}")
    print("현재 디렉토리:", current_dir)
    print("파이썬 경로:", sys.path)
    sys.exit(1)


def setup_matplotlib():
    """matplotlib 설정"""
    try:
        # 백엔드 설정
        matplotlib.use('TkAgg')
        
        # 한글 폰트 설정 시도
        font_candidates = [
            'Malgun Gothic',  # Windows
            'AppleGothic',    # macOS
            'Noto Sans CJK KR',  # Linux
            'DejaVu Sans',    # 기본 대체
            'sans-serif'      # 최종 대체
        ]
        
        for font in font_candidates:
            try:
                matplotlib.rc('font', family=font)
                print(f"폰트 설정 성공: {font}")
                break
            except Exception:
                continue
        else:
            print("한글 폰트 설정 실패. 기본 폰트 사용.")
        
        # 기본 설정
        matplotlib.rc('axes', unicode_minus=False)
        matplotlib.rc('figure', max_open_warning=0)
        
        # 경고 억제
        warnings.filterwarnings("ignore", category=matplotlib.MatplotlibDeprecationWarning)
        
    except Exception as e:
        print(f"matplotlib 설정 오류: {e}")


def check_dependencies():
    """필수 의존성 확인"""
    required_modules = [
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('matplotlib', 'matplotlib'),
        ('tkinter', 'tkinter')
    ]
    
    missing_modules = []
    
    for module_name, import_name in required_modules:
        try:
            __import__(import_name)
        except ImportError:
            missing_modules.append(module_name)
    
    if missing_modules:
        print("다음 모듈들이 설치되지 않았습니다:")
        for module in missing_modules:
            print(f"  - {module}")
        print("\n다음 명령어로 설치하세요:")
        print(f"pip install {' '.join(missing_modules)}")
        return False
    
    return True


def main():
    """메인 함수"""
    print("동작 데이터 분석기 v2.0 시작")
    
    # 의존성 확인
    if not check_dependencies():
        input("Enter 키를 눌러 종료하세요...")
        return
    
    # matplotlib 설정
    setup_matplotlib()
    
    try:
        # Tkinter 루트 윈도우 생성
        root = tk.Tk()
        
        # 윈도우 설정
        gui_config = GUI_CONFIG
        window_size = gui_config.get('window_size', (1200, 800))
        root.geometry(f"{window_size[0]}x{window_size[1]}")
        
        # 언어 설정
        lang = get_language('ko')
        
        # 애플리케이션 생성 및 시작
        try:
            app = MotionAnalysisApp(root, lang=lang)
            print("애플리케이션 초기화 완료")
            
            # 메인 루프 시작
            root.mainloop()
            
        except Exception as e:
            print(f"애플리케이션 초기화 오류: {e}")
            tk.messagebox.showerror("초기화 오류", f"애플리케이션을 시작할 수 없습니다:\n{e}")
            
    except tk.TclError as e:
        print(f"Tkinter 오류: {e}")
        print("GUI 환경을 사용할 수 없습니다.")
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("애플리케이션 종료")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")
    except Exception as e:
        print(f"치명적 오류: {e}")
        import traceback
        traceback.print_exc()
        input("Enter 키를 눌러 종료하세요...")
        sys.exit(1)