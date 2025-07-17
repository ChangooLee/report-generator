#!/bin/bash

echo "🚀 Report Generator 설정을 시작합니다..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수 정의
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. 환경 변수 파일 확인 및 생성
print_status "환경 변수 파일을 확인합니다..."
if [ ! -f .env ]; then
    print_warning ".env 파일이 없습니다. 템플릿을 생성합니다..."
    
    cat > .env << 'EOF'
# 서비스 설정
API_HOST=0.0.0.0
API_PORT=7000
NGINX_PORT=7080

# OpenRouter API 설정 (메인 코드 생성용)
VLLM_API_BASE_URL=https://openrouter.ai/api/v1
VLLM_API_KEY=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
VLLM_MODEL_NAME=Qwen/Qwen2.5-Coder-32B-Instruct

# Claude API 설정 (코드 수정 및 개선용)
CLAUDE_API_BASE_URL=https://openrouter.ai/api/v1
CLAUDE_API_KEY=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
CLAUDE_MODEL_NAME=anthropic/claude-sonnet-4

# 경로 설정
DATA_PATH=/app/data
REPORTS_PATH=/app/reports
STATIC_PATH=/app/static
TEMPLATES_PATH=/app/templates
MCP_SERVER_PATH=/app/mcp_servers

# 보안 설정
SECRET_KEY=your-secret-key-here-please-change-this-in-production
MAX_EXECUTION_TIME=300
MAX_CODE_SIZE=10000

# MCP 설정
MCP_STDIO_ENABLED=true

# 로깅 설정
LOG_LEVEL=INFO

# Docker 설정
DOCKER_NETWORK=report-net
EOF
    
    print_success ".env 파일이 생성되었습니다."
    print_warning "⚠️  .env 파일의 API 키를 실제 값으로 변경해주세요!"
else
    print_success ".env 파일이 이미 존재합니다."
fi

# 2. 디렉토리 생성
print_status "필요한 디렉토리를 생성합니다..."
mkdir -p data/mcp_bundles
mkdir -p data/schemas
mkdir -p reports
mkdir -p static/js
mkdir -p static/css
mkdir -p static/fonts
mkdir -p templates
mkdir -p config
mkdir -p mcp_servers
mkdir -p docker

print_success "디렉토리 생성이 완료되었습니다."

# 3. Chart.js 다운로드
print_status "Chart.js 라이브러리를 다운로드합니다..."
if [ ! -f static/js/chart.min.js ]; then
    curl -L https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.min.js -o static/js/chart.min.js --silent
    if [ $? -eq 0 ]; then
        print_success "Chart.js 다운로드 완료"
    else
        print_error "Chart.js 다운로드 실패"
    fi
else
    print_success "Chart.js가 이미 존재합니다."
fi

# 4. D3.js 다운로드  
print_status "D3.js 라이브러리를 다운로드합니다..."
if [ ! -f static/js/d3.min.js ]; then
    curl -L https://d3js.org/d3.v7.min.js -o static/js/d3.min.js --silent
    if [ $? -eq 0 ]; then
        print_success "D3.js 다운로드 완료"
    else
        print_error "D3.js 다운로드 실패"
    fi
else
    print_success "D3.js가 이미 존재합니다."
fi

# 5. Plotly.js 다운로드
print_status "Plotly.js 라이브러리를 다운로드합니다..."
if [ ! -f static/js/plotly.min.js ]; then
    curl -L https://cdn.plot.ly/plotly-2.27.0.min.js -o static/js/plotly.min.js --silent
    if [ $? -eq 0 ]; then
        print_success "Plotly.js 다운로드 완료"
    else
        print_error "Plotly.js 다운로드 실패"
    fi
else
    print_success "Plotly.js가 이미 존재합니다."
fi

# 6. 기본 CSS 생성
print_status "기본 스타일을 생성합니다..."
if [ ! -f static/css/report.css ]; then
    cat > static/css/report.css << 'EOF'
/* 리포트 기본 스타일 */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 0;
    padding: 20px;
    background-color: #f8f9fa;
    line-height: 1.6;
}

.report-container {
    max-width: 1200px;
    margin: 0 auto;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    padding: 30px;
}

.report-title {
    color: #2c3e50;
    border-bottom: 3px solid #3498db;
    padding-bottom: 15px;
    margin-bottom: 30px;
    font-size: 2.5em;
    font-weight: 300;
}

.chart-container {
    margin: 30px 0;
    padding: 25px;
    background: #fafafa;
    border-radius: 8px;
    border-left: 4px solid #3498db;
}

.chart-title {
    font-size: 1.4em;
    font-weight: 600;
    color: #34495e;
    margin-bottom: 20px;
}

.insight-box {
    background: linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%);
    border: 1px solid #d4edda;
    border-radius: 8px;
    padding: 20px;
    margin: 25px 0;
    border-left: 5px solid #28a745;
}

.insight-title {
    font-weight: 600;
    color: #155724;
    font-size: 1.2em;
    margin-bottom: 10px;
}

