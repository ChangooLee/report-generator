"""에이전틱 HTML 리포트 생성기"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class AgenticHTMLGenerator:
    """AI 기반 동적 HTML 리포트 생성기"""
    
    def __init__(self):
        self.logger = logger
        
    def generate_html_report(self, data: Dict[str, Any], user_query: str = "데이터 분석 리포트") -> str:
        """메인 HTML 리포트 생성 함수"""
        
        try:
            self.logger.info("🤖 에이전틱 HTML 생성 시작")
            
            # 1. 데이터 구조 분석
            data_analysis = self._analyze_data_structure(data)
            self.logger.info(f"📊 데이터 분석 완료: {len(data_analysis)} 키")
            
            # 2. 적절한 차트 유형 결정
            chart_suggestions = self._suggest_chart_types(data)
            
            # 3. 도메인 감지
            domain = self._detect_domain(data, user_query)
            
            # 4. 제목 추론
            title = self._infer_title(data, user_query, domain)
            
            # 5. HTML 생성
            html_content = self._generate_complete_html(
                data=data,
                title=title,
                domain=domain,
                chart_suggestions=chart_suggestions,
                user_query=user_query
            )
            
            self.logger.info("✅ 에이전틱 HTML 생성 완료")
            return html_content
            
        except Exception as e:
            self.logger.error(f"❌ HTML 생성 실패: {e}")
            return self._generate_emergency_html(user_query, str(e))
    
    def _analyze_data_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """데이터 구조 분석"""
        
        analysis = {
            "total_keys": 0,
            "has_time_series": False,
            "has_categorical": False,
            "has_numerical": False,
            "special_keys": [],
            "recommended_charts": []
        }
        
        if not isinstance(data, dict):
            return analysis
            
        analysis["total_keys"] = len(data)
        
        # 키 분석
        for key, value in data.items():
            key_lower = key.lower()
            
            # 시계열 데이터 감지
            if any(time_word in key_lower for time_word in ['date', 'time', 'month', 'year', '월', '년']):
                analysis["has_time_series"] = True
                
            # 카테고리 데이터 감지  
            if isinstance(value, (list, dict)) and len(str(value)) > 50:
                analysis["has_categorical"] = True
                
            # 숫자 데이터 감지
            if any(num_word in key_lower for num_word in ['count', 'total', 'amount', 'value', 'price', '수', '금액', '값']):
                analysis["has_numerical"] = True
                
            # 특별 키 수집
            if any(special in key_lower for special in ['statistics', 'trend', 'analysis', '통계', '분석', '트렌드']):
                analysis["special_keys"].append(key)
        
        return analysis
    
    def _detect_domain(self, data: Dict[str, Any], user_query: str) -> str:
        """데이터 도메인 감지 (일반적인 분류)"""
        
        # 키워드 기반 도메인 매핑 (범용화)
        domain_keywords = {
            "데이터분석": ["analysis", "statistics", "data", "metric", "분석", "통계", "지표"],
            "시계열": ["time", "date", "trend", "monthly", "yearly", "시간", "월별", "연도별"],
            "비교분석": ["comparison", "vs", "difference", "compare", "비교", "대비"],
            "분포분석": ["distribution", "range", "category", "segment", "분포", "범위", "구간"],
            "성과분석": ["performance", "result", "achievement", "성과", "결과", "실적"]
        }
        
        # 데이터 키와 사용자 쿼리에서 도메인 추출
        all_text = " ".join([str(data.keys()), user_query]).lower()
        
        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in all_text)
            domain_scores[domain] = score
            
        # 가장 높은 점수의 도메인 반환
        if domain_scores:
            detected_domain = max(domain_scores.items(), key=lambda x: x[1])[0]
            return detected_domain if domain_scores[detected_domain] > 0 else "데이터분석"
            
        return "데이터분석"
    
    def _infer_title(self, data: Dict[str, Any], user_query: str, domain: str) -> str:
        """제목 추론"""
        
        # 사용자 쿼리에서 제목 힌트 추출
        if "리포트" in user_query or "분석" in user_query:
            if len(user_query) < 50:  # 간단한 쿼리면 그대로 사용
                return user_query
                
        # 도메인 기반 제목 생성
        domain_titles = {
            "데이터분석": "종합 데이터 분석 리포트",
            "시계열": "시계열 데이터 분석 리포트", 
            "비교분석": "비교 분석 리포트",
            "분포분석": "분포 분석 리포트",
            "성과분석": "성과 분석 리포트"
        }
        
        return domain_titles.get(domain, "데이터 분석 리포트")
    
    def _suggest_chart_types(self, data: Dict[str, Any]) -> List[str]:
        """데이터에 기반한 차트 유형 제안"""
        
        suggestions = []
        
        if not isinstance(data, dict):
            return ["bar"]  # 기본값
            
        # 데이터 특성 분석
        has_time_data = any(time_word in str(data).lower() for time_word in ['date', 'time', 'month', '월'])
        has_categories = len(data) > 1
        has_numerical = any(isinstance(v, (int, float)) for v in str(data) if str(v).replace('.', '').isdigit())
        
        # 차트 제안
        if has_time_data:
            suggestions.extend(["line", "area"])
        if has_categories:
            suggestions.extend(["bar", "doughnut"])
        if has_numerical:
            suggestions.extend(["bar", "pie"])
            
        # 기본 차트 유형
        if not suggestions:
            suggestions = ["bar", "line", "doughnut"]
            
        return list(set(suggestions))  # 중복 제거
    
    def _generate_complete_html(self, data: Dict, title: str, domain: str, 
                               chart_suggestions: List[str], user_query: str) -> str:
        """완전한 HTML 리포트 생성"""
        
        # 현재 시간
        current_time = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
        
        # 통계 카드 생성
        stats_cards = self._create_stats_cards(data)
        
        # 차트 생성
        charts_html = self._create_dynamic_charts(data, chart_suggestions)
        
        # 인사이트 생성
        insights = self._generate_insights(data, domain)
        
        html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="/static/js/chart.min.js"></script>
    <style>
        body {{
            font-family: 'Roboto', 'Noto Sans KR', sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            color: #2d3748;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.2em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px;
        }}
        .summary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .chart-container {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .chart-title {{
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 20px;
            color: #2d3748;
        }}
        .chart {{
            height: 400px;
            position: relative;
        }}
        .insights {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #718096;
            border-top: 1px solid #e2e8f0;
        }}
        @media (max-width: 768px) {{
            .container {{ margin: 10px; }}
            .content {{ padding: 20px; }}
            .stats-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p>생성일시: {current_time}</p>
        </div>
        
        <div class="content">
            <div class="summary">
                <h2>📊 분석 요약</h2>
                <p>{self._generate_summary(data, user_query)}</p>
            </div>
            
            {stats_cards}
            
            {charts_html}
            
            <div class="insights">
                <h2>💡 주요 인사이트</h2>
                {insights}
            </div>
        </div>
        
        <div class="footer">
            <p>AI 기반 데이터 분석 리포트 | 생성시간: {current_time}</p>
        </div>
    </div>
</body>
</html>"""
        
        return html_template
    
    def _create_stats_cards(self, data: Dict[str, Any]) -> str:
        """통계 카드 섹션 생성"""
        
        if not isinstance(data, dict):
            return ""
            
        cards = []
        card_count = 0
        max_cards = 4
        
        for key, value in data.items():
            if card_count >= max_cards:
                break
                
            if isinstance(value, dict) and 'total' in str(value).lower():
                # 총계가 있는 딕셔너리
                for sub_key, sub_value in value.items():
                    if 'total' in sub_key.lower() and isinstance(sub_value, (int, float)):
                        cards.append(f"""
                        <div class="stat-card">
                            <div class="stat-number">{sub_value:,}</div>
                            <div class="stat-label">{self._format_label(sub_key)}</div>
                        </div>
                        """)
                        card_count += 1
                        break
                        
            elif isinstance(value, (int, float)):
                cards.append(f"""
                <div class="stat-card">
                    <div class="stat-number">{value:,}</div>
                    <div class="stat-label">{self._format_label(key)}</div>
                </div>
                """)
                card_count += 1
                
            elif isinstance(value, list) and len(value) > 0:
                cards.append(f"""
                <div class="stat-card">
                    <div class="stat-number">{len(value)}</div>
                    <div class="stat-label">{self._format_label(key)} 항목 수</div>
                </div>
                """)
                card_count += 1
        
        # 기본 카드가 없으면 데이터 개수 표시
        if not cards:
            cards.append(f"""
            <div class="stat-card">
                <div class="stat-number">{len(data)}</div>
                <div class="stat-label">데이터 항목 수</div>
            </div>
            """)
        
        return f'<div class="stats-grid">{"".join(cards)}</div>'
    
    def _create_dynamic_charts(self, data: Dict[str, Any], chart_types: List[str]) -> str:
        """동적 차트 생성"""
        
        if not isinstance(data, dict):
            return ""
            
        charts = []
        chart_id = 0
        
        # 각 차트 유형별로 생성
        for chart_type in chart_types[:3]:  # 최대 3개 차트
            chart_data = self._extract_chart_data(data, chart_type, chart_id)
            if chart_data:
                charts.append(chart_data)
                chart_id += 1
                
        return "".join(charts)
    
    def _extract_chart_data(self, data: Dict, chart_type: str, chart_id: int) -> str:
        """차트 데이터 추출 및 HTML 생성"""
        
        chart_config = self._get_chart_config(data, chart_type, chart_id)
        if not chart_config:
            return ""
            
        return f"""
        <div class="chart-container">
            <div class="chart-title">{chart_config['title']}</div>
            <div class="chart">
                <canvas id="chart{chart_id}"></canvas>
            </div>
        </div>
        
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const ctx{chart_id} = document.getElementById('chart{chart_id}').getContext('2d');
                new Chart(ctx{chart_id}, {chart_config['config']});
            }});
        </script>
        """
    
    def _get_chart_config(self, data: Dict, chart_type: str, chart_id: int) -> Optional[Dict]:
        """차트 설정 생성"""
        
        try:
            # 데이터에서 적절한 키-값 쌍 추출
            chart_data = self._prepare_chart_data(data, chart_type)
            if not chart_data:
                return None
                
            labels = chart_data.get('labels', [])
            values = chart_data.get('values', [])
            
            if not labels or not values:
                return None
                
            # 차트 유형별 설정
            config = {
                'type': chart_type,
                'data': {
                    'labels': labels,
                    'datasets': [{
                        'label': chart_data.get('dataset_label', '데이터'),
                        'data': values,
                        'backgroundColor': self._get_chart_colors(len(values)),
                        'borderColor': '#3b82f6',
                        'borderWidth': 2
                    }]
                },
                'options': {
                    'responsive': True,
                    'maintainAspectRatio': False,
                    'plugins': {
                        'legend': {
                            'display': True,
                            'position': 'top'
                        }
                    }
                }
            }
            
            return {
                'title': chart_data.get('title', f'차트 {chart_id + 1}'),
                'config': json.dumps(config)
            }
            
        except Exception as e:
            self.logger.error(f"차트 설정 생성 실패: {e}")
            return None
    
    def _prepare_chart_data(self, data: Dict, chart_type: str) -> Optional[Dict]:
        """차트용 데이터 준비"""
        
        # 첫 번째 적절한 데이터 쌍 찾기
        for key, value in data.items():
            if isinstance(value, dict):
                # 딕셔너리 내부의 키-값을 라벨-값으로 사용
                labels = list(value.keys())[:10]  # 최대 10개
                values = []
                
                for label in labels:
                    val = value[label]
                    if isinstance(val, (int, float)):
                        values.append(val)
                    elif isinstance(val, dict) and 'count' in val:
                        values.append(val['count'])
                    else:
                        values.append(1)  # 기본값
                        
                if labels and values:
                    return {
                        'labels': labels,
                        'values': values,
                        'title': self._format_label(key),
                        'dataset_label': self._format_label(key)
                    }
                    
            elif isinstance(value, list) and len(value) > 0:
                # 리스트를 인덱스별로 차트화
                labels = [f"항목 {i+1}" for i in range(min(len(value), 10))]
                values = []
                
                for item in value[:10]:
                    if isinstance(item, (int, float)):
                        values.append(item)
                    elif isinstance(item, dict):
                        # 딕셔너리에서 숫자 값 찾기
                        num_val = next((v for v in item.values() if isinstance(v, (int, float))), 1)
                        values.append(num_val)
                    else:
                        values.append(1)
                        
                if labels and values:
                    return {
                        'labels': labels,
                        'values': values,
                        'title': self._format_label(key),
                        'dataset_label': self._format_label(key)
                    }
        
        return None
    
    def _get_chart_colors(self, count: int) -> List[str]:
        """차트 색상 팔레트 생성"""
        
        base_colors = [
            '#3b82f6', '#6366f1', '#10b981', '#f59e0b', 
            '#ef4444', '#06b6d4', '#8b5cf6', '#f97316'
        ]
        
        colors = []
        for i in range(count):
            colors.append(base_colors[i % len(base_colors)])
            
        return colors
    
    def _generate_summary(self, data: Dict, user_query: str) -> str:
        """리포트 요약 생성"""
        
        summary_parts = []
        
        # 데이터 크기 정보
        if isinstance(data, dict):
            total_items = sum(len(v) if isinstance(v, (list, dict)) else 1 for v in data.values())
            summary_parts.append(f"총 {total_items}개의 데이터 항목을 분석했습니다.")
            
        # 사용자 쿼리 반영
        if "분석" in user_query:
            summary_parts.append("요청하신 분석을 완료하여 주요 패턴과 트렌드를 확인했습니다.")
        else:
            summary_parts.append("데이터의 핵심 특성과 분포를 종합적으로 분석했습니다.")
            
        # 차트 정보
        summary_parts.append("인터랙티브 차트를 통해 데이터를 시각화하여 이해하기 쉽게 정리했습니다.")
        
        return " ".join(summary_parts)
    
    def _generate_insights(self, data: Dict, domain: str) -> str:
        """인사이트 생성"""
        
        insights = []
        
        # 도메인별 인사이트 템플릿
        domain_insights = {
            "데이터분석": [
                "데이터의 분포 패턴이 명확하게 나타나며, 주요 특성을 파악할 수 있습니다.",
                "시각화를 통해 데이터의 핵심 트렌드를 쉽게 이해할 수 있습니다."
            ],
            "시계열": [
                "시간의 흐름에 따른 변화 패턴이 명확하게 나타납니다.",
                "주기적인 패턴과 트렌드를 파악하여 향후 예측에 활용할 수 있습니다."
            ],
            "비교분석": [
                "각 항목 간의 차이점과 공통점을 명확히 파악했습니다.",
                "상대적 성과와 개선 포인트를 확인할 수 있습니다."
            ]
        }
        
        default_insights = [
            "데이터 분석 결과 의미 있는 패턴을 발견했습니다.",
            "시각화를 통해 데이터의 특성을 효과적으로 파악했습니다."
        ]
        
        selected_insights = domain_insights.get(domain, default_insights)
        
        insights_html = ""
        for i, insight in enumerate(selected_insights, 1):
            insights_html += f"<p>• {insight}</p>"
            
        return insights_html
    
    def _format_label(self, text: str) -> str:
        """라벨 포맷팅"""
        
        # camelCase나 snake_case를 읽기 쉽게 변환
        import re
        
        # snake_case를 공백으로
        text = text.replace('_', ' ')
        
        # camelCase를 공백으로  
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        # 첫 글자 대문자화
        return text.strip().title()
    
    def _generate_emergency_html(self, user_query: str, error: str) -> str:
        """응급 HTML 생성"""
        
        current_time = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
        
        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>리포트 생성 중 오류</title>
</head>
<body>
    <div style="max-width: 800px; margin: 50px auto; padding: 30px; font-family: Arial, sans-serif;">
        <h1>⚠️ 리포트 생성 중 오류</h1>
        <p><strong>요청:</strong> {user_query}</p>
        <p><strong>생성 시간:</strong> {current_time}</p>
        <p><strong>오류 내용:</strong> {error}</p>
        <p>죄송합니다. 리포트 생성 중 문제가 발생했습니다. 다시 시도해 주세요.</p>
    </div>
</body>
</html>""" 