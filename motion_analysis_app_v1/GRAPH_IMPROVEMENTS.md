# 그래프 시각화 개선 사항

## 🎯 해결된 문제점

### 1. **제목 표시 문제**
- **이전**: "knee_angle_r - 정규화된 보행 주기" (한글 깨짐)
- **개선**: "knee_angle_r" (변수명만 깔끔하게 표시)

### 2. **X축 제목 개선**
- **이전**: "보행 주기 (%)" (한글 깨짐)
- **개선**: "Gait Cycle (%)" (영문으로 통일)

### 3. **범례 위치 통일**
- **이전**: 자동 배치 (위치 불일치)
- **개선**: 우측 상단 고정 (`loc='upper right'`)

### 4. **범례 라벨 개선**
- **이전**: "0.2.csv", "0.4.csv", "0.6.csv", "0.8.csv", "1.0.csv"
- **개선**: "20%", "40%", "60%", "80%", "100%"

## 🔧 구현된 기능

### 1. **파일명 → 백분율 변환 함수**
```python
def extract_percentage_from_filename(filename):
    # "0.2.csv" → "20%"
    # "0.4.csv" → "40%"
    # "0.6.csv" → "60%"
    # "0.8.csv" → "80%"
    # "1.0.csv" → "100%"
```

### 2. **그래프 스타일 통일**
```python
# 범례 설정
ax.legend(loc='upper right', frameon=True, fancybox=True, shadow=True, 
         framealpha=0.9, fontsize=10)

# 제목과 축 라벨
ax.set_title(clean_var_name, fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel("Gait Cycle (%)", fontsize=12, fontweight='bold')
ax.set_ylabel("Value", fontsize=12, fontweight='bold')
```

### 3. **시각적 개선**
- **라인 굵기**: 2.5px로 증가
- **투명도**: 신뢰구간 0.15로 조정
- **그리드**: 점선 스타일로 변경
- **색상**: Set1 팔레트 사용

## 📊 적용 범위

### ✅ 개선된 기능들
1. **정규화 그래프 보기** (`plot_normalized_gait_graph`)
2. **정규화 그래프 저장** (`save_normalized_graphs`)
3. **일반 그래프 보기** (`plot_graph`)
4. **일반 그래프 저장** (`save_graphs`)

### 🎨 시각적 개선 사항
- **제목**: 변수명만 표시 (예: "knee_angle_r")
- **X축**: 정규화 그래프는 "Gait Cycle (%)", 일반 그래프는 "Frame/Index"
- **Y축**: "Value"
- **범례**: 우측 상단 고정, 그림자 효과 추가
- **범례 라벨**: "20%", "40%", "60%", "80%", "100%" 형식

## 🔄 파일명 패턴 지원

### 지원하는 파일명 형식
```
0.2.csv     → 20%
0.4.csv     → 40%
0.6.csv     → 60%
0.8.csv     → 80%
1.0.csv     → 100%
20.csv      → 20%
normal.csv  → normal
test_20%.csv → 20%
```

### 변환 로직
1. **소수점 패턴**: 0.2 → 20%
2. **정수 패턴**: 20 → 20%
3. **백분율 패턴**: 20% → 20%
4. **기타**: 원본 파일명 유지

## 🖼️ 그래프 품질 개선

### 고해상도 저장
- **DPI**: 300 (출판 품질)
- **형식**: PNG
- **여백**: `bbox_inches='tight'`

### 폰트 및 크기
- **제목**: 16px, 굵게
- **축 라벨**: 12px, 굵게
- **범례**: 10px
- **눈금**: 10px

## 🚀 사용 방법

1. **파일 로드**: 0.2.csv, 0.4.csv, 0.6.csv, 0.8.csv, 1.0.csv
2. **변수 선택**: knee_angle_r 등
3. **그래프 생성**: "정규화" 버튼 클릭
4. **결과 확인**: 
   - 제목: "knee_angle_r"
   - X축: "Gait Cycle (%)"
   - 범례: "20%", "40%", "60%", "80%", "100%" (우측 상단)

이제 모든 그래프가 일관되고 깔끔하게 표시됩니다! 🎉