"""
Universal Data Analysis Agentic Workflow
클로드 데스크탑 스타일의 전략적 데이터 분석 및 시각화 레포트 생성 시스템
"""

import json
import logging
from typing import Dict, Any, List, Optional, TypedDict
from dataclasses import dataclass
from enum import Enum
import asyncio

from app.llm_client import OpenRouterClient, ModelType
from app.utils.security import SecurityValidator


class AnalysisPhase(Enum):
    """분석 단계 정의"""
    DATA_EXPLORATION = "data_exploration"
    INSIGHT_DISCOVERY = "insight_discovery" 
    VISUALIZATION_STRATEGY = "visualization_strategy"
    STORYTELLING = "storytelling"
    IMPLEMENTATION = "implementation"
    VALIDATION = "validation"


class ChartType(Enum):
    """지원되는 차트 타입"""
    BAR_CHART = "bar"
    LINE_CHART = "line"
    PIE_CHART = "pie"
    SCATTER_PLOT = "scatter"
    AREA_CHART = "area"
    HEATMAP = "heatmap"
    TABLE = "table"
    HISTOGRAM = "histogram"
    BOX_PLOT = "box"
    GAUGE_CHART = "gauge"
    TREEMAP = "treemap"
    RADAR_CHART = "radar"


@dataclass
class DataInsight:
    """데이터에서 발견된 인사이트"""
    type: str  # "trend", "correlation", "outlier", "pattern"
    description: str
    evidence: Dict[str, Any]
    importance: float  # 0-1 scale


@dataclass
class VisualizationRecommendation:
    """시각화 추천"""
    chart_type: ChartType
    data_fields: List[str]
    reasoning: str
    priority: int
    config: Dict[str, Any]


class WorkflowState(TypedDict):
    """워크플로우 상태 관리"""
    session_id: str
    user_query: str
    raw_data: Dict[str, Any]
    
    # Phase 1: Data Exploration
    data_structure: Dict[str, Any]
    data_types: Dict[str, str]
    data_quality: Dict[str, Any]
    
    # Phase 2: Insight Discovery
    insights: List[DataInsight]
    key_findings: List[str]
    
    # Phase 3: Visualization Strategy
    viz_recommendations: List[VisualizationRecommendation]
    selected_visualizations: List[Dict[str, Any]]
    
    # Phase 4: Storytelling
    narrative_structure: Dict[str, Any]
    report_sections: List[Dict[str, Any]]
    
    # Phase 5: Implementation
    generated_code: str
    chart_configs: List[Dict[str, Any]]
    
    # Phase 6: Validation
    validation_results: Dict[str, Any]
    final_report_path: str


