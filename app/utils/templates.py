"""범용 AI 리포트 생성을 위한 프롬프트 템플릿을 제공합니다."""
        
import json
from datetime import datetime
from typing import Dict, Any, List

class PromptTemplates:
    """범용 AI 리포트 생성 프롬프트 템플릿"""
    
    @staticmethod
    def build_generation_prompt(user_query: str, context_data: str, session_id: str) -> str:
        """AI 분석 리포트 생성을 위한 프롬프트를 구성합니다."""
        
        current_time = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
        
        return f"""
AI 기반 종합 분석 리포트를 생성해주세요. 다음 요구사항을 준수해야 합니다:

## 1. 리포트 요청사항
**사용자 요청**: {user_query}
**세션 ID**: {session_id}
**생성 시간**: {current_time}

## 2. 표준 리포트 구조

### 리포트 구성 요소:
- **리포트 헤더**: 제목과 생성일시
- **요약 섹션**: 핵심 발견사항 3-5줄 요약
- **주요 지표 카드**: 핵심 메트릭 시각적 표현
- **상세 분석 섹션**: 최소 3개 섹션으로 구성된 심층 분석
- **데이터 시각화**: Chart.js 기반 인터랙티브 차트
- **인사이트 박스**: 주요 발견사항과 권장사항
- **푸터**: 생성 정보

## 3. 시각화 요구사항

### Chart.js 차트 유형 활용:
- **막대 차트**: 카테고리별 비교
- **선형 차트**: 시계열 트렌드
- **원형/도넛 차트**: 구성비 분석
- **영역 차트**: 누적 데이터
- **콤보 차트**: 복합 지표

### 컬러 팔레트:
- 주요: #3b82f6 (블루)
- 보조: #6366f1 (인디고)
- 성공: #10b981 (그린)
- 경고: #f59e0b (앰버)

## 4. 데이터 분석 컨텍스트
```json
{context_data}
```

## 5. 출력 요구사항

HTML 형태로 완전한 리포트를 생성해주세요:
- 반응형 디자인 (모바일/태블릿/데스크톱)
- 오프라인 Chart.js 라이브러리 활용 (/static/js/chart.min.js)
- 오프라인 폰트 사용 (/static/fonts/)
- 깔끔하고 전문적인 디자인
- 인터랙티브 차트와 시각화
- 데이터 기반 분석과 인사이트

바로 HTML 코드로 응답해주세요. 설명이나 추가 텍스트 없이 온전한 HTML 문서만 제공해주세요.
"""
    
    @staticmethod
    def build_context_summary(data: Dict[str, Any]) -> str:
        """데이터 컨텍스트를 요약합니다."""
        
        if not data:
            return "분석할 데이터가 제공되지 않았습니다."
            
        summary_parts = []
        
        # 데이터 항목 수
        if isinstance(data, dict):
            total_items = sum(len(v) if isinstance(v, list) else 1 for v in data.values())
            summary_parts.append(f"총 {total_items}개 데이터 항목")
            
        # 주요 키 정보
        if isinstance(data, dict):
            main_keys = list(data.keys())[:5]  # 상위 5개만
            summary_parts.append(f"주요 데이터 유형: {', '.join(main_keys)}")
        
        return " | ".join(summary_parts) if summary_parts else "데이터 구조 분석 중"
    
    @staticmethod
    def build_analysis_prompt(query: str, data: Any) -> str:
        """데이터 분석을 위한 프롬프트를 생성합니다."""
        
        return f"""
다음 데이터를 기반으로 '{query}' 요청에 맞는 종합 분석을 수행해주세요:

데이터:
{json.dumps(data, ensure_ascii=False, indent=2) if isinstance(data, (dict, list)) else str(data)}

분석 결과를 다음과 같이 제공해주세요:
1. 데이터 개요 및 특성
2. 주요 패턴 및 트렌드
3. 통계적 요약
4. 핵심 인사이트
5. 권장사항

분석은 구체적이고 데이터에 기반해야 하며, 시각화에 적합한 형태로 구조화해주세요.
"""
    
    @staticmethod
    def get_chart_config_template() -> str:
        """Chart.js 설정 템플릿을 반환합니다."""
        
        return """
// Chart.js 글로벌 설정
Chart.defaults.font.family = "Roboto, 'Noto Sans KR', sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.responsive = true;
Chart.defaults.maintainAspectRatio = false;

// 컬러 팔레트
const colors = {
    primary: '#3b82f6',
    secondary: '#6366f1', 
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    info: '#06b6d4',
    light: '#f8fafc',
    dark: '#1e293b'
};

// 그라데이션 생성 헬퍼
function createGradient(ctx, colorStart, colorEnd) {
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, colorStart);
    gradient.addColorStop(1, colorEnd);
    return gradient;
}
""" 