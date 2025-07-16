from typing import Dict, Any, List, Optional
import json

class PromptTemplates:
    """LLM 상호작용을 위한 프롬프트 템플릿 클래스"""
    
    @staticmethod
    def build_generation_prompt(
        user_query: str, 
        context_data: Dict[str, Any], 
        session_id: str
    ) -> str:
        """삼성생명 스타일의 종합 리포트 생성을 위한 프롬프트를 구성합니다."""
        
        # 데이터 샘플 준비
        data_preview = PromptTemplates._prepare_data_preview(context_data)
        
        prompt = f"""
사용자 요청: {user_query}

제공된 데이터:
{data_preview}

삼성생명 종합 분석 리포트를 생성해주세요. 다음 요구사항을 준수해야 합니다:

## 1. Python 데이터 분석 코드 작성
- 제공된 JSON 데이터를 체계적으로 분석하고 처리
- 통계적 분석, 트렌드 분석, 패턴 인식 수행
- 핵심 지표(KPI) 계산 및 인사이트 도출
- HTML 리포트를 `/reports/report_{session_id}.html`에 저장

## 2. 삼성생명 브랜드 리포트 구조
### 필수 섹션:
- **리포트 헤더**: 삼성생명 로고와 리포트 제목
- **경영진 요약(Executive Summary)**: 핵심 발견사항 3-5줄 요약
- **주요 지표(Key Metrics)**: 시각적 메트릭 카드로 표시
- **상세 분석**: 섹션별 심층 분석 (최소 3개 섹션)
- **차트 및 시각화**: Chart.js를 활용한 인터랙티브 차트
- **인사이트 및 권장사항**: 실행 가능한 제언
- **리포트 푸터**: 생성일시 및 면책조항

## 3. 시각화 및 차트 요구사항
- Chart.js 라이브러리 사용 (/static/js/chart.min.js)
- 최소 3개 이상의 서로 다른 차트 유형 (선형, 막대, 원형, 영역 등)
- 삼성생명 브랜드 컬러 적용 (#1e3c72, #2a5298, #667eea)
- 반응형 디자인 및 인터랙티브 기능

## 4. 기술적 요구사항
- 완전한 오프라인 동작 (외부 CDN 사용 금지)
- 모바일 반응형 디자인
- 접근성 준수 (ARIA 라벨, 키보드 네비게이션)
- 프린트 최적화
- 로딩 애니메이션 및 스크롤 효과

## 5. 보안 및 품질 기준
- XSS 방지를 위한 데이터 이스케이핑
- 안전한 파일 경로만 사용
- 코드 주석 및 에러 처리 포함
- 성능 최적화 고려

## 출력 형식 예시:

```python
import json
import os
from datetime import datetime
import statistics
import math

# 컨텍스트 데이터 로드
context_data = {json.dumps(context_data, indent=2, ensure_ascii=False)}

try:
    # 데이터 전처리 및 분석
    print("📊 데이터 분석을 시작합니다...")
    
    # 여기에 실제 데이터 분석 로직 구현
    # - 기술통계 계산
    # - 트렌드 분석
    # - 이상치 탐지
    # - 패턴 인식
    
    # 핵심 지표 계산
    key_metrics = {{
        "total_records": len(context_data.get("main_data", [])),
        "growth_rate": 0.0,  # 실제 계산 로직 구현
        "performance_score": 85.2,  # 실제 계산 로직 구현
        "risk_level": "낮음"  # 실제 계산 로직 구현
    }}
    
    # 차트 데이터 준비
    chart_data = {{
        "labels": [],  # 실제 데이터에서 추출
        "datasets": []  # 실제 데이터에서 생성
    }}
    
    # HTML 리포트 생성
    html_content = f'''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>삼성생명 종합 분석 리포트</title>
    <link rel="stylesheet" href="/static/css/report.css">
    <script src="/static/js/chart.min.js"></script>
</head>
<body>
    <!-- 삼성생명 헤더 -->
    <header class="sl-header">
        <div class="sl-header-content">
            <img src="/static/images/samsung_life_logo.png" alt="삼성생명" class="sl-logo">
            <div>
                <h1 class="sl-title">종합 분석 리포트</h1>
                <p class="sl-subtitle">{{datetime.now().strftime("%Y년 %m월 %d일 생성")}}</p>
            </div>
        </div>
    </header>

    <!-- 메인 컨테이너 -->
    <div class="report-container">
        <!-- 경영진 요약 -->
        <section class="executive-summary fade-in">
            <h2 class="summary-title">경영진 요약</h2>
            <div class="summary-content">
                <p>본 리포트는 제공된 데이터를 바탕으로 한 종합적인 분석 결과를 제시합니다.</p>
                <p>주요 발견사항: [실제 분석 결과를 바탕으로 작성]</p>
                <p>권장사항: [데이터 기반 실행 가능한 제언]</p>
            </div>
        </section>

        <div class="report-body">
            <!-- 주요 지표 -->
            <section class="scroll-animate">
                <h2 class="section-title">주요 지표</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{{key_metrics["total_records"]:,}}</div>
                        <div class="metric-label">총 데이터 건수</div>
                        <div class="metric-change positive">▲ 전월 대비 증가</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{key_metrics["performance_score"]}}%</div>
                        <div class="metric-label">성과 지수</div>
                        <div class="metric-change positive">▲ {{key_metrics["growth_rate"]:.1f}}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{key_metrics["risk_level"]}}</div>
                        <div class="metric-label">위험 수준</div>
                        <div class="metric-change">안정적 유지</div>
                    </div>
                </div>
            </section>

            <!-- 차트 섹션 -->
            <section class="report-section scroll-animate">
                <h2 class="section-title">데이터 시각화</h2>
                
                <div class="chart-container">
                    <h3 class="chart-title">트렌드 분석</h3>
                    <canvas id="trendChart" width="400" height="200"></canvas>
                </div>
                
                <div class="chart-container">
                    <h3 class="chart-title">분포 현황</h3>
                    <canvas id="distributionChart" width="400" height="200"></canvas>
                </div>
            </section>

            <!-- 상세 분석 -->
            <section class="report-section scroll-animate">
                <h2 class="section-title">상세 분석</h2>
                <p>데이터 분석 결과를 바탕으로 한 심층적인 인사이트를 제공합니다.</p>
                
                <!-- 데이터 테이블 예시 -->
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>구분</th>
                                <th>수치</th>
                                <th>변화율</th>
                                <th>평가</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>지표 1</td>
                                <td>100</td>
                                <td>+5.2%</td>
                                <td>양호</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </section>

            <!-- 인사이트 박스 -->
            <div class="insight-box scroll-animate">
                <h3 class="insight-title">핵심 인사이트</h3>
                <div class="insight-content">
                    <p>분석 결과 도출된 주요 인사이트와 실행 가능한 권장사항을 제시합니다.</p>
                </div>
            </div>
        </div>
    </div>

    <!-- 푸터 -->
    <footer class="sl-footer">
        <div class="footer-content">
            <img src="/static/images/samsung_life_logo.png" alt="삼성생명" class="footer-logo">
            <div class="footer-text">
                <p>삼성생명보험주식회사 | 종합 분석 리포트</p>
                <p class="footer-contact">본 리포트는 제공된 데이터를 바탕으로 자동 생성되었습니다.</p>
            </div>
            <div>
                <p>생성일시: {{datetime.now().strftime("%Y-%m-%d %H:%M")}}</p>
            </div>
        </div>
    </footer>

    <!-- 스크립트 -->
    <script>
        // 스크롤 애니메이션
        const observerOptions = {{
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        }};

        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.classList.add('active');
                }}
            }});
        }}, observerOptions);

        document.querySelectorAll('.scroll-animate').forEach(el => {{
            observer.observe(el);
        }});

        // 차트 생성
        const createCharts = () => {{
            // 트렌드 차트
            const trendCtx = document.getElementById('trendChart').getContext('2d');
            new Chart(trendCtx, {{
                type: 'line',
                data: {{
                                         labels: {{chart_data.get("labels", ["1월", "2월", "3월", "4월", "5월"])}},
                    datasets: [{{
                        label: '데이터 트렌드',
                        data: [12, 19, 15, 25, 22],  // 실제 데이터로 교체
                        borderColor: '#1e3c72',
                        backgroundColor: 'rgba(30, 60, 114, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: true
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            }});

            // 분포 차트
            const distributionCtx = document.getElementById('distributionChart').getContext('2d');
            new Chart(distributionCtx, {{
                type: 'doughnut',
                data: {{
                    labels: ['카테고리 A', '카테고리 B', '카테고리 C'],
                    datasets: [{{
                        data: [30, 40, 30],  // 실제 데이터로 교체
                        backgroundColor: [
                            '#1e3c72',
                            '#2a5298',
                            '#667eea'
                        ],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'bottom'
                        }}
                    }}
                }}
            }});
        }};

        // 페이지 로드 후 차트 생성
        document.addEventListener('DOMContentLoaded', createCharts);
    </script>
</body>
</html>
'''
    
    # 파일 저장
    report_filename = f"report_{session_id}.html"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 삼성생명 종합 리포트가 성공적으로 생성되었습니다: {{report_filename}}")
    print("📈 주요 분석 결과:")
    print(f"   - 총 데이터 건수: {{key_metrics['total_records']:,}}")
    print(f"   - 성과 지수: {{key_metrics['performance_score']}}%")
    print(f"   - 위험 수준: {{key_metrics['risk_level']}}")

except Exception as e:
    print(f"❌ 리포트 생성 중 오류 발생: {{e}}")
    raise
```

**중요 지침:**
1. 실제 제공된 데이터를 분석하여 의미 있는 인사이트 도출
2. 삼성생명 브랜드 가이드라인 준수
3. 전문적이고 신뢰할 수 있는 보고서 형식
4. 실행 가능한 권장사항 제시
5. 시각적으로 매력적이고 정보 전달이 명확한 차트 구성

지금 바로 구현을 시작해주세요!
"""
        
        return prompt
    
    @staticmethod
    def build_error_fix_prompt(
        original_code: str, 
        error_message: str, 
        user_query: str
    ) -> str:
        """오류 수정을 위한 프롬프트를 구성합니다."""
        
        return f"""
이전 코드 실행에서 오류가 발생했습니다.

원본 사용자 요청: {user_query}

이전 생성된 코드:
{original_code}

발생한 오류:
{error_message}

오류를 수정하여 정상 동작하는 코드를 다시 작성해주세요. 
특히 다음 사항들을 확인해주세요:

1. 파일 경로가 올바른지 확인
2. 데이터 구조와 키가 실제 데이터와 일치하는지 확인
3. HTML/JavaScript 문법 오류가 없는지 확인
4. 보안 제약사항을 준수했는지 확인
5. 필요한 라이브러리 import가 빠지지 않았는지 확인

수정된 코드를 제공해주세요:
"""

    @staticmethod
    def build_enhancement_prompt(
        basic_report: str, 
        user_feedback: str
    ) -> str:
        """리포트 개선을 위한 프롬프트를 구성합니다."""
        
        return f"""
다음 기본 리포트를 사용자 피드백을 바탕으로 개선해주세요.

기본 리포트:
{basic_report}

사용자 피드백:
{user_feedback}

개선 사항:
1. 사용자 피드백을 반영한 추가 분석
2. 더 나은 시각화 방법 제안
3. 추가적인 인사이트 제공
4. 개선된 디자인 및 레이아웃
5. 더 나은 사용자 경험 제공

개선된 코드를 제공해주세요:
"""
    
    @staticmethod
    def build_mcp_integration_prompt(
        user_query: str,
        available_tools: List[Dict[str, Any]],
        context_data: Dict[str, Any]
    ) -> str:
        """MCP 도구 통합을 위한 프롬프트를 구성합니다."""
        
        tools_description = "\n".join([
            f"- {tool.get('name')}: {tool.get('description', '설명 없음')}"
            for tool in available_tools
        ])
        
        return f"""
사용자 요청: {user_query}

사용 가능한 MCP 도구들:
{tools_description}

수집된 데이터:
{json.dumps(context_data, indent=2, ensure_ascii=False)}

위 도구들을 통해 수집된 데이터를 활용하여 사용자 요청에 맞는 리포트를 생성해주세요.

특별히 고려할 점:
1. MCP 도구에서 제공된 데이터의 특성을 이해하고 활용
2. 여러 데이터 소스를 종합적으로 분석
3. 데이터의 품질과 신뢰성을 고려한 분석
4. 사용자에게 의미 있는 인사이트 제공

리포트 생성 코드를 작성해주세요:
"""
    
    @staticmethod
    def _prepare_data_preview(context_data: Dict[str, Any]) -> str:
        """컨텍스트 데이터의 미리보기를 생성합니다."""
        
        preview_lines = []
        
        # 메타데이터 정보
        if "_metadata" in context_data:
            metadata = context_data["_metadata"]
            preview_lines.append("**메타데이터:**")
            preview_lines.append(f"  - 쿼리: {metadata.get('query', 'N/A')}")
            preview_lines.append(f"  - 수집 시간: {metadata.get('collected_at', 'N/A')}")
            preview_lines.append(f"  - 데이터 소스 수: {len(metadata.get('sources', []))}")
            preview_lines.append("")
        
        # 각 데이터 소스 정보
        for source_name, data in context_data.items():
            if source_name.startswith('_'):
                continue
                
            preview_lines.append(f"**{source_name}**:")
            
            if isinstance(data, list) and data:
                preview_lines.append(f"  - 레코드 수: {len(data)}")
                
                # 첫 번째 레코드의 구조 표시
                sample = data[0]
                if isinstance(sample, dict):
                    preview_lines.append("  - 필드 구조:")
                    for key, value in list(sample.items())[:5]:
                        preview_lines.append(f"    • {key}: {type(value).__name__}")
                        
            elif isinstance(data, dict):
                preview_lines.append(f"  - 키 개수: {len(data)}")
                preview_lines.append("  - 주요 키:")
                for key in list(data.keys())[:5]:
                    preview_lines.append(f"    • {key}")
                    
            elif isinstance(data, str):
                preview_lines.append(f"  - 텍스트 길이: {len(data)} 문자")
                preview_lines.append(f"  - 미리보기: {data[:100]}...")
                
            else:
                preview_lines.append(f"  - 데이터 타입: {type(data).__name__}")
                    
            preview_lines.append("")
        
        return "\n".join(preview_lines)
    
    @staticmethod
    def build_data_analysis_prompt(
        data_sources: List[str],
        analysis_type: str = "exploratory"
    ) -> str:
        """데이터 분석을 위한 프롬프트를 구성합니다."""
        
        analysis_types = {
            "exploratory": "탐색적 데이터 분석",
            "descriptive": "기술 통계 분석",
            "comparative": "비교 분석",
            "trend": "트렌드 분석",
            "correlation": "상관관계 분석"
        }
        
        analysis_name = analysis_types.get(analysis_type, "일반 분석")
        
        return f"""
다음 데이터 소스들에 대한 {analysis_name}을 수행해주세요:

데이터 소스: {', '.join(data_sources)}

분석 요구사항:
1. 데이터 품질 검사 (결측치, 이상치 등)
2. 기본 통계 정보 산출
3. 데이터 분포 및 패턴 파악
4. 주요 인사이트 도출
5. 시각화를 통한 결과 표현

분석 결과를 포함한 리포트를 생성해주세요.
"""
    
    @staticmethod
    def build_chart_generation_prompt(
        chart_type: str,
        data_fields: List[str],
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """차트 생성을 위한 프롬프트를 구성합니다."""
        
        preferences = user_preferences or {}
        
        return f"""
{chart_type} 차트를 생성해주세요.

사용할 데이터 필드:
{', '.join(data_fields)}

사용자 선호사항:
- 색상 테마: {preferences.get('color_theme', '기본')}
- 차트 크기: {preferences.get('size', '중간')}
- 애니메이션: {preferences.get('animation', '활성화')}
- 범례 표시: {preferences.get('legend', '활성화')}

Chart.js를 사용하여 인터랙티브한 차트를 생성하고, 적절한 스타일링을 적용해주세요.
""" 