class UniversalAgenticWorkflow:
    """범용 데이터 분석 및 시각화 Agentic 워크플로우"""
    
    def __init__(self, llm_client: OpenRouterClient):
        self.llm_client = llm_client
        self.security_validator = SecurityValidator()
        self.logger = logging.getLogger(__name__)
        
    async def execute_workflow(
        self, 
        user_query: str, 
        context_data: Dict[str, Any], 
        session_id: str
    ) -> Dict[str, Any]:
        """6단계 agentic 워크플로우 실행"""
        
        self.logger.info(f"🚀 Universal Agentic Workflow 시작 - Session: {session_id}")
        
        # 초기 상태 설정
        state: WorkflowState = {
            "session_id": session_id,
            "user_query": user_query,
            "raw_data": context_data,
            "data_structure": {},
            "data_types": {},
            "data_quality": {},
            "insights": [],
            "key_findings": [],
            "viz_recommendations": [],
            "selected_visualizations": [],
            "narrative_structure": {},
            "report_sections": [],
            "generated_code": "",
            "chart_configs": [],
            "validation_results": {},
            "final_report_path": ""
        }
        
        try:
            # Phase 1: 데이터 탐색
            self.logger.info("📊 Phase 1: 데이터 구조 탐색 및 분석")
            state = await self._phase_1_data_exploration(state)
            
            # Phase 2: 인사이트 발견
            self.logger.info("🔍 Phase 2: 패턴 및 인사이트 발견")
            state = await self._phase_2_insight_discovery(state)
            
            # Phase 3: 시각화 전략 수립
            self.logger.info("📈 Phase 3: 최적 시각화 전략 수립")
            state = await self._phase_3_visualization_strategy(state)
            
            # Phase 4: 스토리텔링 구조 설계
            self.logger.info("📝 Phase 4: 논리적 리포트 구조 설계")
            state = await self._phase_4_storytelling(state)
            
            # Phase 5: 코드 구현
            self.logger.info("⚙️ Phase 5: 동적 리포트 구현")
            state = await self._phase_5_implementation(state)
            
            # Phase 6: 검증 및 최적화
            self.logger.info("✅ Phase 6: 품질 검증 및 최적화")
            state = await self._phase_6_validation(state)
            
            return {
                "success": True,
                "report_path": state["final_report_path"],
                "insights_count": len(state["insights"]),
                "visualizations_count": len(state["selected_visualizations"]),
                "key_findings": state["key_findings"]
            }
            
        except Exception as e:
            self.logger.error(f"❌ Workflow 실행 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "phase": "unknown"
            }
    
    async def _phase_1_data_exploration(self, state: WorkflowState) -> WorkflowState:
        """Phase 1: 데이터 구조 탐색 및 품질 분석"""
        
        prompt = f"""
주어진 데이터를 분석하여 구조적 특성을 파악해주세요.

사용자 질문: {state['user_query']}

데이터 샘플:
{json.dumps(state['raw_data'], indent=2, ensure_ascii=False)[:2000]}...

다음 항목들을 분석해주세요:

1. **데이터 구조 분석**:
   - 데이터 계층 구조 (nested levels)
   - 메인 데이터 배열의 위치 식별
   - 메타데이터와 실제 데이터 구분

2. **데이터 타입 분석**:
   - 각 필드의 데이터 타입 (숫자, 문자, 날짜, 카테고리)
   - 측정 척도 (명목, 순서, 간격, 비율)
   - 수치형 데이터의 범위와 분포 특성

3. **데이터 품질 평가**:
   - 완성도 (결측치 비율)
   - 일관성 (데이터 형식 통일성)
   - 정확성 (이상치, 범위 검증)

**출력 형식** (JSON):
{{
    "data_structure": {{
        "main_data_path": "경로",
        "total_records": 숫자,
        "nested_levels": 숫자,
        "data_hierarchy": {{}}
    }},
    "data_types": {{
        "field_name": {{"type": "numeric/categorical/temporal", "subtype": "continuous/discrete/ordinal"}},
        ...
    }},
    "data_quality": {{
        "completeness": 0.95,
        "consistency": 0.98,
        "potential_issues": ["설명1", "설명2"]
    }}
}}
"""
        
        response = await self.llm_client.generate_code(
            prompt=prompt,
            model_type=ModelType.CLAUDE_SONNET,
            max_tokens=1500,
            temperature=0.1
        )
        
        # JSON 응답 파싱
        try:
            analysis_result = json.loads(self._extract_json(response))
            state["data_structure"] = analysis_result.get("data_structure", {})
            state["data_types"] = analysis_result.get("data_types", {})
            state["data_quality"] = analysis_result.get("data_quality", {})
        except Exception as e:
            self.logger.warning(f"Phase 1 결과 파싱 실패: {e}")
            # 기본값 설정
            state["data_structure"] = {"main_data_path": "main_data", "total_records": 0}
            state["data_types"] = {}
            state["data_quality"] = {"completeness": 0.8}
        
        return state
    
    async def _phase_2_insight_discovery(self, state: WorkflowState) -> WorkflowState:
        """Phase 2: 패턴, 트렌드, 이상치 등 인사이트 발견"""
        
        prompt = f"""
데이터에서 의미 있는 인사이트를 발견해주세요.

사용자 질문: {state['user_query']}
데이터 구조: {json.dumps(state['data_structure'], ensure_ascii=False)}
데이터 타입: {json.dumps(state['data_types'], ensure_ascii=False)}

다음 관점에서 인사이트를 분석해주세요:

1. **트렌드 분석**: 시간에 따른 변화 패턴
2. **상관관계**: 변수들 간의 관계성
3. **분포 특성**: 데이터의 집중도와 편향성
4. **이상치**: 특별한 주의가 필요한 값들
5. **세그먼트**: 의미 있는 그룹 구분
6. **비즈니스 임팩트**: 실무적 중요성

각 인사이트에 대해 **구체적인 수치**와 **비즈니스 의미**를 제시해주세요.

**출력 형식** (JSON):
{{
    "insights": [
        {{
            "type": "trend/correlation/outlier/pattern",
            "description": "구체적인 설명",
            "evidence": {{"field": "값", "metric": 숫자}},
            "importance": 0.9
        }}
    ],
    "key_findings": [
        "핵심 발견사항 1",
        "핵심 발견사항 2",
        "핵심 발견사항 3"
    ]
}}
"""
        
        response = await self.llm_client.generate_code(
            prompt=prompt,
            model_type=ModelType.CLAUDE_SONNET,
            max_tokens=2000,
            temperature=0.2
        )
        
        try:
            insight_result = json.loads(self._extract_json(response))
            
            # DataInsight 객체로 변환
            insights = []
            for insight_data in insight_result.get("insights", []):
                insight = DataInsight(
                    type=insight_data.get("type", "pattern"),
                    description=insight_data.get("description", ""),
                    evidence=insight_data.get("evidence", {}),
                    importance=insight_data.get("importance", 0.5)
                )
                insights.append(insight)
            
            state["insights"] = insights
            state["key_findings"] = insight_result.get("key_findings", [])
            
        except Exception as e:
            self.logger.warning(f"Phase 2 결과 파싱 실패: {e}")
            state["insights"] = []
            state["key_findings"] = ["데이터 분석을 위한 기본 인사이트"]
        
        return state
    
    async def _phase_3_visualization_strategy(self, state: WorkflowState) -> WorkflowState:
        """Phase 3: 데이터 특성에 맞는 최적 시각화 전략 수립"""
        
        prompt = f"""
발견된 인사이트를 효과적으로 전달할 수 있는 시각화 전략을 수립해주세요.

데이터 타입: {json.dumps(state['data_types'], ensure_ascii=False)}
주요 인사이트: {[insight.description for insight in state['insights']]}
핵심 발견사항: {state['key_findings']}

다음 원칙에 따라 시각화를 추천해주세요:

1. **데이터 타입별 최적 차트**:
   - 수치형 연속 데이터: 히스토그램, 박스플롯, 산점도
   - 범주형 데이터: 막대차트, 파이차트
   - 시계열 데이터: 선형차트, 영역차트
   - 관계형 데이터: 산점도, 히트맵
   - 지리적 데이터: 지도 시각화

2. **인사이트별 최적 표현**:
   - 트렌드 → 선형차트, 영역차트
   - 비교 → 막대차트, 레이더차트
   - 구성 → 파이차트, 트리맵
   - 분포 → 히스토그램, 박스플롯
   - 상관관계 → 산점도, 히트맵

3. **스토리텔링 고려사항**:
   - 주요 메시지가 명확히 전달되는가?
   - 데이터의 맥락이 이해하기 쉬운가?
   - 액션 아이템이 명확한가?

**출력 형식** (JSON):
{{
    "visualizations": [
        {{
            "chart_type": "bar/line/pie/scatter/area/heatmap/table/histogram/box/gauge/treemap/radar",
            "data_fields": ["field1", "field2"],
            "reasoning": "이 차트를 선택한 이유",
            "priority": 1,
            "config": {{
                "title": "차트 제목",
                "x_axis": "X축 라벨",
                "y_axis": "Y축 라벨",
                "color_scheme": "modern/corporate/vibrant",
                "interactive": true
            }}
        }}
    ]
}}
"""
        
        response = await self.llm_client.generate_code(
            prompt=prompt,
            model_type=ModelType.CLAUDE_SONNET,
            max_tokens=2000,
            temperature=0.3
        )
        
        try:
            viz_result = json.loads(self._extract_json(response))
            
            recommendations = []
            for viz_data in viz_result.get("visualizations", []):
                try:
                    chart_type = ChartType(viz_data.get("chart_type", "bar"))
                except ValueError:
                    chart_type = ChartType.BAR_CHART
                
                recommendation = VisualizationRecommendation(
                    chart_type=chart_type,
                    data_fields=viz_data.get("data_fields", []),
                    reasoning=viz_data.get("reasoning", ""),
                    priority=viz_data.get("priority", 5),
                    config=viz_data.get("config", {})
                )
                recommendations.append(recommendation)
            
            # 우선순위별 정렬
            recommendations.sort(key=lambda x: x.priority)
            state["viz_recommendations"] = recommendations
            
            # 상위 5개 시각화 선택
            state["selected_visualizations"] = [
                {
                    "chart_type": rec.chart_type.value,
                    "data_fields": rec.data_fields,
                    "config": rec.config,
                    "reasoning": rec.reasoning
                }
                for rec in recommendations[:5]
            ]
            
        except Exception as e:
            self.logger.warning(f"Phase 3 결과 파싱 실패: {e}")
            # 기본 시각화 설정
            state["selected_visualizations"] = [
                {
                    "chart_type": "bar",
                    "data_fields": [],
                    "config": {"title": "데이터 분석 결과"},
                    "reasoning": "기본 막대 차트"
                }
            ]
        
        return state
    
    async def _phase_4_storytelling(self, state: WorkflowState) -> WorkflowState:
        """Phase 4: 논리적 리포트 구조 및 스토리텔링 설계"""
        
        prompt = f"""
발견된 인사이트와 시각화를 기반으로 논리적이고 설득력 있는 리포트 구조를 설계해주세요.

사용자 질문: {state['user_query']}
핵심 발견사항: {state['key_findings']}
선택된 시각화: {[viz['chart_type'] + ': ' + viz['config'].get('title', '') for viz in state['selected_visualizations']]}

**클로드 데스크탑 스타일의 전문적 리포트 구조**를 만들어주세요:

1. **Executive Summary** (경영진 요약)
   - 핵심 메시지 3-5줄
   - 주요 지표 하이라이트
   - 액션 아이템

2. **Key Insights** (주요 인사이트)
   - 데이터에서 발견한 중요한 패턴
   - 비즈니스 임팩트
   - 수치적 근거

3. **Detailed Analysis** (상세 분석)
   - 섹션별 심층 분석
   - 각 시각화에 대한 설명
   - 방법론 및 가정사항

4. **Recommendations** (권장사항)
   - 실행 가능한 제안
   - 우선순위 정리
   - 기대 효과

**출력 형식** (JSON):
{{
    "narrative_structure": {{
        "title": "리포트 제목",
        "subtitle": "부제목",
        "key_message": "핵심 메시지 한 줄",
        "story_arc": ["도입", "문제 인식", "분석", "해결책", "결론"]
    }},
    "report_sections": [
        {{
            "section_id": "executive_summary",
            "title": "Executive Summary",
            "content_type": "text",
            "key_points": ["포인트1", "포인트2"],
            "order": 1
        }},
        {{
            "section_id": "insights",
            "title": "Key Insights",
            "content_type": "insights_grid",
            "visualizations": [시각화_인덱스],
            "order": 2
        }}
    ]
}}
"""
        
        response = await self.llm_client.generate_code(
            prompt=prompt,
            model_type=ModelType.CLAUDE_SONNET,
            max_tokens=2000,
            temperature=0.3
        )
        
        try:
            story_result = json.loads(self._extract_json(response))
            state["narrative_structure"] = story_result.get("narrative_structure", {})
            state["report_sections"] = story_result.get("report_sections", [])
            
        except Exception as e:
            self.logger.warning(f"Phase 4 결과 파싱 실패: {e}")
            # 기본 구조 설정
            state["narrative_structure"] = {
                "title": "데이터 분석 리포트",
                "key_message": "데이터 기반 인사이트 제공"
            }
            state["report_sections"] = [
                {"section_id": "summary", "title": "요약", "order": 1},
                {"section_id": "analysis", "title": "분석", "order": 2}
            ]
        
        return state
    
    async def _phase_5_implementation(self, state: WorkflowState) -> WorkflowState:
        """Phase 5: 동적 리포트 코드 생성 및 구현"""
        
        # 현대적이고 깔끔한 템플릿 생성
        template = self._generate_modern_template()
        
        prompt = f"""
다음 요구사항에 맞는 Python 코드를 생성해주세요:

리포트 구조: {json.dumps(state['narrative_structure'], ensure_ascii=False)}
섹션 정보: {json.dumps(state['report_sections'], ensure_ascii=False)}
시각화 설정: {json.dumps(state['selected_visualizations'], ensure_ascii=False)}
핵심 발견사항: {state['key_findings']}

**생성 요구사항**:

1. **데이터 처리**:
   - context_data에서 실제 데이터 추출 및 전처리
   - 각 시각화에 필요한 데이터 준비
   - 통계 계산 및 집계

2. **동적 차트 생성**:
   - Chart.js를 사용한 인터랙티브 차트
   - 각 차트 타입별 최적화된 설정
   - 현대적이고 전문적인 디자인

3. **HTML 구조**:
   - 제공된 템플릿 활용
   - 섹션별 동적 콘텐츠 생성
   - 반응형 레이아웃

**출력**: Python 코드만 생성하세요.

```python
import json
import pandas as pd
from datetime import datetime
import os

# 컨텍스트 데이터 로드
with open('/tmp/context_{state['session_id']}.json', 'r', encoding='utf-8') as f:
    context_data = json.load(f)

# 여기에 실제 구현 코드...
```
"""
        
        response = await self.llm_client.generate_code(
            prompt=prompt,
            model_type=ModelType.QWEN_CODER,
            max_tokens=3000,
            temperature=0.1
        )
        
        # Python 코드 추출
        generated_code = self._extract_python_code(response)
        
        # 템플릿과 결합
        final_code = template.format(
            session_id=state['session_id'],
            dynamic_code=self._indent_code(generated_code, 4),
            report_title=state['narrative_structure'].get('title', '데이터 분석 리포트')
        )
        
        state["generated_code"] = final_code
        
        return state
    
    async def _phase_6_validation(self, state: WorkflowState) -> WorkflowState:
        """Phase 6: 코드 검증 및 품질 보증"""
        
        # 1. 문법 검증
        syntax_valid = self._validate_python_syntax(state["generated_code"])
        
        # 2. 보안 검증
        security_result = self.security_validator.validate_code(state["generated_code"])
        
        # 3. 필수 요소 검증
        required_elements = ["context_data", "html_content", "report_filename"]
        has_required = all(elem in state["generated_code"] for elem in required_elements)
        
        validation_results = {
            "syntax_valid": syntax_valid,
            "security_safe": security_result.get("is_safe", False),
            "has_required_elements": has_required,
            "issues": []
        }
        
        # 검증 실패 시 자동 수정
        if not all([syntax_valid, security_result.get("is_safe", False), has_required]):
            self.logger.warning("코드 검증 실패 - 자동 수정 시도")
            state = await self._auto_fix_code(state, validation_results)
        
        # 최종 리포트 경로 설정
        state["final_report_path"] = f"./reports/report_{state['session_id']}.html"
        state["validation_results"] = validation_results
        
        return state
    
    def _generate_modern_template(self) -> str:
        """현대적이고 깔끔한 리포트 템플릿 생성"""
        return """
import json
import pandas as pd
from datetime import datetime
import os

print("📊 Universal Data Analysis Report 생성 중...")

try:
    # 컨텍스트 데이터 로드
    with open('/tmp/context_{session_id}.json', 'r', encoding='utf-8') as f:
        context_data = json.load(f)
    
    print(f"✅ 데이터 로드 완료: {{len(context_data)}}개 항목")
    
    # 동적 분석 로직 실행
{dynamic_code}
    
    # 현대적 HTML 리포트 생성
    html_content = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <script src="/static/js/chart.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 1.1rem;
            color: #7f8c8d;
        }}
        
        .section {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }}
        
        .section-title {{
            font-size: 1.8rem;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
            padding-left: 20px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        }}
        
        .metric-value {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 5px;
        }}
        
        .metric-label {{
            font-size: 1rem;
            opacity: 0.9;
        }}
        
        .chart-container {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .chart-title {{
            font-size: 1.4rem;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 20px;
            text-align: center;
        }}
        
        .insights-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .insight-card {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(240, 147, 251, 0.3);
        }}
        
        .insight-title {{
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9rem;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
            
            .metrics-grid,
            .insights-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{report_title}</h1>
            <p>생성일: {{datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}}</p>
        </div>
        
        {{sections_html}}
    </div>
    
    <div class="footer">
        <p>본 리포트는 AI 기반 데이터 분석 시스템에 의해 생성되었습니다.</p>
        <p>© 2024 Universal Analytics Platform. All rights reserved.</p>
    </div>
    
    <script>
        {{chart_scripts}}
        
        // 스크롤 애니메이션
        const observerOptions = {{
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        }};
        
        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }}
            }});
        }}, observerOptions);
        
        document.querySelectorAll('.section').forEach(section => {{
            section.style.opacity = '0';
            section.style.transform = 'translateY(30px)';
            section.style.transition = 'all 0.6s ease';
            observer.observe(section);
        }});
    </script>
</body>
</html>'''
    
    # 리포트 파일 저장
    report_filename = f"./reports/report_{session_id}.html"
    os.makedirs("./reports", exist_ok=True)
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Universal Analytics Report 생성 완료: {{report_filename}}")
    
except Exception as e:
    print(f"❌ 리포트 생성 실패: {{e}}")
    raise
"""
    
    async def _auto_fix_code(
        self, 
        state: WorkflowState, 
        validation_results: Dict[str, Any]
    ) -> WorkflowState:
        """검증 실패한 코드 자동 수정"""
        
        issues = validation_results.get("issues", [])
        
        fix_prompt = f"""
다음 코드에서 발견된 문제를 수정해주세요:

문제점:
{issues}

원본 코드:
{state['generated_code']}

수정 요청:
1. 문법 오류 수정
2. 보안 취약점 제거
3. 필수 요소 추가 (context_data, html_content, report_filename)
4. 안전하고 실행 가능한 코드로 변경

수정된 코드만 제공해주세요.
"""
        
        try:
            fixed_response = await self.llm_client.generate_code(
                prompt=fix_prompt,
                model_type=ModelType.CLAUDE_SONNET,
                max_tokens=3000,
                temperature=0.1
            )
            
            fixed_code = self._extract_python_code(fixed_response)
            if fixed_code:
                state["generated_code"] = fixed_code
                self.logger.info("✅ 코드 자동 수정 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 코드 자동 수정 실패: {e}")
        
        return state
    
    def _validate_python_syntax(self, code: str) -> bool:
        """Python 문법 검증"""
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError:
            return False
    
    def _extract_json(self, text: str) -> str:
        """텍스트에서 JSON 블록 추출"""
        lines = text.split('\n')
        json_lines = []
        in_json = False
        
        for line in lines:
            if line.strip().startswith('{') and not in_json:
                in_json = True
                json_lines.append(line)
            elif in_json:
                json_lines.append(line)
                if line.strip().endswith('}') and line.count('}') >= line.count('{'):
                    break
        
        return '\n'.join(json_lines)
    
    def _extract_python_code(self, text: str) -> str:
        """텍스트에서 Python 코드 블록 추출"""
        if '```python' in text:
            start = text.find('```python') + 9
            end = text.find('```', start)
            return text[start:end].strip()
        elif '```' in text:
            start = text.find('```') + 3
            end = text.find('```', start)
            return text[start:end].strip()
        else:
            return text.strip()
    
    def _indent_code(self, code: str, spaces: int = 4) -> str:
        """코드 들여쓰기"""
        indent = ' ' * spaces
        return '\n'.join(indent + line for line in code.split('\n')) 