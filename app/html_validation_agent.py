"""
HTML Validation and Browser Testing Agent
HTML 검증 및 브라우저 테스트 전문 에이전트
"""

import os
import subprocess
import tempfile
import webbrowser
from typing import Dict, Any, List
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """HTML 검증 결과"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]


class HTMLValidationAgent:
    """HTML 검증 및 브라우저 테스트 전문 에이전트"""
    
    def __init__(self):
        pass
    
    def validate_html_structure(self, html_content: str) -> ValidationResult:
        """HTML 구조 검증"""
        errors = []
        warnings = []
        suggestions = []
        
        # 기본 HTML 구조 체크
        if not html_content.strip().startswith('<!DOCTYPE'):
            errors.append("DOCTYPE 선언이 없습니다")
        
        if '<html' not in html_content:
            errors.append("html 태그가 없습니다")
        
        if '<head>' not in html_content:
            errors.append("head 태그가 없습니다")
            
        if '<body>' not in html_content:
            errors.append("body 태그가 없습니다")
        
        # 메타 태그 체크
        if 'charset=' not in html_content:
            warnings.append("문자 인코딩이 지정되지 않았습니다")
        
        if 'viewport' not in html_content:
            warnings.append("반응형 viewport 메타태그가 없습니다")
        
        # 차트 라이브러리 체크
        if 'chart' in html_content.lower():
            if 'chart.js' not in html_content and 'chartjs' not in html_content:
                errors.append("Chart.js 라이브러리가 포함되지 않았습니다")
            elif 'cdn' not in html_content and 'https://' not in html_content:
                warnings.append("Chart.js가 로컬 파일로 참조되어 있습니다. CDN 사용을 권장합니다")
        
        # Python 코드가 HTML에 섞여있는지 체크
        if 'import ' in html_content or 'def ' in html_content:
            errors.append("HTML에 Python 코드가 섞여있습니다")
        
        # 완료되지 않은 태그 체크
        if html_content.count('<script>') != html_content.count('</script>'):
            errors.append("script 태그가 제대로 닫히지 않았습니다")
        
        # 개선 제안
        if errors:
            suggestions.append("HTML 구조를 완전히 재생성해야 합니다")
        elif warnings:
            suggestions.append("브라우저 호환성을 위해 경고사항을 수정하세요")
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def test_in_browser(self, html_content: str, auto_open: bool = False) -> Dict[str, Any]:
        """브라우저에서 HTML 테스트"""
        
        try:
            # 임시 파일 생성
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html_content)
                temp_path = f.name
            
            # 브라우저에서 열기 (선택적)
            if auto_open:
                webbrowser.open(f'file://{temp_path}')
                logger.info(f"브라우저에서 테스트 파일 열기: {temp_path}")
            
            return {
                "success": True,
                "temp_file_path": temp_path,
                "browser_url": f"file://{temp_path}",
                "message": "HTML 파일이 생성되었습니다"
            }
            
        except Exception as e:
            logger.error(f"브라우저 테스트 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "브라우저 테스트 실패"
            }
    
    def generate_improvement_suggestions(self, validation_result: ValidationResult, html_content: str) -> List[str]:
        """개선 제안 생성"""
        
        suggestions = []
        
        if not validation_result.is_valid:
            suggestions.append("🔥 긴급: HTML 구조가 잘못되었습니다. 완전히 재생성이 필요합니다.")
        
        if 'chart' in html_content.lower() and validation_result.errors:
            suggestions.append("📊 차트를 제대로 표시하려면 Chart.js CDN을 추가하세요:")
            suggestions.append("   <script src='https://cdn.jsdelivr.net/npm/chart.js'></script>")
        
        if '예시' in html_content or '가정' in html_content:
            suggestions.append("📋 실제 데이터를 사용하여 리포트를 재생성하세요")
        
        if 'def ' in html_content or 'import ' in html_content:
            suggestions.append("🧹 HTML에서 Python 코드를 제거하고 순수 HTML로 만드세요")
        
        if validation_result.warnings:
            suggestions.append("⚠️ 브라우저 호환성을 위해 다음 경고사항들을 수정하세요:")
            for warning in validation_result.warnings:
                suggestions.append(f"   - {warning}")
        
        return suggestions
    
    def create_perfect_html_template(self, data: Dict[str, Any]) -> str:
        """완벽한 HTML 템플릿 생성"""
        
        # 실제 데이터 추출
        raw_data = data.get('raw_data', {})
        june_stats = raw_data.get('june_2025', {}).get('overallStatistics', {})
        july_stats = raw_data.get('july_2025', {}).get('overallStatistics', {})
        
        june_count = june_stats.get('transactionCount', 0)
        july_count = july_stats.get('transactionCount', 0)
        june_amount = june_stats.get('totalAmount', 0)
        july_amount = july_stats.get('totalAmount', 0)
        june_avg = june_stats.get('averagePrice', 0)
        july_avg = july_stats.get('averagePrice', 0)
        
        # 변화율 계산
        count_change = ((july_count - june_count) / june_count * 100) if june_count > 0 else 0
        amount_change = ((july_amount - june_amount) / june_amount * 100) if june_amount > 0 else 0
        avg_change = ((july_avg - june_avg) / june_avg * 100) if june_avg > 0 else 0
        
        html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>강남구 상업업무용 부동산 실거래 분석 리포트 (2025년 6-7월)</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Noto Sans KR', sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header p {{
            font-size: 1.2rem;
            opacity: 0.9;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-number {{
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.9rem;
        }}
        
        .stat-change {{
            font-size: 0.8rem;
            margin-top: 5px;
            padding: 5px 10px;
            border-radius: 15px;
            display: inline-block;
        }}
        
        .positive {{
            background: #d4edda;
            color: #155724;
        }}
        
        .negative {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .section {{
            background: white;
            margin-bottom: 30px;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        
        .section h2 {{
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.8rem;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 20px 0;
        }}
        
        .insight-box {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        
        .insight-box h3 {{
            color: #495057;
            margin-bottom: 10px;
        }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9rem;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 2rem;
            }}
            
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>강남구 상업업무용 부동산 실거래 분석 리포트</h1>
            <p>2025년 6월 - 7월 실제 거래 데이터 기반 분석</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{june_count:,}</div>
                <div class="stat-label">6월 거래 건수</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{july_count:,}</div>
                <div class="stat-label">7월 거래 건수</div>
                <div class="stat-change {'positive' if count_change >= 0 else 'negative'}">
                    {count_change:+.1f}%
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{june_amount:,.0f}억</div>
                <div class="stat-label">6월 총 거래액</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{july_amount:,.0f}억</div>
                <div class="stat-label">7월 총 거래액</div>
                <div class="stat-change {'positive' if amount_change >= 0 else 'negative'}">
                    {amount_change:+.1f}%
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 거래량 변화 추이</h2>
            <div class="chart-container">
                <canvas id="volumeChart"></canvas>
            </div>
        </div>
        
        <div class="section">
            <h2>💰 거래액 변화 추이</h2>
            <div class="chart-container">
                <canvas id="amountChart"></canvas>
            </div>
        </div>
        
        <div class="section">
            <h2>📈 평균 거래가 분석</h2>
            <div class="chart-container">
                <canvas id="avgPriceChart"></canvas>
            </div>
            
            <div class="insight-box">
                <h3>💡 주요 인사이트</h3>
                <p><strong>평균 거래가 변화:</strong> {avg_change:+.1f}% ({june_avg:.1f}억 → {july_avg:.1f}억)</p>
                <p><strong>시장 온도:</strong> {'상승세' if avg_change > 0 else '하락세' if avg_change < 0 else '보합세'}</p>
            </div>
        </div>
        
        <div class="section">
            <h2>🎯 투자 전략 및 전망</h2>
            <div class="insight-box">
                <h3>📋 단기 전략 (1-3개월)</h3>
                <p>거래량 {'증가' if count_change > 0 else '감소'}와 평균가격 {'상승' if avg_change > 0 else '하락'}을 고려한 신중한 접근 필요</p>
            </div>
            
            <div class="insight-box">
                <h3>🔮 중기 전망 (3-12개월)</h3>
                <p>강남구 상업업무용 부동산 시장의 지속적인 모니터링과 시장 변화에 따른 전략 조정 권장</p>
            </div>
        </div>
        
        <div class="footer">
            <p>본 리포트는 실제 MCP 부동산 거래 데이터를 기반으로 생성되었습니다. (생성일: {data.get('collection_time', 'N/A')})</p>
        </div>
    </div>
    
    <script>
        // 거래량 차트
        const volumeCtx = document.getElementById('volumeChart').getContext('2d');
        new Chart(volumeCtx, {{
            type: 'bar',
            data: {{
                labels: ['2025년 6월', '2025년 7월'],
                datasets: [{{
                    label: '거래 건수',
                    data: [{june_count}, {july_count}],
                    backgroundColor: [
                        'rgba(102, 126, 234, 0.8)',
                        'rgba(118, 75, 162, 0.8)'
                    ],
                    borderColor: [
                        'rgba(102, 126, 234, 1)',
                        'rgba(118, 75, 162, 1)'
                    ],
                    borderWidth: 2,
                    borderRadius: 5
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    title: {{
                        display: true,
                        text: '월별 거래 건수',
                        font: {{
                            size: 16,
                            weight: 'bold'
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: '건수'
                        }}
                    }}
                }}
            }}
        }});
        
        // 거래액 차트
        const amountCtx = document.getElementById('amountChart').getContext('2d');
        new Chart(amountCtx, {{
            type: 'line',
            data: {{
                labels: ['2025년 6월', '2025년 7월'],
                datasets: [{{
                    label: '총 거래액 (억원)',
                    data: [{june_amount}, {july_amount}],
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    title: {{
                        display: true,
                        text: '월별 총 거래액 추이',
                        font: {{
                            size: 16,
                            weight: 'bold'
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: '억원'
                        }}
                    }}
                }}
            }}
        }});
        
        // 평균 거래가 차트
        const avgPriceCtx = document.getElementById('avgPriceChart').getContext('2d');
        new Chart(avgPriceCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['6월 평균', '7월 평균'],
                datasets: [{{
                    data: [{june_avg}, {july_avg}],
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(75, 192, 192, 0.8)'
                    ],
                    borderColor: [
                        'rgba(255, 99, 132, 1)',
                        'rgba(75, 192, 192, 1)'
                    ],
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }},
                    title: {{
                        display: true,
                        text: '월별 평균 거래가 비교 (억원)',
                        font: {{
                            size: 16,
                            weight: 'bold'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        
        return html_template 