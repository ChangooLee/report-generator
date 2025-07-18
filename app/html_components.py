"""
HTML 컴포넌트 라이브러리
LLM이 데이터를 보고 적절한 컴포넌트를 선택하여 조합할 수 있도록 하는 재사용 가능한 템플릿들
"""

class HTMLComponents:
    """재사용 가능한 HTML 컴포넌트 라이브러리"""
    
    @staticmethod
    def base_template(title: str = "데이터 분석 리포트") -> str:
        """기본 HTML 템플릿"""
        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{{{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}}}
        
        body {{{{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
            padding: 20px;
        }}}}
        
        .container {{{{
            max-width: 1400px;
            margin: 0 auto;
        }}}}
        
        .header {{{{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}}}
        
        .header h1 {{{{
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}}}
        
        .header p {{{{
            font-size: 1.2rem;
            opacity: 0.9;
        }}}}
        
        .grid {{{{
            display: grid;
            gap: 20px;
            margin-bottom: 30px;
        }}}}
        
        .grid-2 {{{{ grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); }}}}
        .grid-3 {{{{ grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); }}}}
        .grid-4 {{{{ grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}}}
        
        .card {{{{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.3);
        }}}}
        
        .card h3 {{{{
            color: #4a5568;
            margin-bottom: 15px;
            font-size: 1.3rem;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }}}}
        
        .chart-container {{{{
            position: relative;
            height: 400px;
            margin: 20px 0;
        }}}}
        
        .metric-grid {{{{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}}}
        
        .metric-card {{{{
            background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}}}
        
        .metric-number {{{{
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 5px;
        }}}}
        
        .metric-label {{{{
            font-size: 0.9rem;
            opacity: 0.9;
        }}}}
        
        .table {{{{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}}}
        
        .table th, .table td {{{{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}}}
        
        .table th {{{{
            background: #f7fafc;
            font-weight: 600;
            color: #4a5568;
        }}}}
        
        .highlight {{{{
            background: linear-gradient(120deg, #a8edea 0%, #fed6e3 100%);
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: bold;
        }}}}
        
        .insight-box {{{{
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
            border-radius: 10px;
            padding: 20px;
            margin: 15px 0;
            border-left: 4px solid #3182ce;
        }}}}
        
        .tag {{{{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
            margin: 2px;
        }}}}
        
        .tag-positive {{{{ background: #d4edda; color: #155724; }}}}
        .tag-negative {{{{ background: #f8d7da; color: #721c24; }}}}
        .tag-neutral {{{{ background: #fff3cd; color: #856404; }}}}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {title}</h1>
            <p>AI 에이전트가 생성한 데이터 분석 리포트</p>
        </div>
        {{content}}
    </div>
    {{scripts}}
</body>
</html>"""

    @staticmethod
    def metric_cards(metrics: list) -> str:
        """메트릭 카드 컴포넌트"""
        cards_html = ""
        for metric in metrics:
            cards_html += f"""
        <div class="metric-card">
            <div class="metric-number">{metric.get('value', 'N/A')}</div>
            <div class="metric-label">{metric.get('label', '')}</div>
        </div>"""
        
        return f"""
    <div class="card">
        <h3>📈 주요 지표</h3>
        <div class="metric-grid">
            {cards_html}
        </div>
    </div>"""

    @staticmethod
    def chart_component(chart_id: str, title: str, chart_type: str = "line") -> str:
        """차트 컴포넌트"""
        return f"""
    <div class="card">
        <h3>{title}</h3>
        <div class="chart-container">
            <canvas id="{chart_id}"></canvas>
        </div>
    </div>"""

    @staticmethod
    def data_table(headers: list, rows: list, title: str = "데이터 테이블") -> str:
        """데이터 테이블 컴포넌트"""
        header_html = "".join([f"<th>{header}</th>" for header in headers])
        rows_html = ""
        
        for row in rows:
            row_html = "".join([f"<td>{cell}</td>" for cell in row])
            rows_html += f"<tr>{row_html}</tr>"
        
        return f"""
    <div class="card">
        <h3>{title}</h3>
        <table class="table">
            <thead>
                <tr>{header_html}</tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>"""

    @staticmethod
    def insight_box(insights: list) -> str:
        """인사이트 박스 컴포넌트"""
        insights_html = ""
        for insight in insights:
            insights_html += f"""
        <div class="insight-box">
            <strong>{insight.get('title', '')}</strong>
            <p>{insight.get('content', '')}</p>
        </div>"""
        
        return f"""
    <div class="card">
        <h3>💡 주요 인사이트</h3>
        {insights_html}
    </div>"""

    @staticmethod
    def chart_script(chart_id: str, chart_type: str, data: dict, options: dict = None) -> str:
        """Chart.js 스크립트 생성"""
        default_options = {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"position": "top"},
                "title": {"display": True, "text": data.get("title", "")}
            }
        }
        
        if options:
            default_options.update(options)
        
        return f"""
    const {chart_id}Ctx = document.getElementById('{chart_id}').getContext('2d');
    new Chart({chart_id}Ctx, {{
        type: '{chart_type}',
        data: {data},
        options: {default_options}
    }});"""


class ComponentSelector:
    """LLM이 데이터를 분석하여 적절한 컴포넌트를 선택하는 도우미"""
    
    @staticmethod
    def analyze_data_structure(data: dict) -> dict:
        """데이터 구조를 분석하여 권장 컴포넌트 반환"""
        recommendations = {
            "charts": [],
            "metrics": [],
            "tables": [],
            "layout": "grid-2"
        }
        
        # 숫자 데이터가 있으면 차트 권장
        numeric_fields = []
        categorical_fields = []
        time_fields = []
        
        for key, value in data.items():
            if isinstance(value, (int, float)):
                numeric_fields.append(key)
            elif isinstance(value, str):
                if any(time_word in key.lower() for time_word in ['date', 'time', 'month', 'year']):
                    time_fields.append(key)
                else:
                    categorical_fields.append(key)
        
        # 차트 유형 권장
        if time_fields and numeric_fields:
            recommendations["charts"].append({
                "type": "line",
                "title": "시간별 트렌드",
                "x_field": time_fields[0],
                "y_field": numeric_fields[0]
            })
        
        if categorical_fields and numeric_fields:
            recommendations["charts"].append({
                "type": "bar",
                "title": "카테고리별 분석",
                "x_field": categorical_fields[0],
                "y_field": numeric_fields[0]
            })
        
        if len(numeric_fields) >= 2:
            recommendations["charts"].append({
                "type": "scatter",
                "title": "상관관계 분석",
                "x_field": numeric_fields[0],
                "y_field": numeric_fields[1]
            })
        
        # 메트릭 권장
        for field in numeric_fields:
            recommendations["metrics"].append({
                "label": field.replace("_", " ").title(),
                "value": data.get(field, 0)
            })
        
        # 레이아웃 권장
        component_count = len(recommendations["charts"]) + (1 if recommendations["metrics"] else 0)
        if component_count <= 2:
            recommendations["layout"] = "grid-2"
        elif component_count <= 3:
            recommendations["layout"] = "grid-3"
        else:
            recommendations["layout"] = "grid-4"
        
        return recommendations

    @staticmethod
    def generate_color_palette(count: int) -> list:
        """동적 색상 팔레트 생성"""
        colors = [
            'rgba(255, 99, 132, 0.8)',
            'rgba(54, 162, 235, 0.8)', 
            'rgba(255, 205, 86, 0.8)',
            'rgba(75, 192, 192, 0.8)',
            'rgba(153, 102, 255, 0.8)',
            'rgba(255, 159, 64, 0.8)',
            'rgba(199, 199, 199, 0.8)',
            'rgba(83, 102, 255, 0.8)'
        ]
        return (colors * ((count // len(colors)) + 1))[:count] 