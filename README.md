# 🤖 AI 리포트 생성기

OpenRouter API를 활용한 AI 기반 대화형 리포트 생성 서비스입니다. 자연어로 요청하면 AI가 인터랙티브한 HTML 리포트를 자동으로 생성합니다.

## ✨ 주요 기능

- **🗣️ 자연어 요청**: 복잡한 설정 없이 자연어로 리포트를 요청
- **🎨 인터랙티브 차트**: Chart.js, D3.js, Plotly.js를 활용한 동적 시각화
- **🔄 MCP 서버 연동**: stdio 기반 MCP 서버와 연동하여 다양한 데이터 소스 활용
- **🛡️ 안전한 실행 환경**: 격리된 환경에서 코드 실행 및 보안 검증
- **📱 반응형 디자인**: 모바일과 데스크톱 모두 지원
- **🌐 웹 인터페이스**: 직관적인 웹 UI 제공
- **🔌 RESTful API**: 프로그래밍 방식 접근 가능

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   웹 브라우저    │────│   Nginx 프록시   │────│  FastAPI 서버   │
│   (포트 7080)   │    │   (정적 파일)    │    │   (포트 7000)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐              │
                       │  OpenRouter AI  │──────────────┘
                       │  - Qwen2.5-Coder│
                       │  - Claude 3.5   │
                       └─────────────────┘
                                                        │
                       ┌─────────────────┐              │
                       │   MCP 서버들    │──────────────┘
                       │   (stdio 연동)  │
                       └─────────────────┘
```

## 🚀 빠른 시작

### 1. 사전 요구사항

- Docker & Docker Compose
- OpenRouter API 키
- 7000번, 7080번 포트 사용 가능

### 2. 설치 및 설정

```bash
# 1. 저장소 클론 (또는 파일 다운로드)
git clone <repository-url>
cd report-generator

# 2. 초기 설정 실행
bash scripts/setup.sh

# 3. 환경 변수 설정
# .env 파일에서 OpenRouter API 키 설정
vim .env  # 또는 원하는 에디터로 편집

# 4. 서비스 시작
bash scripts/start.sh
```

### 3. 접속

- 🌐 **웹 인터페이스**: http://localhost:7080
- 📚 **API 문서**: http://localhost:7080/api/docs
- 📊 **생성된 리포트**: http://localhost:7080/reports/

## 🔧 설정

### 환경 변수

```bash
# OpenRouter API 설정 (메인 코드 생성용)
VLLM_API_BASE_URL=https://openrouter.ai/api/v1
VLLM_API_KEY=your-openrouter-api-key
VLLM_MODEL_NAME=Qwen/Qwen2.5-Coder-32B-Instruct

# Claude API 설정 (코드 수정 및 개선용)
CLAUDE_API_BASE_URL=https://openrouter.ai/api/v1
CLAUDE_API_KEY=your-openrouter-api-key
CLAUDE_MODEL_NAME=anthropic/claude-3.5-sonnet

# 서비스 포트
API_PORT=7000
NGINX_PORT=7080

# 보안 설정
MAX_EXECUTION_TIME=300
MAX_CODE_SIZE=10000
```

### MCP 서버 설정

MCP 서버는 stdio 기반으로 연동됩니다:

```python
# MCP 서버 등록 예시
mcp_client.register_server(
    name="my_server",
    command="/path/to/mcp/server",
    args=["--stdio"],
    env={"ENV_VAR": "value"}
)
```

## 💡 사용법

### 웹 인터페이스

1. 브라우저에서 http://localhost:7080 접속
2. 텍스트 박스에 원하는 리포트 내용을 자연어로 입력
3. "리포트 생성하기" 버튼 클릭
4. 생성된 HTML 리포트 확인

### API 사용

```python
import requests

# 리포트 생성 요청
response = requests.post("http://localhost:7000/generate-report", json={
    "user_query": "월별 매출 추이를 선 그래프로 보여주세요",
    "session_id": "my_session_123"
})

result = response.json()
if result["success"]:
    print(f"리포트 URL: {result['report_url']}")
```

### 예시 요청

- "월별 매출 추이를 선 그래프로 보여주세요"
- "고객 연령대별 구매 패턴을 분석해주세요"
- "제품 카테고리별 판매량을 파이 차트로 표현해주세요"
- "지역별 매출 현황을 대시보드로 만들어주세요"

## 🏗️ 프로젝트 구조

```
report-generator/
├── app/                        # 메인 애플리케이션
│   ├── main.py                 # FastAPI 메인 앱
│   ├── orchestrator.py         # 전체 로직 오케스트레이터
│   ├── llm_client.py          # OpenRouter API 클라이언트
│   ├── mcp_client.py          # MCP 서버 연동
│   ├── code_executor.py       # 안전한 코드 실행
│   └── utils/                 # 유틸리티 모듈
│       ├── templates.py       # 프롬프트 템플릿
│       └── security.py        # 보안 검증
├── docker/                    # Docker 설정
│   ├── app.Dockerfile         # 애플리케이션 Dockerfile
│   └── nginx.Dockerfile       # Nginx Dockerfile
├── config/                    # 설정 파일
│   └── nginx.conf            # Nginx 설정
├── static/                    # 정적 파일
│   ├── index.html            # 웹 인터페이스
│   ├── css/                  # 스타일시트
│   └── js/                   # JavaScript 라이브러리
├── scripts/                   # 스크립트
│   ├── setup.sh              # 초기 설정
│   └── start.sh              # 서비스 시작
├── data/                     # 데이터
│   └── mcp_bundles/          # 샘플 데이터
├── reports/                  # 생성된 리포트
├── docker-compose.yml        # Docker Compose 설정
├── requirements.txt          # Python 의존성
└── README.md                # 이 파일
```

## 🔐 보안 기능

- **코드 실행 격리**: 별도 프로세스에서 코드 실행
- **입력 검증**: 사용자 입력 및 생성된 코드 보안 검증
- **시간 제한**: 코드 실행 시간 제한 (기본 300초)
- **파일 시스템 보호**: 안전한 경로만 접근 허용
- **HTML 검증**: 생성된 HTML의 XSS 방지

## 🔄 MCP 서버 연동

이 시스템은 stdio 기반 MCP 서버와 연동하여 다양한 데이터 소스를 활용할 수 있습니다:

- 파일 시스템 접근
- 데이터베이스 연결
- API 호출
- 웹 스크래핑
- 문서 처리

## 🐛 문제 해결

### 일반적인 문제

1. **API 키 오류**
   ```bash
   # .env 파일의 API 키 확인
   cat .env | grep API_KEY
   ```

2. **포트 충돌**
   ```bash
   # 포트 사용 중인 프로세스 확인
   lsof -i :7000
   lsof -i :7080
   ```

3. **Docker 문제**
   ```bash
   # 컨테이너 로그 확인
   docker-compose logs -f
   
   # 컨테이너 재시작
   docker-compose restart
   ```

### 로그 확인

```bash
# 실시간 로그 모니터링
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs app
docker-compose logs nginx
```

## 🔧 개발

### 개발 환경 설정

```bash
# Python 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 7000
```

### 코드 기여

1. Fork 저장소
2. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 Push (`git push origin feature/amazing-feature`)
5. Pull Request 생성

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 지원

문제가 발생하거나 질문이 있으면:

1. [GitHub Issues](https://github.com/your-repo/issues)에 문제 등록
2. 문서를 다시 확인
3. 로그 파일 검토

---

**⭐ 이 프로젝트가 유용하다면 스타를 눌러주세요!** 