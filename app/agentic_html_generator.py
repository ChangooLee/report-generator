"""
에이전틱 HTML 리포트 생성기
LLM이 데이터를 분석하고 적절한 컴포넌트를 선택하여 조합하는 시스템
"""

import json
from typing import Any, Dict, List
from app.html_components import HTMLComponents, ComponentSelector
import logging

logger = logging.getLogger(__name__)

class AgenticHTMLGenerator:
    """LLM이 데이터를 분석하여 동적으로 리포트를 생성하는 시스템"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.components = HTMLComponents()
        self.selector = ComponentSelector()
    
    async def generate_html(self, data: Any, user_query: str = "") -> str:
        """
        순수 LLM 기반 HTML 생성 - 템플릿 없이 완전한 HTML을 LLM이 생성
        """
        try:
            logger.info("🤖 순수 LLM 기반 HTML 생성 시작")
            
            # LLM에게 직접 HTML 생성 요청
            if self.llm_client:
                html_content = await self._generate_html_with_llm(data, user_query)
                if html_content and len(html_content) > 1000:  # 유효한 HTML인지 기본 검증
                    logger.info("✅ LLM으로 HTML 생성 완료")
                    return html_content
            
            # LLM 실패시 폴백
            logger.warning("⚠️ LLM HTML 생성 실패 - 폴백 사용")
            return self._generate_fallback_report(data)
            
        except Exception as e:
            logger.error(f"❌ HTML 생성 실패: {e}")
            return self._generate_fallback_report(data)
    
    async def _generate_html_with_llm(self, data: Any, user_query: str) -> str:
        """LLM을 사용하여 완전한 HTML 생성"""
        
        # 데이터를 JSON 문자열로 변환
        if isinstance(data, str):
            data_str = data
        else:
            data_str = json.dumps(data, ensure_ascii=False, indent=2)
        
        prompt = f"""다음 부동산 거래 데이터를 분석하여 완전한 HTML 리포트를 생성해주세요.

**데이터:**
```json
{data_str}
```

**사용자 요청:** {user_query}

**요구사항:**
1. 완전한 HTML 문서를 생성 (DOCTYPE, html, head, body 포함)
2. Chart.js를 사용한 인터랙티브 차트 포함
3. 한국어로 작성
4. 반응형 디자인
5. 데이터의 핵심 인사이트를 시각화
6. 색상과 스타일을 아름답게 적용

**차트 종류:**
- 거래량 통계 (막대 차트)
- 가격 분포 (히스토그램)
- 지역별 비교 (파이 차트)
- 시계열 트렌드 (라인 차트)