.metric-card {
    display: inline-block;
    background: white;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 25px;
    margin: 15px;
    min-width: 180px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transition: transform 0.2s ease;
}

.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(0,0,0,0.15);
}

.metric-value {
    font-size: 2.5em;
    font-weight: bold;
    color: #2980b9;
    margin-bottom: 8px;
}

.metric-label {
    color: #7f8c8d;
    font-size: 1.1em;
    font-weight: 500;
}

.table-container {
    overflow-x: auto;
    margin: 25px 0;
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.data-table th {
    background: #34495e;
    color: white;
    padding: 15px;
    text-align: left;
    font-weight: 600;
}

.data-table td {
    padding: 12px 15px;
    border-bottom: 1px solid #f1f2f6;
}

.data-table tr:hover {
    background: #f8f9fa;
}

.summary-section {
    background: #e3f2fd;
    border-radius: 8px;
    padding: 25px;
    margin: 30px 0;
    border-left: 5px solid #2196f3;
}

.footer {
    margin-top: 40px;
    padding-top: 20px;
    border-top: 2px solid #e9ecef;
    text-align: center;
    color: #6c757d;
    font-size: 0.9em;
}

/* 반응형 디자인 */
@media (max-width: 768px) {
    .report-container {
        padding: 20px;
        margin: 10px;
    }
    
    .metric-card {
        display: block;
        margin: 10px 0;
        min-width: auto;
    }
    
    .report-title {
        font-size: 2em;
    }
    
    .chart-container {
        padding: 15px;
    }
}

/* 차트 스타일 */
canvas {
    max-width: 100%;
    height: auto;
}

/* 로딩 애니메이션 */
.loading {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 200px;
}

.spinner {
    border: 4px solid #f3f3f3;
    border-top: 4px solid #3498db;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
EOF
    print_success "기본 CSS 파일이 생성되었습니다."
else
    print_success "CSS 파일이 이미 존재합니다."
fi

# 7. 샘플 데이터 생성
print_status "샘플 데이터를 생성합니다..."
if [ ! -f data/mcp_bundles/sales_data.json ]; then
    cat > data/mcp_bundles/sales_data.json << 'EOF'
[
  {
    "date": "2024-01-01",
    "product": "Product A",
    "sales": 1500,
    "revenue": 45000,
    "region": "Seoul",
    "category": "Electronics"
  },
  {
    "date": "2024-01-01",
    "product": "Product B", 
    "sales": 800,
    "revenue": 32000,
    "region": "Busan",
    "category": "Clothing"
  },
  {
    "date": "2024-02-01",
    "product": "Product A",
    "sales": 1800,
    "revenue": 54000,
    "region": "Seoul",
    "category": "Electronics"
  },
  {
    "date": "2024-02-01",
    "product": "Product B",
    "sales": 950,
    "revenue": 38000,
    "region": "Busan", 
    "category": "Clothing"
  },
  {
    "date": "2024-03-01",
    "product": "Product A",
    "sales": 2100,
    "revenue": 63000,
    "region": "Seoul",
    "category": "Electronics"
  },
  {
    "date": "2024-03-01",
    "product": "Product B",
    "sales": 1200,
    "revenue": 48000,
    "region": "Busan",
    "category": "Clothing"
  }
]
EOF
    print_success "샘플 매출 데이터가 생성되었습니다."
else
    print_success "샘플 데이터가 이미 존재합니다."
fi

# 8. 실행 권한 부여
print_status "스크립트 실행 권한을 설정합니다..."
chmod +x scripts/*.sh 2>/dev/null || true
print_success "실행 권한 설정 완료"

# 9. Docker 네트워크 생성
print_status "Docker 네트워크를 확인합니다..."
if command -v docker &> /dev/null; then
    if ! docker network ls | grep -q "report-net"; then
        docker network create report-net 2>/dev/null || true
        print_success "Docker 네트워크 'report-net'이 생성되었습니다."
    else
        print_success "Docker 네트워크가 이미 존재합니다."
    fi
else
    print_warning "Docker가 설치되어 있지 않습니다."
fi

# 10. 설정 완료 메시지
echo ""
print_success "✅ 설정이 완료되었습니다!"
echo ""
echo -e "${BLUE}📋 다음 단계:${NC}"
echo "1. .env 파일에서 OpenRouter API 키를 실제 값으로 변경"
echo "2. docker-compose up -d 실행하여 서비스 시작"
echo "3. http://localhost:7080 에서 웹 인터페이스 확인"
echo ""
echo -e "${BLUE}🌐 서비스 URL:${NC}"
echo "  - 웹 인터페이스: http://localhost:7080"
echo "  - API 문서: http://localhost:7080/api/docs"
echo "  - 헬스체크: http://localhost:7080/health"
echo ""
echo -e "${YELLOW}⚠️  주의사항:${NC}"
echo "  - OpenRouter API 키가 설정되어야 정상 작동합니다"
echo "  - 7000번 및 7080번 포트가 사용 가능해야 합니다"
echo "" 