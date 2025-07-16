import asyncio
import time
import uuid
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from .llm_client import OpenRouterClient, ModelType
from .utils.security import SecurityValidator

logger = logging.getLogger(__name__)

@dataclass
class WorkflowStep:
    """워크플로우 단계 정의"""
    name: str
    description: str
    prompt_template: str
    model_type: ModelType = ModelType.CLAUDE_SONNET
    max_tokens: int = 1500
    temperature: float = 0.1

@dataclass
class WorkflowState:
    """워크플로우 상태 관리"""
    session_id: str
    user_query: str
    context_data: Dict[str, Any]
    plan: Optional[Dict[str, Any]] = None
    analysis_strategy: Optional[Dict[str, Any]] = None
    template_fragments: Optional[Dict[str, str]] = None
    final_code: Optional[str] = None
    errors: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class MultiStepWorkflow:
    """멀티스텝 리포트 생성 워크플로우"""
    
    def __init__(self, llm_client: OpenRouterClient):
        self.llm_client = llm_client
        self.security_validator = SecurityValidator()
        self.steps = self._define_workflow_steps()
        
    def _define_workflow_steps(self) -> List[WorkflowStep]:
        """워크플로우 단계들을 정의합니다."""
        return [
            WorkflowStep(
                name="plan",
                description="리포트 구조 계획 수립",
                prompt_template="""
사용자 요청을 분석하고 리포트 구조를 계획해주세요.

사용자 요청: {user_query}

다음 형식으로 계획을 작성해주세요:

```json
{{
    "report_title": "리포트 제목",
    "sections": [
        {{"name": "경영진 요약", "content_type": "text", "priority": 1}},
        {{"name": "주요 지표", "content_type": "kpi_cards", "priority": 2}},
        {{"name": "상세 분석", "content_type": "analysis", "priority": 3}},
        {{"name": "차트 및 시각화", "content_type": "charts", "priority": 4}}
    ],
    "required_charts": [
        {{"type": "line", "title": "트렌드 분석", "data_fields": ["date", "value"]}},
        {{"type": "bar", "title": "카테고리 비교", "data_fields": ["category", "amount"]}}
    ],
    "key_metrics": ["total_records", "growth_rate", "performance_score"]
}}
```

핵심 분석 포인트:
1. 사용자가 궁금해하는 핵심 질문 파악
2. 필요한 리포트 섹션 식별
3. 적절한 시각화 방법 결정
4. 핵심 지표 정의
""",
                max_tokens=1000,
                temperature=0.2
            ),
            
            WorkflowStep(
                name="analyze",
                description="데이터 분석 전략 수립",
                prompt_template="""
다음 계획을 바탕으로 데이터 분석 전략을 수립해주세요.

계획: {plan}
데이터 미리보기: {data_preview}

다음 형식으로 분석 전략을 작성해주세요:

```json
{{
    "data_preprocessing": [
        "결측치 처리 방법",
        "데이터 타입 변환",
        "이상치 제거"
    ],
    "analysis_steps": [
        {{"step": 1, "action": "기본 통계 계산", "fields": ["field1", "field2"]}},
        {{"step": 2, "action": "트렌드 분석", "method": "시계열 분석"}}
    ],
    "calculations": [
        {{"metric": "growth_rate", "formula": "(current - previous) / previous * 100"}},
        {{"metric": "performance_score", "formula": "weighted average of key indicators"}}
    ]
}}
```

분석할 데이터의 특성을 고려하여 실용적인 전략을 제시해주세요.
""",
                max_tokens=800,
                temperature=0.1
            ),
            
            WorkflowStep(
                name="generate_templates",
                description="템플릿 조각 생성",
                prompt_template="""
다음 계획과 분석 전략을 바탕으로 코드 템플릿 조각들을 생성해주세요.

계획: {plan}
분석 전략: {analysis_strategy}

다음 형식으로 템플릿 조각들을 제공해주세요:

**데이터 처리 템플릿:**
```python
# 데이터 로드 및 전처리
import json
import pandas as pd
from datetime import datetime

# context_data에서 데이터 추출
data = context_data.get('main_data', [])
df = pd.DataFrame(data)

# 기본 전처리
# [구체적인 전처리 로직]
```

**분석 로직 템플릿:**
```python
# 핵심 지표 계산
# [구체적인 계산 로직]
```

**HTML 헤더 템플릿:**
```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <link rel="stylesheet" href="/static/css/report.css">
    <script src="/static/js/chart.min.js"></script>
</head>
```

**차트 템플릿 (예시):**
```html
<div class="chart-container">
    <canvas id="chart1"></canvas>
</div>
<script>
// Chart.js 코드
</script>
```

각 템플릿은 독립적이면서도 조합 가능하도록 설계해주세요.
""",
                max_tokens=2000,
                temperature=0.15
            )
        ]
    
    async def execute_workflow(self, user_query: str, context_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """전체 워크플로우를 실행합니다."""
        start_time = time.time()
        
        # 워크플로우 상태 초기화
        state = WorkflowState(
            session_id=session_id,
            user_query=user_query,
            context_data=context_data
        )
        
        try:
            # Step 1: 리포트 계획 수립
            logger.info(f"[{session_id}] Step 1: 리포트 계획 수립")
            state.plan = await self._execute_planning_step(state)
            
            # Step 2: 데이터 분석 전략 수립
            logger.info(f"[{session_id}] Step 2: 데이터 분석 전략 수립")
            state.analysis_strategy = await self._execute_analysis_step(state)
            
            # Step 3: 템플릿 조각 생성
            logger.info(f"[{session_id}] Step 3: 템플릿 조각 생성")
            state.template_fragments = await self._execute_template_step(state)
            
            # Step 4: 최종 코드 조합
            logger.info(f"[{session_id}] Step 4: 최종 코드 조합")
            state.final_code = await self._assemble_final_code(state)
            
            # Step 5: 코드 검증
            logger.info(f"[{session_id}] Step 5: 코드 검증")
            validation_result = await self._validate_code(state.final_code)
            
            if not validation_result["valid"]:
                logger.warning(f"[{session_id}] 코드 검증 실패, 수정 시도")
                state.final_code = await self._fix_code_issues(state, validation_result["issues"])
            
            return {
                "success": True,
                "python_code": state.final_code,
                "plan": state.plan,
                "processing_time": time.time() - start_time,
                "steps_completed": 5
            }
            
        except Exception as e:
            logger.error(f"[{session_id}] 워크플로우 실행 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "state": state.__dict__
            }
    
    async def _execute_planning_step(self, state: WorkflowState) -> Dict[str, Any]:
        """리포트 계획 수립 단계를 실행합니다."""
        step = self.steps[0]  # plan step
        
        prompt = step.prompt_template.format(
            user_query=state.user_query
        )
        
        response = await self.llm_client.generate_code(
            prompt=prompt,
            model_type=step.model_type,
            max_tokens=step.max_tokens,
            temperature=step.temperature
        )
        
        # JSON 추출
        plan = self._extract_json_from_response(response)
        if not plan:
            raise ValueError("리포트 계획을 생성할 수 없습니다.")
            
        return plan
    
    async def _execute_analysis_step(self, state: WorkflowState) -> Dict[str, Any]:
        """데이터 분석 전략 수립 단계를 실행합니다."""
        step = self.steps[1]  # analyze step
        
        # 데이터 미리보기 생성 (토큰 절약을 위해 축약)
        data_preview = self._create_compact_data_preview(state.context_data)
        
                 prompt = step.prompt_template.format(
            plan=json.dumps(state.plan or {}, ensure_ascii=False, indent=2),
            data_preview=data_preview
        )
        
        response = await self.llm_client.generate_code(
            prompt=prompt,
            model_type=step.model_type,
            max_tokens=step.max_tokens,
            temperature=step.temperature
        )
        
        # JSON 추출
        strategy = self._extract_json_from_response(response)
        if not strategy:
            raise ValueError("데이터 분석 전략을 생성할 수 없습니다.")
            
        return strategy
    
    async def _execute_template_step(self, state: WorkflowState) -> Dict[str, str]:
        """템플릿 조각 생성 단계를 실행합니다."""
        step = self.steps[2]  # generate_templates step
        
        prompt = step.prompt_template.format(
            plan=json.dumps(state.plan, ensure_ascii=False, indent=2),
            analysis_strategy=json.dumps(state.analysis_strategy, ensure_ascii=False, indent=2),
            report_title=state.plan.get('report_title', '분석 리포트')
        )
        
        response = await self.llm_client.generate_code(
            prompt=prompt,
            model_type=step.model_type,
            max_tokens=step.max_tokens,
            temperature=step.temperature
        )
        
        # 템플릿 조각들 추출
        fragments = self._extract_template_fragments(response)
        return fragments
    
    async def _assemble_final_code(self, state: WorkflowState) -> str:
        """템플릿 조각들을 조합하여 최종 코드를 생성합니다."""
        
        # 삼성생명 브랜드 스타일 적용
        samsung_style = """
<style>
body {
    font-family: 'Noto Sans KR', sans-serif;
    margin: 0;
    padding: 20px;
    background: #f8f9fa;
    color: #333;
}

.header {
    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
    color: white;
    padding: 30px;
    text-align: center;
    margin-bottom: 30px;
}

.logo {
    max-height: 60px;
    margin-bottom: 20px;
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.kpi-card {
    background: white;
    padding: 25px;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    border-left: 4px solid #1e3c72;
}

.chart-container {
    background: white;
    padding: 25px;
    border-radius: 12px;
    margin-bottom: 30px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.section-title {
    color: #1e3c72;
    font-size: 1.5em;
    font-weight: bold;
    margin-bottom: 20px;
    border-bottom: 3px solid #1e3c72;
    padding-bottom: 10px;
}

@media (max-width: 768px) {
    .kpi-grid {
        grid-template-columns: 1fr;
    }
}
</style>
"""
        
        # 기본 HTML 구조 생성
        html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{state.plan.get('report_title', '분석 리포트')}</title>
    <link rel="stylesheet" href="/static/css/report.css">
    <script src="/static/js/chart.min.js"></script>
    {samsung_style}
</head>
<body>
    <div class="header">
        <img src="/static/images/samsung_life_logo.png" alt="삼성생명" class="logo">
        <h1>{state.plan.get('report_title', '분석 리포트')}</h1>
        <p>생성일: {{current_date}}</p>
    </div>
    
    <div class="container">
        {{content_sections}}
    </div>
    
    <footer style="text-align: center; margin-top: 50px; padding: 20px; color: #666;">
        <p>본 리포트는 AI 기반 분석 시스템에 의해 생성되었습니다.</p>
        <p>© 2024 Samsung Life Insurance. All rights reserved.</p>
    </footer>
    
    <script>
        {{chart_scripts}}
    </script>
</body>
</html>"""
        
        # Python 코드 조합
        python_code = f"""
import json
import pandas as pd
from datetime import datetime
import os

print("📊 삼성생명 리포트 생성을 시작합니다...")

try:
    # 컨텍스트 데이터 로드
    with open('/tmp/context_{{session_id}}.json', 'r', encoding='utf-8') as f:
        context_data = json.load(f)
    
    print(f"✅ 데이터 로드 완료: {{len(context_data)}}개 항목")
    
    # 데이터 전처리
    {state.template_fragments.get('data_processing', '# 데이터 처리 로직')}
    
    # 핵심 지표 계산
    {state.template_fragments.get('analysis_logic', '# 분석 로직')}
    
    # HTML 콘텐츠 생성
    sections_html = ""
    chart_scripts = ""
    
    # 각 섹션 생성
    for section in {json.dumps(state.plan.get('sections', []))}: 
        if section['content_type'] == 'kpi_cards':
            sections_html += '''
            <div class="section">
                <h2 class="section-title">''' + section['name'] + '''</h2>
                <div class="kpi-grid">
                    <!-- KPI 카드들이 여기에 추가됩니다 -->
                </div>
            </div>
            '''
        elif section['content_type'] == 'charts':
            sections_html += '''
            <div class="section">
                <h2 class="section-title">''' + section['name'] + '''</h2>
                <div class="chart-container">
                    <canvas id="chart1"></canvas>
                </div>
            </div>
            '''
            # 차트 스크립트 추가
            chart_scripts += '''
            const ctx1 = document.getElementById('chart1').getContext('2d');
            new Chart(ctx1, {{
                type: 'line',
                data: {{
                    labels: ['1월', '2월', '3월', '4월', '5월'],
                    datasets: [{{
                        label: '매출',
                        data: [12, 19, 3, 5, 2],
                        borderColor: '#1e3c72',
                        backgroundColor: 'rgba(30, 60, 114, 0.1)'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false
                }}
            }});
            '''
    
    # 최종 HTML 생성
    html_content = '''{html_template}'''.format(
        current_date=datetime.now().strftime('%Y년 %m월 %d일'),
        content_sections=sections_html,
        chart_scripts=chart_scripts
    )
    
    # 리포트 파일 저장
    report_filename = f"./reports/report_{{session_id}}.html"
    os.makedirs("./reports", exist_ok=True)
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 리포트 생성 완료: {{report_filename}}")
    
except Exception as e:
    print(f"❌ 리포트 생성 실패: {{e}}")
    raise
"""
        
        return python_code
    
    async def _validate_code(self, code: str) -> Dict[str, Any]:
        """생성된 코드를 검증합니다."""
        issues = []
        
        # 기본 문법 검사
        try:
            import ast
            ast.parse(code)
        except SyntaxError as e:
            issues.append(f"문법 오류: {e}")
        
        # 보안 검사
        if not self.security_validator.validate_code_execution(code):
            issues.append("보안 정책 위반")
        
        # 필수 요소 검사
        required_elements = ["context_data", "html_content", "report_filename"]
        for element in required_elements:
            if element not in code:
                issues.append(f"필수 요소 누락: {element}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    async def _fix_code_issues(self, state: WorkflowState, issues: List[str]) -> str:
        """코드 문제점을 수정합니다."""
        fix_prompt = f"""
다음 코드에 문제가 있습니다. 수정해주세요.

원본 코드:
{state.final_code}

발견된 문제점:
{', '.join(issues)}

수정된 Python 코드만 제공해주세요:
"""
        
        response = await self.llm_client.generate_code(
            prompt=fix_prompt,
            model_type=ModelType.CLAUDE_SONNET,
            max_tokens=3000,
            temperature=0.1
        )
        
        # Python 코드 블록 추출
        import re
        python_pattern = r'```python\n(.*?)\n```'
        matches = re.findall(python_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0]
        else:
            return state.final_code  # 수정 실패시 원본 반환
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """응답에서 JSON을 추출합니다."""
        import re
        
        # JSON 블록 찾기
        json_pattern = r'```json\n(.*?)\n```'
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 오류: {e}")
                return None
        
        # JSON 블록이 없으면 전체 응답에서 JSON 찾기 시도
        try:
            # 중괄호로 시작하는 JSON 찾기
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
        except:
            pass
            
        return None
    
    def _extract_template_fragments(self, response: str) -> Dict[str, str]:
        """응답에서 템플릿 조각들을 추출합니다."""
        import re
        
        fragments = {}
        
        # Python 코드 블록들 추출
        python_pattern = r'```python\n(.*?)\n```'
        python_matches = re.findall(python_pattern, response, re.DOTALL)
        
        # HTML 코드 블록들 추출
        html_pattern = r'```html\n(.*?)\n```'
        html_matches = re.findall(html_pattern, response, re.DOTALL)
        
        # 첫 번째 Python 블록을 데이터 처리로 간주
        if python_matches:
            fragments['data_processing'] = python_matches[0]
            if len(python_matches) > 1:
                fragments['analysis_logic'] = python_matches[1]
        
        # HTML 블록들 저장
        if html_matches:
            fragments['html_header'] = html_matches[0]
            if len(html_matches) > 1:
                fragments['chart_template'] = html_matches[1]
        
        return fragments
    
    def _create_compact_data_preview(self, context_data: Dict[str, Any]) -> str:
        """토큰 절약을 위한 간소화된 데이터 미리보기를 생성합니다."""
        preview = {}
        
        for key, value in context_data.items():
            if key.startswith('_'):
                continue
                
            if isinstance(value, list) and len(value) > 0:
                preview[key] = {
                    "type": "list",
                    "length": len(value),
                    "sample": value[0] if value else {},
                    "fields": list(value[0].keys()) if value and isinstance(value[0], dict) else []
                }
            elif isinstance(value, dict):
                preview[key] = {
                    "type": "dict", 
                    "keys": list(value.keys())[:5]  # 처음 5개 키만
                }
            else:
                preview[key] = {"type": type(value).__name__, "value": str(value)[:100]}
        
        return json.dumps(preview, ensure_ascii=False, indent=2) 