완전한 HTML 코드만 반환해주세요. 설명이나 주석은 제외하고 HTML 코드만 출력하세요."""

        try:
            # LLM 호출
            response = await self.llm_client.acomplete(prompt)
            html_content = response.strip()
            
            # HTML 태그 확인
            if '<!DOCTYPE' in html_content and '<html' in html_content:
                return html_content
            else:
                logger.warning("⚠️ LLM 응답이 완전한 HTML이 아님")
                return self._generate_fallback_report(data)
                
        except Exception as e:
            logger.error(f"❌ LLM HTML 생성 오류: {e}")
            return self._generate_fallback_report(data)
    
    def _analyze_data_comprehensively(self, data: Any) -> Dict[str, Any]:
        """데이터를 종합적으로 분석 - MCP 도구 결과 포함"""
        analysis = {
            "data_type": type(data).__name__,
            "summary": {},
            "numeric_fields": [],
            "categorical_fields": [],
            "time_fields": [],
            "recommendations": {},
            "processed_data": {},
            "source": "unknown"
        }
        
        logger.info(f"🔍 데이터 분석 시작: 타입={type(data)}, 크기={len(data) if hasattr(data, '__len__') else 'N/A'}")
        
        if isinstance(data, list) and len(data) > 0:
            # 리스트 데이터 분석 (MCP 도구 결과 또는 샘플 데이터)
            analysis.update(self._analyze_list_data(data))
            analysis["source"] = "mcp_list_data"
        elif isinstance(data, dict):
            # 딕셔너리 데이터 분석 (MCP 도구 결과)
            analysis.update(self._analyze_dict_data(data))
            analysis["source"] = "mcp_dict_data"
        else:
            # 기타 데이터 타입 (텍스트, 에러 등)
            analysis["summary"] = {"type": "fallback", "size": 1, "content": str(data)[:200]}
            analysis["source"] = "fallback_data"
        
        # 데이터 품질 검증
        if not analysis.get("processed_data"):
            logger.warning("⚠️ 처리된 데이터가 없음 - 기본 구조 생성")
            analysis["processed_data"] = {"fallback": True, "data_preview": str(data)[:300]}
        
        # 컴포넌트 권장사항 생성
        analysis["recommendations"] = self.selector.analyze_data_structure(analysis["processed_data"])
        
        logger.info(f"📊 데이터 분석 완료: 소스={analysis['source']}, 필드={len(analysis.get('numeric_fields', []))}")
        
        return analysis
    
    def _analyze_list_data(self, data: List[Dict]) -> Dict[str, Any]:
        """리스트 형태 데이터 분석 (예: JSON 배열)"""
        if not data:
            return {"summary": {"type": "empty_list", "size": 0}}
        
        # 첫 번째 항목으로 필드 분석
        sample_item = data[0]
        numeric_fields = []
        categorical_fields = []
        time_fields = []
        
        for key, value in sample_item.items():
            if isinstance(value, (int, float)):
                numeric_fields.append(key)
            elif isinstance(value, str):
                if any(word in key.lower() for word in ['date', 'time', 'month', 'year']):
                    time_fields.append(key)
                else:
                    categorical_fields.append(key)
        
        # 집계 데이터 생성
        processed_data = {}
        
        # 월별/카테고리별 집계
        if time_fields:
            time_field = time_fields[0]
            time_aggregation: Dict[str, Dict[str, Any]] = {}
            for item in data:
                period = item.get(time_field, 'Unknown')
                if period not in time_aggregation:
                    time_aggregation[period] = {}
                
                for num_field in numeric_fields:
                    if num_field not in time_aggregation[period]:
                        time_aggregation[period][num_field] = 0
                    time_aggregation[period][num_field] += item.get(num_field, 0)
            
            processed_data["time_series"] = time_aggregation
        
        # 카테고리별 집계
        if categorical_fields:
            cat_field = categorical_fields[0]
            category_aggregation: Dict[str, Dict[str, Any]] = {}
            for item in data:
                category = item.get(cat_field, 'Unknown')
                if category not in category_aggregation:
                    category_aggregation[category] = {}
                
                for num_field in numeric_fields:
                    if num_field not in category_aggregation[category]:
                        category_aggregation[category][num_field] = 0
                    category_aggregation[category][num_field] += item.get(num_field, 0)
            
            processed_data["category_breakdown"] = category_aggregation
        
        return {
            "summary": {
                "type": "structured_list",
                "size": len(data),
                "fields": len(sample_item),
                "numeric_fields_count": len(numeric_fields),
                "categorical_fields_count": len(categorical_fields)
            },
            "numeric_fields": numeric_fields,
            "categorical_fields": categorical_fields,
            "time_fields": time_fields,
            "processed_data": processed_data
        }
    
    def _analyze_dict_data(self, data: Dict) -> Dict[str, Any]:
        """딕셔너리 형태 데이터 분석 - MCP 도구 결과 특화"""
        numeric_fields = []
        categorical_fields = []
        processed_data = {}
        
        logger.info(f"🔍 딕셔너리 데이터 분석: 키={list(data.keys())}")
        
        # MCP 도구 결과인지 확인
        if "data" in data or "results" in data or "items" in data:
            # MCP 도구 결과 구조 처리
            actual_data = data.get("data") or data.get("results") or data.get("items") or data
            
            if isinstance(actual_data, list) and len(actual_data) > 0:
                logger.info(f"📋 MCP 리스트 데이터 발견: {len(actual_data)}개 항목")
                return self._analyze_list_data(actual_data)
        
        # 통계 데이터나 집계 결과 처리
        if any(key in data for key in ['total', 'count', 'sum', 'avg', 'mean', 'max', 'min']):
            logger.info("📊 통계 데이터 감지")
            for key, value in data.items():
                if isinstance(value, (int, float)) and key not in ['error', 'status']:
                    numeric_fields.append(key)
                    processed_data[key] = value
                elif isinstance(value, str) and key not in ['error', 'message']:
                    categorical_fields.append(key)
        
        # 에러 데이터 처리
        elif "error" in data or "error_data" in data:
            logger.warning("⚠️ 에러 데이터 감지")
            processed_data: Dict[str, Any] = {  # type: ignore
                "error_message": data.get("error_data") or data.get("error", "알 수 없는 오류"),
                "raw_data": str(data.get("raw_data", ""))[:300]
            }
        
        # 일반 딕셔너리 데이터
        else:
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    numeric_fields.append(key)
                    processed_data[key] = value  # type: ignore
                elif isinstance(value, str):
                    categorical_fields.append(key)
                    processed_data[key] = value  # type: ignore
                elif isinstance(value, list):
                    processed_data[f"{key}_list"] = value[:10]  # type: ignore
        
        return {
            "summary": {
                "type": "mcp_dictionary",
                "size": len(data),
                "numeric_fields_count": len(numeric_fields),
                "categorical_fields_count": len(categorical_fields),
                "is_error": "error" in data or "error_data" in data
            },
            "numeric_fields": numeric_fields,
            "categorical_fields": categorical_fields,
            "processed_data": processed_data or data
        }
    
    async def _get_llm_recommendations(self, analysis: Dict, user_query: str) -> Dict:
        """LLM에게 리포트 구조 추천 요청"""
        # 실제 구현에서는 LLM API 호출
        # 지금은 기본 구조 반환
        return self._get_default_structure(analysis)
    
    def _get_default_structure(self, analysis: Dict) -> Dict:
        """기본 리포트 구조 결정"""
        structure = {
            "title": "데이터 분석 리포트",
            "layout": "grid-2",
            "components": []
        }
        
        data_type = analysis["summary"]["type"]
        processed_data = analysis["processed_data"]
        
        if data_type == "structured_list":
            # 구조화된 리스트 데이터용 컴포넌트
            
            # 1. 주요 메트릭 카드
            metrics = []
            for field in analysis["numeric_fields"][:4]:  # 최대 4개 메트릭
                total_value = sum(item.get(field, 0) for item in processed_data.get("time_series", {}).values())
                metrics.append({
                    "label": field.replace("_", " ").title(),
                    "value": f"{total_value:,}" if isinstance(total_value, int) else f"{total_value:.2f}"
                })
            
            if metrics:
                structure["components"].append({  # type: ignore
                    "type": "metric_cards",
                    "data": metrics
                })
            
            # 2. 시간별 트렌드 차트
            if "time_series" in processed_data and analysis["numeric_fields"]:
                time_data = processed_data["time_series"]
                periods = list(time_data.keys())
                main_metric = analysis["numeric_fields"][0]
                values = [time_data[period].get(main_metric, 0) for period in periods]
                
                structure["components"].append({  # type: ignore
                    "type": "chart",
                    "chart_type": "line",
                    "title": f"📈 {main_metric.replace('_', ' ').title()} 트렌드",
                    "chart_id": "trendChart",
                    "data": {
                        "labels": periods,
                        "datasets": [{
                            "label": main_metric.replace("_", " ").title(),
                            "data": values,
                            "borderColor": "rgb(75, 192, 192)",
                            "backgroundColor": "rgba(75, 192, 192, 0.1)",
                            "tension": 0.1,
                            "fill": True
                        }]
                    }
                })
            
            # 3. 카테고리별 분포 차트
            if "category_breakdown" in processed_data and analysis["numeric_fields"]:
                cat_data = processed_data["category_breakdown"]
                categories = list(cat_data.keys())
                main_metric = analysis["numeric_fields"][0]
                values = [cat_data[cat].get(main_metric, 0) for cat in categories]
                colors = self.selector.generate_color_palette(len(categories))
                
                structure["components"].append({  # type: ignore
                    "type": "chart",
                    "chart_type": "doughnut",
                    "title": f"🍩 {main_metric.replace('_', ' ').title()} 분포",
                    "chart_id": "distributionChart",
                    "data": {
                        "labels": categories,
                        "datasets": [{
                            "label": main_metric.replace("_", " ").title(),
                            "data": values,
                            "backgroundColor": colors,
                            "borderWidth": 2
                        }]
                    }
                })
            
            # 4. 인사이트 박스
            insights = self._generate_insights(analysis)
            if insights:
                structure["components"].append({  # type: ignore
                    "type": "insights",
                    "data": insights
                })
        
        return structure
    
    def _generate_insights(self, analysis: Dict) -> List[Dict]:
        """데이터 기반 인사이트 생성"""
        insights = []
        
        data_summary = analysis["summary"]
        numeric_fields = analysis["numeric_fields"]
        processed_data = analysis["processed_data"]
        
        # 기본 데이터 인사이트
        insights.append({
            "title": "📊 데이터 개요",
            "content": f"총 {data_summary['size']}개의 데이터 포인트를 분석했습니다. {len(numeric_fields)}개의 수치형 지표와 {data_summary.get('categorical_fields_count', 0)}개의 카테고리형 지표가 포함되어 있습니다."
        })
        
        # 시계열 인사이트
        if "time_series" in processed_data:
            time_data = processed_data["time_series"]
            periods = list(time_data.keys())
            if len(periods) > 1:
                insights.append({
                    "title": "📈 트렌드 분석",
                    "content": f"{min(periods)}부터 {max(periods)}까지 {len(periods)}개 기간의 데이터를 분석했습니다. 시간별 변화 패턴을 통해 성장 추세를 확인할 수 있습니다."
                })
        
        # 카테고리 인사이트
        if "category_breakdown" in processed_data:
            cat_data = processed_data["category_breakdown"]
            insights.append({
                "title": "🎯 카테고리 분석",
                "content": f"{len(cat_data)}개의 서로 다른 카테고리가 식별되었습니다. 각 카테고리별 성과를 비교하여 최적의 전략을 수립할 수 있습니다."
            })
        
        return insights
    
    def _assemble_html(self, analysis: Dict, structure: Dict) -> str:
        """컴포넌트를 조합하여 최종 HTML 생성"""
        content_sections = []
        scripts = []
        
        # 레이아웃 컨테이너 시작
        content_sections.append(f'<div class="grid {structure["layout"]}">')
        
        # 컴포넌트별 HTML 생성
        for component in structure["components"]:
            comp_type = component["type"]
            
            if comp_type == "metric_cards":
                content_sections.append(self.components.metric_cards(component["data"]))
            
            elif comp_type == "chart":
                chart_id = component["chart_id"]
                content_sections.append(
                    self.components.chart_component(chart_id, component["title"])
                )
                scripts.append(
                    self.components.chart_script(
                        chart_id, 
                        component["chart_type"], 
                        component["data"]
                    )
                )
            
            elif comp_type == "insights":
                content_sections.append(self.components.insight_box(component["data"]))
            
            elif comp_type == "table":
                content_sections.append(
                    self.components.data_table(
                        component["headers"], 
                        component["rows"], 
                        component.get("title", "데이터 테이블")
                    )
                )
        
        # 레이아웃 컨테이너 종료
        content_sections.append('</div>')
        
        # 스크립트 조합
        script_html = f"""
    <script>
        {chr(10).join(scripts)}
    </script>"""
        
        # 최종 HTML 조합
        final_html = self.components.base_template(structure["title"]).format(
            content=chr(10).join(content_sections),
            scripts=script_html
        )
        
        return final_html
    
    def _generate_fallback_report(self, data: Any) -> str:
        """에러 발생시 폴백 리포트"""
        return self.components.base_template("기본 리포트").format(
            content="""
    <div class="card">
        <h3>📊 기본 데이터 리포트</h3>
        <div class="insight-box">
            <strong>데이터 처리 완료</strong>
            <p>제공된 데이터를 기반으로 기본 리포트가 생성되었습니다.</p>
        </div>
    </div>""",
            scripts="<script>console.log('기본 리포트 로드 완료');</script>"
        ) 