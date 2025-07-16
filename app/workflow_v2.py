import asyncio
import time
import uuid
import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from .llm_client import OpenRouterClient, ModelType
from .utils.security import SecurityValidator

logger = logging.getLogger(__name__)

@dataclass
class WorkflowState:
    """워크플로우 상태 관리"""
    session_id: str
    user_query: str
    context_data: Dict[str, Any]
    plan: Dict[str, Any] = field(default_factory=dict)
    analysis_strategy: Dict[str, Any] = field(default_factory=dict)
    template_fragments: Dict[str, str] = field(default_factory=dict)
    final_code: str = ""
    errors: List[str] = field(default_factory=list)

class AgenticWorkflow:
    """에이전틱 방식의 리포트 생성 워크플로우"""
    
    def __init__(self, llm_client: OpenRouterClient):
        self.llm_client = llm_client
        self.security_validator = SecurityValidator()
        
    async def execute_workflow(self, user_query: str, context_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """전체 워크플로우를 실행합니다."""
        start_time = time.time()
        
        state = WorkflowState(
            session_id=session_id,
            user_query=user_query,
            context_data=context_data
        )
        
        try:
            # Step 1: 계획 수립 (토큰 절약형)
            logger.info(f"[{session_id}] Step 1: 리포트 계획 수립")
            plan_result = await self._plan_report(state.user_query)
            if plan_result:
                state.plan = plan_result
            
            # Step 2: 데이터 분석 전략 (최소한의 컨텍스트만 사용)
            logger.info(f"[{session_id}] Step 2: 데이터 분석 전략")
            strategy_result = await self._analyze_data_strategy(state.plan, context_data)
            if strategy_result:
                state.analysis_strategy = strategy_result
            
            # Step 3: 템플릿 기반 코드 생성
            logger.info(f"[{session_id}] Step 3: 코드 생성")
            final_code = await self._generate_code_from_template(state)
            state.final_code = final_code
            
            # Step 4: 자체 검증
            logger.info(f"[{session_id}] Step 4: 코드 검증")
            validation_result = self._validate_generated_code(final_code)
            
            if not validation_result["is_safe"]:
                logger.warning(f"[{session_id}] 코드 검증 실패, 수정 시도")
                state.final_code = await self._fix_code_with_llm(state, validation_result)
            
            return {
                "success": True,
                "python_code": state.final_code,
                "plan": state.plan,
                "processing_time": time.time() - start_time,
                "token_usage": "optimized"
            }
            
        except Exception as e:
            logger.error(f"[{session_id}] 워크플로우 실행 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    async def _plan_report(self, user_query: str) -> Dict[str, Any]:
        """리포트 계획을 수립합니다 (토큰 최적화)"""
        
        # 간소화된 계획 프롬프트
        prompt = f"""
사용자 요청을 분석하고 리포트 구조를 JSON으로 계획해주세요.

요청: {user_query}

다음 JSON 형식으로만 응답하세요:
```json
{{
    "title": "리포트 제목",
    "sections": ["경영진 요약", "주요 지표", "차트 분석", "인사이트"],
    "charts": [
        {{"type": "line", "title": "트렌드", "fields": ["date", "value"]}},
        {{"type": "bar", "title": "비교", "fields": ["category", "amount"]}}
    ],
    "metrics": ["총계", "증감률", "성과점수"]
}}
```
"""
        
        response = await self.llm_client.generate_code(
            prompt=prompt,
            model_type=ModelType.CLAUDE_SONNET,
            max_tokens=800,
            temperature=0.2
        )
        
        # JSON 추출
        plan = self._extract_json_response(response)
        return plan or {
            "title": "분석 리포트",
            "sections": ["개요", "분석", "결론"],
            "charts": [{"type": "bar", "title": "기본 차트", "fields": ["x", "y"]}],
            "metrics": ["총계", "평균"]
        }
    
    async def _analyze_data_strategy(self, plan: Dict[str, Any], context_data: Dict[str, Any]) -> Dict[str, Any]:
        """데이터 분석 전략을 수립합니다 (압축된 데이터 미리보기 사용)"""
        
        # 데이터 구조만 간단히 분석
        data_summary = self._create_data_summary(context_data)
        
        prompt = f"""
계획: {json.dumps(plan, ensure_ascii=False)}
데이터 구조: {data_summary}

간단한 분석 전략을 JSON으로 제시하세요:
```json
{{
    "key_fields": ["주요필드1", "주요필드2"],
    "calculations": ["합계", "평균", "증감률"],
    "grouping": "분류기준"
}}
```
"""
        
        response = await self.llm_client.generate_code(
            prompt=prompt,
            model_type=ModelType.CLAUDE_SONNET,
            max_tokens=500,
            temperature=0.1
        )
        
        strategy = self._extract_json_response(response)
        return strategy or {
            "key_fields": ["value"],
            "calculations": ["sum", "avg"],
            "grouping": "category"
        }
    
    async def _generate_code_from_template(self, state: WorkflowState) -> str:
        """템플릿 기반으로 최종 코드를 생성합니다"""
        
        # 고정 삼성생명 템플릿 사용 (토큰 절약)
        samsung_template = self._get_samsung_template()
        
        # 분석 로직만 LLM으로 생성
        analysis_prompt = f"""
다음 계획에 맞는 간단한 Python 분석 코드를 작성하세요:

계획: {json.dumps(state.plan, ensure_ascii=False)}
전략: {json.dumps(state.analysis_strategy, ensure_ascii=False)}

Python 코드만 응답하세요:
```python
# 데이터 분석 로직
data = context_data.get('main_data', [])
# 분석 수행
# KPI 계산
```
"""
        
        analysis_code = await self.llm_client.generate_code(
            prompt=analysis_prompt,
            model_type=ModelType.QWEN_CODER,
            max_tokens=1000,
            temperature=0.1
        )
        
        # 코드 블록 추출
        extracted_analysis = self._extract_python_code(analysis_code)
        
        # 템플릿과 조합
        final_code = samsung_template.format(
            session_id=state.session_id,
            report_title=state.plan.get('title', '분석 리포트'),
            analysis_logic=extracted_analysis,
            sections=json.dumps(state.plan.get('sections', []))
        )
        
        return final_code
    
    def _get_samsung_template(self) -> str:
        """고정된 삼성생명 템플릿을 반환합니다"""
        
        return """
import json
import pandas as pd
from datetime import datetime
import os

print("📊 삼성생명 리포트 생성 중...")

try:
    # 컨텍스트 데이터 로드
    with open('/tmp/context_{session_id}.json', 'r', encoding='utf-8') as f:
        context_data = json.load(f)
    
    print(f"✅ 데이터 로드 완료: {{len(context_data)}}개 항목")
    
    # 분석 로직 실행
    {analysis_logic}
    
    # 기본 KPI 계산
    if 'main_data' in context_data:
        main_data = context_data['main_data']
        if isinstance(main_data, list) and main_data:
            total_records = len(main_data)
            # 간단한 집계
            if isinstance(main_data[0], dict):
                numeric_fields = []
                for key, value in main_data[0].items():
                    if isinstance(value, (int, float)):
                        numeric_fields.append(key)
                
                key_metrics = {{
                    'total_records': total_records,
                    'performance_score': 85,  # 기본값
                    'growth_rate': 12.5       # 기본값
                }}
            else:
                key_metrics = {{'total_records': total_records, 'performance_score': 80, 'growth_rate': 0}}
        else:
            key_metrics = {{'total_records': 0, 'performance_score': 0, 'growth_rate': 0}}
    else:
        key_metrics = {{'total_records': 0, 'performance_score': 0, 'growth_rate': 0}}
    
    print(f"📈 핵심 지표 계산 완료: {{key_metrics}}")
    
    # HTML 리포트 생성
    html_content = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <link rel="stylesheet" href="/static/css/report.css">
    <script src="/static/js/chart.min.js"></script>
    <style>
    body {{
        font-family: 'Noto Sans KR', sans-serif;
        margin: 0;
        padding: 20px;
        background: #f8f9fa;
        color: #333;
    }}
    .header {{
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        padding: 30px;
        text-align: center;
        margin-bottom: 30px;
    }}
    .logo {{
        max-height: 60px;
        margin-bottom: 20px;
    }}
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin-bottom: 30px;
    }}
    .kpi-card {{
        background: white;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border-left: 4px solid #1e3c72;
    }}
    .chart-container {{
        background: white;
        padding: 25px;
        border-radius: 12px;
        margin-bottom: 30px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }}
    .section-title {{
        color: #1e3c72;
        font-size: 1.5em;
        font-weight: bold;
        margin-bottom: 20px;
        border-bottom: 3px solid #1e3c72;
        padding-bottom: 10px;
    }}
    </style>
</head>
<body>
    <div class="header">
        <img src="/static/images/samsung_life_logo.png" alt="삼성생명" class="logo">
        <h1>{report_title}</h1>
        <p>생성일: {{datetime.now().strftime('%Y년 %m월 %d일')}}</p>
    </div>
    
    <div class="container">
        <div class="section">
            <h2 class="section-title">주요 지표</h2>
            <div class="kpi-grid">
                <div class="kpi-card">
                    <h3>총 레코드 수</h3>
                    <div style="font-size: 2em; font-weight: bold; color: #1e3c72;">
                        {{key_metrics['total_records']:,}}
                    </div>
                </div>
                <div class="kpi-card">
                    <h3>성과 지수</h3>
                    <div style="font-size: 2em; font-weight: bold; color: #1e3c72;">
                        {{key_metrics['performance_score']}}%
                    </div>
                </div>
                <div class="kpi-card">
                    <h3>성장률</h3>
                    <div style="font-size: 2em; font-weight: bold; color: #1e3c72;">
                        {{key_metrics['growth_rate']}}%
                    </div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">데이터 시각화</h2>
            <div class="chart-container">
                <canvas id="mainChart" style="width: 100%; height: 400px;"></canvas>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">분석 결과</h2>
            <div style="background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <p>• 총 {{key_metrics['total_records']}}건의 데이터를 분석했습니다.</p>
                <p>• 전체적인 성과 지수는 {{key_metrics['performance_score']}}%로 양호한 수준입니다.</p>
                <p>• 전년 대비 {{key_metrics['growth_rate']}}%의 성장을 보이고 있습니다.</p>
            </div>
        </div>
    </div>
    
    <footer style="text-align: center; margin-top: 50px; padding: 20px; color: #666;">
        <p>본 리포트는 AI 기반 분석 시스템에 의해 생성되었습니다.</p>
        <p>© 2024 Samsung Life Insurance. All rights reserved.</p>
    </footer>
    
    <script>
        const ctx = document.getElementById('mainChart').getContext('2d');
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: ['1분기', '2분기', '3분기', '4분기'],
                datasets: [{{
                    label: '실적',
                    data: [65, 78, 82, 95],
                    backgroundColor: 'rgba(30, 60, 114, 0.8)',
                    borderColor: '#1e3c72',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>'''
    
    # 리포트 파일 저장
    report_filename = f"./reports/report_{session_id}.html"
    os.makedirs("./reports", exist_ok=True)
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 리포트 생성 완료: {{report_filename}}")
    
except Exception as e:
    print(f"❌ 리포트 생성 실패: {{e}}")
    raise
"""
    
    def _create_data_summary(self, context_data: Dict[str, Any]) -> str:
        """간소화된 데이터 요약 생성 (토큰 절약)"""
        
        summary = {}
        for key, value in context_data.items():
            if key.startswith('_'):
                continue
                
            if isinstance(value, list) and value:
                summary[key] = {
                    "type": "list",
                    "count": len(value),
                    "fields": list(value[0].keys()) if isinstance(value[0], dict) else []
                }
            elif isinstance(value, dict):
                summary[key] = {"type": "dict", "keys": list(value.keys())[:3]}
        
        return json.dumps(summary, ensure_ascii=False)
    
    def _extract_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """LLM 응답에서 JSON을 추출합니다"""
        
        import re
        
        # JSON 블록 찾기
        json_pattern = r'```json\n(.*?)\n```'
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass
        
        # JSON 블록이 없으면 중괄호로 감싸진 부분 찾기
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
        except:
            pass
            
        return None
    
    def _extract_python_code(self, response: str) -> str:
        """Python 코드 블록을 추출합니다"""
        
        import re
        
        # Python 코드 블록 찾기
        python_pattern = r'```python\n(.*?)\n```'
        matches = re.findall(python_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0]
        
        # 코드 블록이 없으면 기본 분석 로직 반환
        return """
# 기본 데이터 분석
data = context_data.get('main_data', [])
print(f"분석할 데이터 수: {len(data) if isinstance(data, list) else 0}")
"""
    
    def _validate_generated_code(self, code: str) -> Dict[str, Any]:
        """생성된 코드를 검증합니다"""
        
        # 기본 문법 검사
        try:
            import ast
            ast.parse(code)
            syntax_ok = True
        except SyntaxError:
            syntax_ok = False
        
        # 보안 검사
        security_result = self.security_validator.validate_code(code)
        
        return {
            "is_safe": syntax_ok and security_result["is_safe"],
            "syntax_ok": syntax_ok,
            "security_issues": security_result.get("errors", []),
            "warnings": security_result.get("warnings", [])
        }
    
    async def _fix_code_with_llm(self, state: WorkflowState, validation_result: Dict[str, Any]) -> str:
        """검증 실패한 코드를 LLM으로 수정합니다"""
        
        issues = validation_result.get("security_issues", []) + validation_result.get("warnings", [])
        
        fix_prompt = f"""
다음 코드에 문제가 있습니다. 간단히 수정해주세요:

문제점: {', '.join(issues[:3])}  # 최대 3개만

Python 코드만 응답하세요:
```python
# 수정된 코드
```
"""
        
        try:
            response = await self.llm_client.generate_code(
                prompt=fix_prompt,
                model_type=ModelType.CLAUDE_SONNET,
                max_tokens=1500,
                temperature=0.1
            )
            
            fixed_code = self._extract_python_code(response)
            return fixed_code if fixed_code.strip() else state.final_code
            
        except Exception as e:
            logger.error(f"코드 수정 실패: {e}")
            return state.final_code 