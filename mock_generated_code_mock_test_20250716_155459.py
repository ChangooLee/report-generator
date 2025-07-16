
import json
import pandas as pd
from datetime import datetime
import os

print("📊 삼성생명 리포트 생성 중... (Mock)")

try:
    # 컨텍스트 데이터 로드
    with open('/tmp/context_mock_test_20250716_155459.json', 'r', encoding='utf-8') as f:
        context_data = json.load(f)
    
    print(f"✅ 데이터 로드 완료: {len(context_data)}개 항목")
    
    # 데이터 전처리 (Mock)

    # 데이터 로드 및 전처리
    import pandas as pd
    import json
    
    # 컨텍스트 데이터에서 메인 데이터 추출
    main_data = context_data.get('main_data', [])
    df = pd.DataFrame(main_data)
    
    # 기본 전처리
    if not df.empty:
        # 결측치 처리
        df = df.fillna(0)
        
        # 데이터 타입 변환
        numeric_columns = df.select_dtypes(include=['object']).columns
        for col in numeric_columns:
            try:
                df[col] = pd.to_numeric(df[col], errors='ignore')
            except:
                pass
    
    print(f"전처리 완료: {len(df)}개 레코드")
    
    
    # 분석 로직 (Mock)

    # 핵심 지표 계산
    key_metrics = {}
    
    if not df.empty:
        # 기본 통계
        region_col = df.columns[0] if len(df.columns) > 0 else 'value'
        
        try:
            key_metrics['total_records'] = len(df)
            key_metrics['total_value'] = df.select_dtypes(include=['number']).sum().sum()
            key_metrics['average_value'] = df.select_dtypes(include=['number']).mean().mean()
            key_metrics['performance_score'] = min(95, max(50, int(key_metrics['average_value'] / 10000 * 100)))
            key_metrics['growth_rate'] = 12.5  # 기본값
        except:
            key_metrics = {'total_records': len(df), 'performance_score': 75, 'growth_rate': 5.0}
    else:
        key_metrics = {'total_records': 0, 'performance_score': 0, 'growth_rate': 0}
    
    print(f"핵심 지표 계산 완료: {key_metrics}")
    
    
    # HTML 리포트 생성 (Mock)
    html_content = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>삼성생명 보험료 현황 분석 리포트</title>
    <link rel="stylesheet" href="/static/css/report.css">
    <script src="/static/js/chart.min.js"></script>
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
    </style>
</head>
<body>
    <div class="header">
        <img src="/static/images/samsung_life_logo.png" alt="삼성생명" class="logo">
        <h1>삼성생명 보험료 현황 분석 리포트</h1>
        <p>생성일: {datetime.now().strftime('%Y년 %m월 %d일')}</p>
    </div>
    
    <div class="container">
        <div class="section">
            <h2 class="section-title">주요 지표</h2>
            <div class="kpi-grid">
                <div class="kpi-card">
                    <h3>총 레코드 수</h3>
                    <div style="font-size: 2em; font-weight: bold; color: #1e3c72;">
                        {key_metrics.get('total_records', 0):,}
                    </div>
                </div>
                <div class="kpi-card">
                    <h3>성과 지수</h3>
                    <div style="font-size: 2em; font-weight: bold; color: #1e3c72;">
                        {key_metrics.get('performance_score', 0)}%
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <footer style="text-align: center; margin-top: 50px; padding: 20px; color: #666;">
        <p>본 리포트는 AI 기반 분석 시스템에 의해 생성되었습니다. (Mock 버전)</p>
        <p>© 2024 Samsung Life Insurance. All rights reserved.</p>
    </footer>
</body>
</html>'''
    
    # 리포트 파일 저장
    report_filename = f"./reports/report_mock_test_20250716_155459.html"
    os.makedirs("./reports", exist_ok=True)
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Mock 리포트 생성 완료: {report_filename}")
    
except Exception as e:
    print(f"❌ Mock 리포트 생성 실패: {e}")
    raise
