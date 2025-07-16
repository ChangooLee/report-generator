"""
Dynamic Chart and Visualization Template Generator
동적 차트, 표, 그래프 생성을 위한 템플릿 엔진
"""

import json
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass


class VisualizationType(Enum):
    """지원하는 시각화 타입"""
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    PIE_CHART = "pie_chart"
    SCATTER_PLOT = "scatter_plot"
    AREA_CHART = "area_chart"
    HISTOGRAM = "histogram"
    BOX_PLOT = "box_plot"
    HEATMAP = "heatmap"
    DATA_TABLE = "data_table"
    KPI_CARDS = "kpi_cards"
    GAUGE_CHART = "gauge_chart"
    TREEMAP = "treemap"
    RADAR_CHART = "radar_chart"
    BUBBLE_CHART = "bubble_chart"
    VIOLIN_PLOT = "violin_plot"


@dataclass
class TemplateConfig:
    """템플릿 설정"""
    chart_type: VisualizationType
    title: str
    data_fields: List[str]
    color_scheme: str = "modern"
    interactive: bool = True
    responsive: bool = True
    animation: bool = True
    custom_options: Dict[str, Any] = None


class TemplateGenerator:
    """동적 시각화 템플릿 생성기"""
    
    def __init__(self):
        self.color_schemes = {
            "modern": ["#667eea", "#764ba2", "#f093fb", "#f5576c", "#4facfe", "#00f2fe"],
            "corporate": ["#2c3e50", "#34495e", "#3498db", "#e74c3c", "#f39c12", "#27ae60"],
            "vibrant": ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#feca57", "#ff9ff3"],
            "pastel": ["#ffeaa7", "#fab1a0", "#fd79a8", "#fdcb6e", "#6c5ce7", "#a29bfe"],
            "dark": ["#2d3436", "#636e72", "#74b9ff", "#0984e3", "#00cec9", "#fd79a8"]
        }
    
    def generate_chart_template(self, config: TemplateConfig) -> Dict[str, str]:
        """차트 템플릿 생성"""
        
        if config.chart_type == VisualizationType.BAR_CHART:
            return self._generate_bar_chart_template(config)
        elif config.chart_type == VisualizationType.LINE_CHART:
            return self._generate_line_chart_template(config)
        elif config.chart_type == VisualizationType.PIE_CHART:
            return self._generate_pie_chart_template(config)
        elif config.chart_type == VisualizationType.SCATTER_PLOT:
            return self._generate_scatter_plot_template(config)
        elif config.chart_type == VisualizationType.AREA_CHART:
            return self._generate_area_chart_template(config)
        elif config.chart_type == VisualizationType.HISTOGRAM:
            return self._generate_histogram_template(config)
        elif config.chart_type == VisualizationType.HEATMAP:
            return self._generate_heatmap_template(config)
        elif config.chart_type == VisualizationType.DATA_TABLE:
            return self._generate_data_table_template(config)
        elif config.chart_type == VisualizationType.KPI_CARDS:
            return self._generate_kpi_cards_template(config)
        elif config.chart_type == VisualizationType.GAUGE_CHART:
            return self._generate_gauge_chart_template(config)
        elif config.chart_type == VisualizationType.RADAR_CHART:
            return self._generate_radar_chart_template(config)
        else:
            return self._generate_default_template(config)
    
    def _generate_bar_chart_template(self, config: TemplateConfig) -> Dict[str, str]:
        """막대차트 템플릿"""
        
        colors = self.color_schemes.get(config.color_scheme, self.color_schemes["modern"])
        
        data_processing = f"""
# 막대차트 데이터 처리
chart_data = {{}}

if 'main_data' in context_data and context_data['main_data']:
    df = pd.DataFrame(context_data['main_data'])
    
    if len({config.data_fields}) == 1:
        # 단일 필드: 카테고리별 빈도
        field = '{config.data_fields[0] if config.data_fields else 'value'}'
        if field in df.columns:
            value_counts = df[field].value_counts().head(10)
            chart_data = {{
                'labels': value_counts.index.tolist(),
                'data': value_counts.values.tolist()
            }}
    elif len({config.data_fields}) >= 2:
        # 두 필드: 그룹별 집계
        x_field, y_field = '{config.data_fields[0]}', '{config.data_fields[1] if len(config.data_fields) > 1 else config.data_fields[0]}'
        if x_field in df.columns and y_field in df.columns:
            grouped = df.groupby(x_field)[y_field].mean().head(10)
            chart_data = {{
                'labels': grouped.index.tolist(),
                'data': grouped.values.tolist()
            }}

print(f"막대차트 데이터 준비 완료: {{len(chart_data.get('labels', []))}}개 항목")
"""

        html_template = f"""
<div class="chart-container" id="bar-chart-container">
    <h3 class="chart-title">{config.title}</h3>
    <canvas id="barChart" style="width: 100%; height: 400px;"></canvas>
</div>
"""

        javascript_template = f"""
// 막대차트 생성
if (typeof Chart !== 'undefined' && chart_data && chart_data.labels) {{
    const barCtx = document.getElementById('barChart').getContext('2d');
    new Chart(barCtx, {{
        type: 'bar',
        data: {{
            labels: chart_data.labels,
            datasets: [{{
                label: '{config.data_fields[1] if len(config.data_fields) > 1 else "값"}',
                data: chart_data.data,
                backgroundColor: {json.dumps(colors)},
                borderColor: '#ffffff',
                borderWidth: 2,
                borderRadius: {'5' if config.interactive else '0'},
                borderSkipped: false,
            }}]
        }},
        options: {{
            responsive: {str(config.responsive).lower()},
            maintainAspectRatio: false,
            animation: {{
                duration: {1000 if config.animation else 0}
            }},
            interaction: {{
                intersect: false,
                mode: 'index'
            }},
            plugins: {{
                title: {{
                    display: true,
                    text: '{config.title}',
                    font: {{
                        size: 16,
                        weight: 'bold'
                    }}
                }},
                legend: {{
                    display: {str(len(config.data_fields) > 1).lower()},
                    position: 'top'
                }},
                tooltip: {{
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#667eea',
                    borderWidth: 1
                }}
            }},
            scales: {{
                y: {{
                    beginAtZero: true,
                    grid: {{
                        color: 'rgba(0,0,0,0.1)',
                        drawBorder: false
                    }},
                    ticks: {{
                        font: {{
                            size: 12
                        }}
                    }}
                }},
                x: {{
                    grid: {{
                        display: false
                    }},
                    ticks: {{
                        maxRotation: 45,
                        font: {{
                            size: 12
                        }}
                    }}
                }}
            }}
        }}
    }});
    console.log('막대차트 생성 완료');
}} else {{
    console.warn('막대차트 데이터가 없거나 Chart.js가 로드되지 않음');
}}
"""

        return {
            "data_processing": data_processing,
            "html": html_template,
            "javascript": javascript_template
        }
    
    def _generate_line_chart_template(self, config: TemplateConfig) -> Dict[str, str]:
        """선형차트 템플릿"""
        
        colors = self.color_schemes.get(config.color_scheme, self.color_schemes["modern"])
        
        data_processing = f"""
# 선형차트 데이터 처리
line_chart_data = {{}}

if 'main_data' in context_data and context_data['main_data']:
    df = pd.DataFrame(context_data['main_data'])
    
    if len({config.data_fields}) >= 2:
        x_field, y_field = '{config.data_fields[0]}', '{config.data_fields[1]}'
        if x_field in df.columns and y_field in df.columns:
            # 시간순 정렬 시도
            try:
                df[x_field] = pd.to_datetime(df[x_field])
                df = df.sort_values(x_field)
                df[x_field] = df[x_field].dt.strftime('%Y-%m-%d')
            except:
                # 날짜가 아니면 그냥 정렬
                df = df.sort_values(x_field)
            
            # 중복값 처리 (평균)
            grouped = df.groupby(x_field)[y_field].mean()
            
            line_chart_data = {{
                'labels': grouped.index.tolist(),
                'data': grouped.values.tolist()
            }}

print(f"선형차트 데이터 준비 완료: {{len(line_chart_data.get('labels', []))}}개 포인트")
"""

        html_template = f"""
<div class="chart-container" id="line-chart-container">
    <h3 class="chart-title">{config.title}</h3>
    <canvas id="lineChart" style="width: 100%; height: 400px;"></canvas>
</div>
"""

        javascript_template = f"""
// 선형차트 생성
if (typeof Chart !== 'undefined' && line_chart_data && line_chart_data.labels) {{
    const lineCtx = document.getElementById('lineChart').getContext('2d');
    new Chart(lineCtx, {{
        type: 'line',
        data: {{
            labels: line_chart_data.labels,
            datasets: [{{
                label: '{config.data_fields[1] if len(config.data_fields) > 1 else "값"}',
                data: line_chart_data.data,
                borderColor: '{colors[0]}',
                backgroundColor: '{colors[0]}20',
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '{colors[0]}',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }}]
        }},
        options: {{
            responsive: {str(config.responsive).lower()},
            maintainAspectRatio: false,
            animation: {{
                duration: {1200 if config.animation else 0}
            }},
            interaction: {{
                intersect: false,
                mode: 'index'
            }},
            plugins: {{
                title: {{
                    display: true,
                    text: '{config.title}',
                    font: {{
                        size: 16,
                        weight: 'bold'
                    }}
                }},
                legend: {{
                    display: true,
                    position: 'top'
                }},
                tooltip: {{
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff'
                }}
            }},
            scales: {{
                y: {{
                    beginAtZero: false,
                    grid: {{
                        color: 'rgba(0,0,0,0.1)'
                    }}
                }},
                x: {{
                    grid: {{
                        display: false
                    }}
                }}
            }}
        }}
    }});
    console.log('선형차트 생성 완료');
}} else {{
    console.warn('선형차트 데이터가 없거나 Chart.js가 로드되지 않음');
}}
"""

        return {
            "data_processing": data_processing,
            "html": html_template,
            "javascript": javascript_template
        }
    
    def _generate_pie_chart_template(self, config: TemplateConfig) -> Dict[str, str]:
        """파이차트 템플릿"""
        
        colors = self.color_schemes.get(config.color_scheme, self.color_schemes["modern"])
        
        data_processing = f"""
# 파이차트 데이터 처리
pie_chart_data = {{}}

if 'main_data' in context_data and context_data['main_data']:
    df = pd.DataFrame(context_data['main_data'])
    
    field = '{config.data_fields[0] if config.data_fields else 'category'}'
    if field in df.columns:
        value_counts = df[field].value_counts().head(8)  # 상위 8개만
        pie_chart_data = {{
            'labels': value_counts.index.tolist(),
            'data': value_counts.values.tolist()
        }}

print(f"파이차트 데이터 준비 완료: {{len(pie_chart_data.get('labels', []))}}개 섹션")
"""

        html_template = f"""
<div class="chart-container" id="pie-chart-container">
    <h3 class="chart-title">{config.title}</h3>
    <canvas id="pieChart" style="width: 100%; height: 400px;"></canvas>
</div>
"""

        javascript_template = f"""
// 파이차트 생성
if (typeof Chart !== 'undefined' && pie_chart_data && pie_chart_data.labels) {{
    const pieCtx = document.getElementById('pieChart').getContext('2d');
    new Chart(pieCtx, {{
        type: 'pie',
        data: {{
            labels: pie_chart_data.labels,
            datasets: [{{
                data: pie_chart_data.data,
                backgroundColor: {json.dumps(colors + colors)},  // 색상 확장
                borderColor: '#ffffff',
                borderWidth: 3,
                hoverOffset: 4
            }}]
        }},
        options: {{
            responsive: {str(config.responsive).lower()},
            maintainAspectRatio: false,
            animation: {{
                animateRotate: {str(config.animation).lower()},
                duration: {1500 if config.animation else 0}
            }},
            plugins: {{
                title: {{
                    display: true,
                    text: '{config.title}',
                    font: {{
                        size: 16,
                        weight: 'bold'
                    }}
                }},
                legend: {{
                    display: true,
                    position: 'right',
                    labels: {{
                        padding: 20,
                        usePointStyle: true,
                        font: {{
                            size: 12
                        }}
                    }}
                }},
                tooltip: {{
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    callbacks: {{
                        label: function(context) {{
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return context.label + ': ' + percentage + '%';
                        }}
                    }}
                }}
            }}
        }}
    }});
    console.log('파이차트 생성 완료');
}} else {{
    console.warn('파이차트 데이터가 없거나 Chart.js가 로드되지 않음');
}}
"""

        return {
            "data_processing": data_processing,
            "html": html_template,
            "javascript": javascript_template
        }
    
    def _generate_scatter_plot_template(self, config: TemplateConfig) -> Dict[str, str]:
        """산점도 템플릿"""
        
        colors = self.color_schemes.get(config.color_scheme, self.color_schemes["modern"])
        
        data_processing = f"""
# 산점도 데이터 처리
scatter_data = {{}}

if 'main_data' in context_data and context_data['main_data']:
    df = pd.DataFrame(context_data['main_data'])
    
    if len({config.data_fields}) >= 2:
        x_field, y_field = '{config.data_fields[0]}', '{config.data_fields[1]}'
        if x_field in df.columns and y_field in df.columns:
            # 수치형 데이터만 선택
            numeric_df = df[[x_field, y_field]].select_dtypes(include=['number'])
            if not numeric_df.empty:
                scatter_data = {{
                    'data': [{{
                        'x': float(row[x_field]) if pd.notnull(row[x_field]) else 0,
                        'y': float(row[y_field]) if pd.notnull(row[y_field]) else 0
                    }} for _, row in numeric_df.iterrows()],
                    'x_label': x_field,
                    'y_label': y_field
                }}

print(f"산점도 데이터 준비 완료: {{len(scatter_data.get('data', []))}}개 포인트")
"""

        html_template = f"""
<div class="chart-container" id="scatter-chart-container">
    <h3 class="chart-title">{config.title}</h3>
    <canvas id="scatterChart" style="width: 100%; height: 400px;"></canvas>
</div>
"""

        javascript_template = f"""
// 산점도 생성
if (typeof Chart !== 'undefined' && scatter_data && scatter_data.data) {{
    const scatterCtx = document.getElementById('scatterChart').getContext('2d');
    new Chart(scatterCtx, {{
        type: 'scatter',
        data: {{
            datasets: [{{
                label: '{config.data_fields[0] if config.data_fields else "X"} vs {config.data_fields[1] if len(config.data_fields) > 1 else "Y"}',
                data: scatter_data.data,
                backgroundColor: '{colors[0]}80',
                borderColor: '{colors[0]}',
                pointRadius: 6,
                pointHoverRadius: 8,
                pointBorderWidth: 2,
                pointBorderColor: '#ffffff'
            }}]
        }},
        options: {{
            responsive: {str(config.responsive).lower()},
            maintainAspectRatio: false,
            animation: {{
                duration: {1000 if config.animation else 0}
            }},
            plugins: {{
                title: {{
                    display: true,
                    text: '{config.title}',
                    font: {{
                        size: 16,
                        weight: 'bold'
                    }}
                }},
                legend: {{
                    display: true,
                    position: 'top'
                }},
                tooltip: {{
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff'
                }}
            }},
            scales: {{
                x: {{
                    type: 'linear',
                    position: 'bottom',
                    title: {{
                        display: true,
                        text: scatter_data.x_label || '{config.data_fields[0] if config.data_fields else "X축"}',
                        font: {{
                            size: 14,
                            weight: 'bold'
                        }}
                    }},
                    grid: {{
                        color: 'rgba(0,0,0,0.1)'
                    }}
                }},
                y: {{
                    title: {{
                        display: true,
                        text: scatter_data.y_label || '{config.data_fields[1] if len(config.data_fields) > 1 else "Y축"}',
                        font: {{
                            size: 14,
                            weight: 'bold'
                        }}
                    }},
                    grid: {{
                        color: 'rgba(0,0,0,0.1)'
                    }}
                }}
            }}
        }}
    }});
    console.log('산점도 생성 완료');
}} else {{
    console.warn('산점도 데이터가 없거나 Chart.js가 로드되지 않음');
}}
"""

        return {
            "data_processing": data_processing,
            "html": html_template,
            "javascript": javascript_template
        }
    
    def _generate_data_table_template(self, config: TemplateConfig) -> Dict[str, str]:
        """데이터 테이블 템플릿"""
        
        data_processing = f"""
# 데이터 테이블 처리
table_data = {{}}

if 'main_data' in context_data and context_data['main_data']:
    df = pd.DataFrame(context_data['main_data'])
    
    # 표시할 열 선택
    display_columns = {config.data_fields if config.data_fields else 'list(df.columns)'}
    if not display_columns:
        display_columns = list(df.columns)[:8]  # 최대 8개 열만
    
    # 존재하는 열만 선택
    available_columns = [col for col in display_columns if col in df.columns]
    
    if available_columns:
        table_df = df[available_columns].head(20)  # 최대 20행
        
        # 수치형 데이터 포맷팅
        for col in table_df.columns:
            if table_df[col].dtype in ['float64', 'int64']:
                if table_df[col].dtype == 'float64':
                    table_df[col] = table_df[col].round(2)
        
        table_data = {{
            'columns': available_columns,
            'rows': table_df.values.tolist(),
            'total_rows': len(df)
        }}

print(f"데이터 테이블 준비 완료: {{len(table_data.get('rows', []))}}행 x {{len(table_data.get('columns', []))}}열")
"""

        html_template = f"""
<div class="section" id="data-table-section">
    <h3 class="section-title">{config.title}</h3>
    <div class="table-container">
        <div id="dataTable"></div>
    </div>
</div>

<style>
.table-container {{
    overflow-x: auto;
    background: white;
    border-radius: 10px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    margin: 20px 0;
}}

.modern-table {{
    width: 100%;
    border-collapse: collapse;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px;
}}

.modern-table th {{
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 15px 12px;
    text-align: left;
    font-weight: 600;
    border: none;
    position: sticky;
    top: 0;
    z-index: 10;
}}

.modern-table td {{
    padding: 12px;
    border-bottom: 1px solid #f0f0f0;
    transition: background-color 0.2s ease;
}}

.modern-table tbody tr:hover {{
    background-color: #f8f9ff;
}}

.modern-table tbody tr:nth-child(even) {{
    background-color: #fafafa;
}}

.table-info {{
    padding: 10px 15px;
    background: #f8f9fa;
    border-radius: 0 0 10px 10px;
    font-size: 12px;
    color: #666;
    text-align: center;
}}
</style>
"""

        javascript_template = f"""
// 데이터 테이블 생성
if (table_data && table_data.columns && table_data.rows) {{
    const tableContainer = document.getElementById('dataTable');
    
    let tableHTML = '<table class="modern-table">';
    
    // 헤더 생성
    tableHTML += '<thead><tr>';
    table_data.columns.forEach(col => {{
        tableHTML += `<th>${{col}}</th>`;
    }});
    tableHTML += '</tr></thead>';
    
    // 데이터 행 생성
    tableHTML += '<tbody>';
    table_data.rows.forEach(row => {{
        tableHTML += '<tr>';
        row.forEach(cell => {{
            // null/undefined 처리
            const displayValue = cell !== null && cell !== undefined ? cell : '';
            // 숫자 포맷팅
            const formattedValue = typeof cell === 'number' ? 
                (Number.isInteger(cell) ? cell.toLocaleString() : cell.toFixed(2)) : 
                displayValue;
            tableHTML += `<td>${{formattedValue}}</td>`;
        }});
        tableHTML += '</tr>';
    }});
    tableHTML += '</tbody>';
    
    tableHTML += '</table>';
    
    // 테이블 정보 추가
    tableHTML += `<div class="table-info">
        표시된 행: ${{table_data.rows.length}} / 전체: ${{table_data.total_rows || table_data.rows.length}}
    </div>`;
    
    tableContainer.innerHTML = tableHTML;
    
    console.log('데이터 테이블 생성 완료');
}} else {{
    console.warn('테이블 데이터가 없음');
}}
"""

        return {
            "data_processing": data_processing,
            "html": html_template,
            "javascript": javascript_template
        }
    
    def _generate_kpi_cards_template(self, config: TemplateConfig) -> Dict[str, str]:
        """KPI 카드 템플릿"""
        
        colors = self.color_schemes.get(config.color_scheme, self.color_schemes["modern"])
        
        data_processing = f"""
# KPI 카드 데이터 처리
kpi_data = []

if 'main_data' in context_data and context_data['main_data']:
    df = pd.DataFrame(context_data['main_data'])
    
    # 수치형 컬럼들에 대한 기본 KPI 계산
    numeric_columns = df.select_dtypes(include=['number']).columns
    
    for col in numeric_columns[:6]:  # 최대 6개 KPI
        if col in df.columns:
            values = df[col].dropna()
            if len(values) > 0:
                kpi_data.append({{
                    'title': col.replace('_', ' ').title(),
                    'value': f'{{values.sum():,.0f}}' if values.sum() > 100 else f'{{values.mean():.2f}}',
                    'subtitle': 'Total' if values.sum() > 100 else 'Average',
                    'trend': 'up' if values.mean() > values.median() else 'down',
                    'percentage': f'{{abs(values.std() / values.mean() * 100):.1f}}%' if values.mean() != 0 else '0%'
                }})
    
    # 추가 통계 KPI
    if len(df) > 0:
        kpi_data.extend([
            {{
                'title': 'Total Records',
                'value': f'{{len(df):,}}',
                'subtitle': 'Data Points',
                'trend': 'neutral',
                'percentage': '100%'
            }},
            {{
                'title': 'Completeness',
                'value': f'{{(1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100:.1f}}%',
                'subtitle': 'Data Quality',
                'trend': 'up',
                'percentage': 'Quality Score'
            }}
        ])

print(f"KPI 카드 데이터 준비 완료: {{len(kpi_data)}}개 지표")
"""

        html_template = f"""
<div class="section" id="kpi-section">
    <h3 class="section-title">{config.title}</h3>
    <div class="kpi-grid" id="kpiGrid">
        <!-- KPI 카드들이 동적으로 생성됩니다 -->
    </div>
</div>

<style>
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
    margin: 20px 0;
}}

.kpi-card {{
    background: linear-gradient(135deg, var(--card-color-1), var(--card-color-2));
    color: white;
    padding: 25px;
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    position: relative;
    overflow: hidden;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}}

.kpi-card:hover {{
    transform: translateY(-5px);
    box-shadow: 0 15px 40px rgba(0,0,0,0.2);
}}

.kpi-card::before {{
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 100px;
    height: 100px;
    background: rgba(255,255,255,0.1);
    border-radius: 50%;
    transform: translate(30px, -30px);
}}

.kpi-title {{
    font-size: 0.9rem;
    opacity: 0.9;
    margin-bottom: 5px;
    font-weight: 500;
}}

.kpi-value {{
    font-size: 2.2rem;
    font-weight: 700;
    margin-bottom: 5px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.2);
}}

.kpi-subtitle {{
    font-size: 0.8rem;
    opacity: 0.8;
    margin-bottom: 10px;
}}

.kpi-trend {{
    display: flex;
    align-items: center;
    font-size: 0.8rem;
    gap: 5px;
}}

.trend-icon {{
    width: 12px;
    height: 12px;
    border-radius: 50%;
}}

.trend-up {{ background: #4ade80; }}
.trend-down {{ background: #f87171; }}
.trend-neutral {{ background: #94a3b8; }}

/* 색상 테마 */
.kpi-card:nth-child(1) {{ --card-color-1: #667eea; --card-color-2: #764ba2; }}
.kpi-card:nth-child(2) {{ --card-color-1: #f093fb; --card-color-2: #f5576c; }}
.kpi-card:nth-child(3) {{ --card-color-1: #4facfe; --card-color-2: #00f2fe; }}
.kpi-card:nth-child(4) {{ --card-color-1: #43e97b; --card-color-2: #38f9d7; }}
.kpi-card:nth-child(5) {{ --card-color-1: #fa709a; --card-color-2: #fee140; }}
.kpi-card:nth-child(6) {{ --card-color-1: #a8edea; --card-color-2: #fed6e3; }}
</style>
"""

        javascript_template = f"""
// KPI 카드 생성
if (kpi_data && kpi_data.length > 0) {{
    const kpiContainer = document.getElementById('kpiGrid');
    let cardsHTML = '';
    
    kpi_data.forEach((kpi, index) => {{
        const trendClass = kpi.trend === 'up' ? 'trend-up' : 
                          kpi.trend === 'down' ? 'trend-down' : 'trend-neutral';
        
        cardsHTML += `
            <div class="kpi-card">
                <div class="kpi-title">${{kpi.title}}</div>
                <div class="kpi-value">${{kpi.value}}</div>
                <div class="kpi-subtitle">${{kpi.subtitle}}</div>
                <div class="kpi-trend">
                    <div class="trend-icon ${{trendClass}}"></div>
                    <span>${{kpi.percentage}}</span>
                </div>
            </div>
        `;
    }});
    
    kpiContainer.innerHTML = cardsHTML;
    
    // 애니메이션 효과
    const cards = kpiContainer.querySelectorAll('.kpi-card');
    cards.forEach((card, index) => {{
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {{
            card.style.transition = 'all 0.6s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }}, index * 100);
    }});
    
    console.log('KPI 카드 생성 완료');
}} else {{
    console.warn('KPI 데이터가 없음');
}}
"""

        return {
            "data_processing": data_processing,
            "html": html_template,
            "javascript": javascript_template
        }
    
    def _generate_histogram_template(self, config: TemplateConfig) -> Dict[str, str]:
        """히스토그램 템플릿"""
        
        colors = self.color_schemes.get(config.color_scheme, self.color_schemes["modern"])
        
        data_processing = f"""
# 히스토그램 데이터 처리
histogram_data = {{}}

if 'main_data' in context_data and context_data['main_data']:
    df = pd.DataFrame(context_data['main_data'])
    
    field = '{config.data_fields[0] if config.data_fields else 'value'}'
    if field in df.columns:
        values = pd.to_numeric(df[field], errors='coerce').dropna()
        if len(values) > 0:
            # 구간 생성 (최대 20개)
            n_bins = min(20, max(5, int(len(values) ** 0.5)))
            hist, bin_edges = np.histogram(values, bins=n_bins)
            
            # 구간 라벨 생성
            bin_labels = [f'{{bin_edges[i]:.1f}}-{{bin_edges[i+1]:.1f}}' for i in range(len(hist))]
            
            histogram_data = {{
                'labels': bin_labels,
                'data': hist.tolist(),
                'field_name': field
            }}

print(f"히스토그램 데이터 준비 완료: {{len(histogram_data.get('labels', []))}}개 구간")
"""

        html_template = f"""
<div class="chart-container" id="histogram-container">
    <h3 class="chart-title">{config.title}</h3>
    <canvas id="histogramChart" style="width: 100%; height: 400px;"></canvas>
</div>
"""

        javascript_template = f"""
// 히스토그램 생성
if (typeof Chart !== 'undefined' && histogram_data && histogram_data.labels) {{
    const histCtx = document.getElementById('histogramChart').getContext('2d');
    new Chart(histCtx, {{
        type: 'bar',
        data: {{
            labels: histogram_data.labels,
            datasets: [{{
                label: 'Frequency',
                data: histogram_data.data,
                backgroundColor: '{colors[0]}80',
                borderColor: '{colors[0]}',
                borderWidth: 1,
                borderRadius: 2
            }}]
        }},
        options: {{
            responsive: {str(config.responsive).lower()},
            maintainAspectRatio: false,
            animation: {{
                duration: {1000 if config.animation else 0}
            }},
            plugins: {{
                title: {{
                    display: true,
                    text: '{config.title}',
                    font: {{
                        size: 16,
                        weight: 'bold'
                    }}
                }},
                legend: {{
                    display: false
                }},
                tooltip: {{
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    callbacks: {{
                        title: function(context) {{
                            return `Range: ${{context[0].label}}`;
                        }},
                        label: function(context) {{
                            return `Frequency: ${{context.parsed.y}}`;
                        }}
                    }}
                }}
            }},
            scales: {{
                y: {{
                    beginAtZero: true,
                    title: {{
                        display: true,
                        text: 'Frequency'
                    }},
                    grid: {{
                        color: 'rgba(0,0,0,0.1)'
                    }}
                }},
                x: {{
                    title: {{
                        display: true,
                        text: histogram_data.field_name || '{config.data_fields[0] if config.data_fields else "Value"}'
                    }},
                    grid: {{
                        display: false
                    }},
                    ticks: {{
                        maxRotation: 45
                    }}
                }}
            }}
        }}
    }});
    console.log('히스토그램 생성 완료');
}} else {{
    console.warn('히스토그램 데이터가 없거나 Chart.js가 로드되지 않음');
}}
"""

        return {
            "data_processing": data_processing,
            "html": html_template,
            "javascript": javascript_template
        }
    
    def _generate_area_chart_template(self, config: TemplateConfig) -> Dict[str, str]:
        """영역차트 템플릿"""
        
        colors = self.color_schemes.get(config.color_scheme, self.color_schemes["modern"])
        
        # 기본적으로 선형차트와 비슷하지만 fill 옵션이 다름
        line_template = self._generate_line_chart_template(config)
        
        # JavaScript에서 fill: true로 변경
        javascript_template = line_template["javascript"].replace(
            "fill: true,", "fill: true,"
        ).replace(
            "lineChart", "areaChart"
        ).replace(
            "선형차트", "영역차트"
        )
        
        html_template = line_template["html"].replace(
            "line-chart-container", "area-chart-container"
        ).replace(
            "lineChart", "areaChart"
        )
        
        data_processing = line_template["data_processing"].replace(
            "선형차트", "영역차트"
        ).replace(
            "line_chart_data", "area_chart_data"
        )
        
        return {
            "data_processing": data_processing,
            "html": html_template,
            "javascript": javascript_template
        }
    
    def _generate_heatmap_template(self, config: TemplateConfig) -> Dict[str, str]:
        """히트맵 템플릿 (상관관계 매트릭스)"""
        
        data_processing = f"""
# 히트맵 데이터 처리 (상관관계 매트릭스)
heatmap_data = {{}}

if 'main_data' in context_data and context_data['main_data']:
    df = pd.DataFrame(context_data['main_data'])
    
    # 수치형 컬럼만 선택
    numeric_df = df.select_dtypes(include=['number'])
    
    if len(numeric_df.columns) >= 2:
        # 상관관계 계산
        corr_matrix = numeric_df.corr()
        
        # 히트맵용 데이터 변환
        heatmap_values = []
        for i, row_name in enumerate(corr_matrix.index):
            for j, col_name in enumerate(corr_matrix.columns):
                heatmap_values.append({{
                    'x': j,
                    'y': i,
                    'v': corr_matrix.iloc[i, j],
                    'row': row_name,
                    'col': col_name
                }})
        
        heatmap_data = {{
            'data': heatmap_values,
            'labels': corr_matrix.columns.tolist(),
            'size': len(corr_matrix)
        }}

print(f"히트맵 데이터 준비 완료: {{heatmap_data.get('size', 0)}}x{{heatmap_data.get('size', 0)}} 매트릭스")
"""

        html_template = f"""
<div class="chart-container" id="heatmap-container">
    <h3 class="chart-title">{config.title}</h3>
    <div id="heatmapViz" style="width: 100%; height: 400px; background: white; border-radius: 10px;"></div>
</div>

<style>
.heatmap-cell {{
    transition: opacity 0.2s ease;
    cursor: pointer;
}}

.heatmap-cell:hover {{
    stroke: #333;
    stroke-width: 2;
}}

.heatmap-label {{
    font-size: 12px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    fill: #333;
}}

.heatmap-tooltip {{
    position: absolute;
    background: rgba(0,0,0,0.8);
    color: white;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 12px;
    pointer-events: none;
    z-index: 1000;
}}
</style>
"""

        javascript_template = f"""
// 히트맵 생성 (D3.js 스타일 구현)
if (heatmap_data && heatmap_data.data) {{
    const container = document.getElementById('heatmapViz');
    const size = heatmap_data.size;
    const cellSize = Math.min(300 / size, 40);
    const margin = 60;
    
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', size * cellSize + margin * 2);
    svg.setAttribute('height', size * cellSize + margin * 2);
    container.appendChild(svg);
    
    // 색상 스케일 함수
    function getColor(value) {{
        const intensity = Math.abs(value);
        if (value > 0) {{
            return `rgba(102, 126, 234, ${{intensity}})`;  // 양의 상관관계: 파란색
        }} else {{
            return `rgba(245, 87, 108, ${{intensity}})`;   // 음의 상관관계: 빨간색
        }}
    }}
    
    // 툴팁 생성
    const tooltip = document.createElement('div');
    tooltip.className = 'heatmap-tooltip';
    tooltip.style.display = 'none';
    document.body.appendChild(tooltip);
    
    // 셀 생성
    heatmap_data.data.forEach(d => {{
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', d.x * cellSize + margin);
        rect.setAttribute('y', d.y * cellSize + margin);
        rect.setAttribute('width', cellSize - 1);
        rect.setAttribute('height', cellSize - 1);
        rect.setAttribute('fill', getColor(d.v));
        rect.setAttribute('class', 'heatmap-cell');
        
        // 마우스 이벤트
        rect.addEventListener('mouseover', (e) => {{
            tooltip.innerHTML = `
                <strong>${{d.row}} vs ${{d.col}}</strong><br>
                Correlation: ${{d.v.toFixed(3)}}
            `;
            tooltip.style.display = 'block';
            tooltip.style.left = (e.pageX + 10) + 'px';
            tooltip.style.top = (e.pageY - 10) + 'px';
        }});
        
        rect.addEventListener('mouseout', () => {{
            tooltip.style.display = 'none';
        }});
        
        svg.appendChild(rect);
    }});
    
    // 라벨 추가
    heatmap_data.labels.forEach((label, i) => {{
        // X축 라벨
        const xLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        xLabel.setAttribute('x', i * cellSize + margin + cellSize/2);
        xLabel.setAttribute('y', margin - 10);
        xLabel.setAttribute('text-anchor', 'middle');
        xLabel.setAttribute('class', 'heatmap-label');
        xLabel.textContent = label.length > 10 ? label.substring(0, 10) + '...' : label;
        svg.appendChild(xLabel);
        
        // Y축 라벨
        const yLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        yLabel.setAttribute('x', margin - 10);
        yLabel.setAttribute('y', i * cellSize + margin + cellSize/2);
        yLabel.setAttribute('text-anchor', 'end');
        yLabel.setAttribute('dominant-baseline', 'middle');
        yLabel.setAttribute('class', 'heatmap-label');
        yLabel.textContent = label.length > 10 ? label.substring(0, 10) + '...' : label;
        svg.appendChild(yLabel);
    }});
    
    console.log('히트맵 생성 완료');
}} else {{
    document.getElementById('heatmapViz').innerHTML = 
        '<div style="text-align: center; padding: 50px; color: #666;">히트맵을 생성할 수치형 데이터가 부족합니다.</div>';
    console.warn('히트맵 데이터가 없음');
}}
"""

        return {
            "data_processing": data_processing,
            "html": html_template,
            "javascript": javascript_template
        }
    
    def _generate_gauge_chart_template(self, config: TemplateConfig) -> Dict[str, str]:
        """게이지 차트 템플릿"""
        
        colors = self.color_schemes.get(config.color_scheme, self.color_schemes["modern"])
        
        data_processing = f"""
# 게이지 차트 데이터 처리
gauge_data = {{}}

if 'main_data' in context_data and context_data['main_data']:
    df = pd.DataFrame(context_data['main_data'])
    
    field = '{config.data_fields[0] if config.data_fields else 'value'}'
    if field in df.columns:
        values = pd.to_numeric(df[field], errors='coerce').dropna()
        if len(values) > 0:
            current_value = values.mean()
            max_value = values.max()
            min_value = values.min()
            
            # 0-100 스케일로 정규화
            if max_value != min_value:
                normalized_value = ((current_value - min_value) / (max_value - min_value)) * 100
            else:
                normalized_value = 50
            
            gauge_data = {{
                'value': round(normalized_value, 1),
                'display_value': f'{{current_value:.2f}}',
                'field_name': field,
                'min': min_value,
                'max': max_value
            }}

print(f"게이지 차트 데이터 준비 완료: {{gauge_data.get('value', 0)}}%")
"""

        html_template = f"""
<div class="chart-container" id="gauge-container">
    <h3 class="chart-title">{config.title}</h3>
    <div id="gaugeChart" style="width: 100%; height: 300px; display: flex; justify-content: center; align-items: center;"></div>
</div>

<style>
.gauge-container {{
    position: relative;
    display: inline-block;
}}

.gauge-value {{
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -20%);
    font-size: 2rem;
    font-weight: bold;
    color: #333;
    text-align: center;
}}

.gauge-label {{
    position: absolute;
    top: 65%;
    left: 50%;
    transform: translate(-50%, 0);
    font-size: 1rem;
    color: #666;
    text-align: center;
}}
</style>
"""

        javascript_template = f"""
// 게이지 차트 생성
if (gauge_data && typeof gauge_data.value === 'number') {{
    const container = document.getElementById('gaugeChart');
    const size = 200;
    const strokeWidth = 20;
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const angle = (gauge_data.value / 100) * 180; // 반원 게이지
    
    container.innerHTML = `
        <div class="gauge-container">
            <svg width="${{size}}" height="${{size/2 + 50}}" style="transform: rotate(-90deg);">
                <!-- 배경 호 -->
                <path d="M ${{strokeWidth/2}} ${{size/2}} A ${{radius}} ${{radius}} 0 0 1 ${{size - strokeWidth/2}} ${{size/2}}"
                      stroke="#e0e0e0" stroke-width="${{strokeWidth}}" fill="none"/>
                <!-- 값 호 -->
                <path d="M ${{strokeWidth/2}} ${{size/2}} A ${{radius}} ${{radius}} 0 ${{angle > 90 ? 1 : 0}} 1 
                         ${{size/2 + radius * Math.cos((angle - 90) * Math.PI / 180)}} 
                         ${{size/2 + radius * Math.sin((angle - 90) * Math.PI / 180)}}"
                      stroke="{colors[0]}" stroke-width="${{strokeWidth}}" fill="none" stroke-linecap="round">
                    <animate attributeName="stroke-dasharray" 
                             from="0 ${{circumference/2}}" 
                             to="${{(circumference/2) * (gauge_data.value/100)}} ${{circumference/2}}"
                             dur="1.5s" fill="freeze"/>
                </path>
            </svg>
            <div class="gauge-value">${{gauge_data.display_value}}</div>
            <div class="gauge-label">${{gauge_data.field_name}}</div>
        </div>
    `;
    
    console.log('게이지 차트 생성 완료');
}} else {{
    document.getElementById('gaugeChart').innerHTML = 
        '<div style="text-align: center; padding: 50px; color: #666;">게이지 차트를 생성할 데이터가 없습니다.</div>';
    console.warn('게이지 데이터가 없음');
}}
"""

        return {
            "data_processing": data_processing,
            "html": html_template,
            "javascript": javascript_template
        }
    
    def _generate_radar_chart_template(self, config: TemplateConfig) -> Dict[str, str]:
        """레이더 차트 템플릿"""
        
        colors = self.color_schemes.get(config.color_scheme, self.color_schemes["modern"])
        
        data_processing = f"""
# 레이더 차트 데이터 처리
radar_data = {{}}

if 'main_data' in context_data and context_data['main_data']:
    df = pd.DataFrame(context_data['main_data'])
    
    # 수치형 컬럼 선택 (최대 8개)
    numeric_columns = df.select_dtypes(include=['number']).columns[:8]
    
    if len(numeric_columns) >= 3:
        # 각 컬럼을 0-100 스케일로 정규화
        normalized_data = []
        labels = []
        
        for col in numeric_columns:
            values = df[col].dropna()
            if len(values) > 0:
                # 평균값을 사용하고 정규화
                avg_value = values.mean()
                min_val, max_val = values.min(), values.max()
                
                if max_val != min_val:
                    normalized_value = ((avg_value - min_val) / (max_val - min_val)) * 100
                else:
                    normalized_value = 50
                
                normalized_data.append(round(normalized_value, 1))
                labels.append(col.replace('_', ' ').title())
        
        if len(labels) >= 3:
            radar_data = {{
                'labels': labels,
                'data': normalized_data
            }}

print(f"레이더 차트 데이터 준비 완료: {{len(radar_data.get('labels', []))}}개 축")
"""

        html_template = f"""
<div class="chart-container" id="radar-container">
    <h3 class="chart-title">{config.title}</h3>
    <canvas id="radarChart" style="width: 100%; height: 400px;"></canvas>
</div>
"""

        javascript_template = f"""
// 레이더 차트 생성
if (typeof Chart !== 'undefined' && radar_data && radar_data.labels) {{
    const radarCtx = document.getElementById('radarChart').getContext('2d');
    new Chart(radarCtx, {{
        type: 'radar',
        data: {{
            labels: radar_data.labels,
            datasets: [{{
                label: 'Performance Score',
                data: radar_data.data,
                borderColor: '{colors[0]}',
                backgroundColor: '{colors[0]}30',
                pointBackgroundColor: '{colors[0]}',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 7,
                borderWidth: 2
            }}]
        }},
        options: {{
            responsive: {str(config.responsive).lower()},
            maintainAspectRatio: false,
            animation: {{
                duration: {1500 if config.animation else 0}
            }},
            plugins: {{
                title: {{
                    display: true,
                    text: '{config.title}',
                    font: {{
                        size: 16,
                        weight: 'bold'
                    }}
                }},
                legend: {{
                    display: true,
                    position: 'top'
                }},
                tooltip: {{
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff'
                }}
            }},
            scales: {{
                r: {{
                    beginAtZero: true,
                    max: 100,
                    min: 0,
                    ticks: {{
                        stepSize: 20,
                        font: {{
                            size: 10
                        }}
                    }},
                    grid: {{
                        color: 'rgba(0,0,0,0.1)'
                    }},
                    angleLines: {{
                        color: 'rgba(0,0,0,0.1)'
                    }},
                    pointLabels: {{
                        font: {{
                            size: 12,
                            weight: 'bold'
                        }},
                        color: '#333'
                    }}
                }}
            }}
        }}
    }});
    console.log('레이더 차트 생성 완료');
}} else {{
    console.warn('레이더 차트 데이터가 없거나 Chart.js가 로드되지 않음');
}}
"""

        return {
            "data_processing": data_processing,
            "html": html_template,
            "javascript": javascript_template
        }
    
    def _generate_default_template(self, config: TemplateConfig) -> Dict[str, str]:
        """기본 템플릿"""
        
        return {
            "data_processing": "# 기본 데이터 처리\nprint('기본 템플릿 사용')",
            "html": f'<div class="section"><h3>{config.title}</h3><p>지원되지 않는 차트 타입입니다.</p></div>',
            "javascript": "console.log('기본 템플릿 실행');"
        }
    
    def get_available_templates(self) -> List[str]:
        """사용 가능한 템플릿 목록 반환"""
        return [vtype.value for vtype in VisualizationType]
    
    def get_color_schemes(self) -> Dict[str, List[str]]:
        """사용 가능한 색상 테마 반환"""
        return self.color_schemes.copy() 