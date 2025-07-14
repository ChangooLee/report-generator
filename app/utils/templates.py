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
        """리포트 생성을 위한 프롬프트를 구성합니다."""
        
        # 데이터 샘플 준비
        data_preview = PromptTemplates._prepare_data_preview(context_data)
        
        prompt = f"""
사용자 요청: {user_query}

제공된 데이터:
{data_preview}

다음 요구사항에 맞는 웹 리포트를 생성해주세요:

1. **Python 코드 작성**:
   - 제공된 JSON 데이터를 분석하고 처리
   - HTML 파일을 생성하여 /reports/report_{session_id}.html에 저장
   - 차트 데이터를 JavaScript 형태로 준비

2. **HTML 리포트 구조**:
   - 제목과 요약
   - 주요 인사이트 섹션
   - 인터랙티브 차트 (Chart.js 사용)
   - 결론 및 권장사항

3. **기술적 요구사항**:
   - Chart.js는 /static/js/chart.min.js 경로 사용
   - 완전한 오프라인 동작
   - 모바일 반응형 디자인
   - 접근성 고려

4. **보안 고려사항**:
   - 안전한 파일 경로만 사용
   - XSS 방지를 위한 데이터 이스케이핑

예시 출력 형식:

```python
import json
import os
from datetime import datetime

# 컨텍스트 데이터 로드
context_data = {json.dumps(context_data, indent=2, ensure_ascii=False)}

# 데이터 분석 및 처리
# ... 분석 로직 ...

# HTML 리포트 생성
html_content = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>데이터 분석 리포트</title>
    <script src="/static/js/chart.min.js"></script>
    <style>
        /* 스타일 정의 */
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .chart-container {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>데이터 분석 리포트</h1>
        <!-- 리포트 내용 -->
        <div class="chart-container">
            <canvas id="myChart"></canvas>
        </div>
        <script>
            // Chart.js 코드
        </script>
    </div>
</body>
</html>
'''

# 파일 저장
with open('/reports/report_{session_id}.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("리포트 생성 완료")
```

실제 구현을 시작해주세요.
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