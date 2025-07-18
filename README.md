# AI 리포트 생성 시스템

> LangGraph 기반 AI 에이전트를 활용한 동적 데이터 분석 및 HTML 리포트 자동 생성 플랫폼

MCP(Model Context Protocol) 도구와 Chart.js를 활용하여 다양한 데이터를 자동으로 분석하고 전문적인 HTML 웹 리포트를 생성하는 시스템입니다.

## 🎯 프로젝트 개요

자연어 질의를 통해 AI 에이전트가 적절한 도구를 선택하고 데이터를 분석하여 동적으로 HTML 리포트를 생성합니다.

### 주요 특징
- **에이전틱 워크플로우**: LangGraph 기반 AI 에이전트 자동화
- **동적 도구 선택**: 질의에 따른 MCP 도구 자동 매칭
- **유연한 시각화**: Chart.js 기반 다양한 차트 자동 생성
- **스트리밍 인터페이스**: 처리 과정과 결과를 실시간 전송
- **반응형 디자인**: 모바일, 태블릿, 데스크톱 최적화
- **완전 오프라인**: 외부 CDN 의존성 없음

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   자연어 질의    │───▶│   AI 에이전트     │───▶│   Claude 모델    │
│                │    │   (LangGraph)    │    │                │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Nginx 서버    │◀───│  동적 HTML 리포트 │◀───│  MCP 도구 실행   │
│  (리포트 호스팅) │    │                 │    │   (데이터 처리)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📁 프로젝트 구조

```
report-generator/
├── README.md
├── docker-compose.yml
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI 메인 애플리케이션
│   ├── orchestrator.py             # 전체 로직 오케스트레이션
│   ├── streaming_api.py            # 스트리밍 API 엔드포인트
│   ├── langgraph_workflow.py       # LangGraph 에이전트 워크플로우
│   ├── llm_client.py              # OpenRouter API 클라이언트
│   ├── mcp_client.py              # MCP 서버 연동
│   ├── agentic_html_generator.py  # 에이전틱 HTML 생성기
│   ├── code_executor.py           # 안전한 코드 실행 환경
│   └── utils/
│       ├── __init__.py
│       ├── security.py            # 보안 검증 모듈
│       └── templates.py           # 프롬프트 템플릿
├── data/
│   └── mcp_bundles/               # MCP JSON 데이터 번들들
├── static/
│   ├── images/                    # 이미지 리소스
│   ├── js/
│   │   ├── chart.min.js          # Chart.js 라이브러리
│   │   ├── d3.min.js             # D3.js 라이브러리
│   │   └── plotly.min.js         # Plotly.js 라이브러리
│   ├── css/
│   │   └── report.css            # 리포트 스타일
│   └── fonts/                    # 오프라인 폰트
├── reports/                      # 생성된 리포트 저장소
├── docker/
│   ├── app.Dockerfile            # 메인 애플리케이션
│   └── nginx.Dockerfile          # Nginx 웹서버
└── config/
    └── nginx.conf                # Nginx 설정
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/ChangooLee/report-generator.git
cd report-generator

# 환경 설정 스크립트 실행
chmod +x scripts/setup.sh
./scripts/setup.sh

# 환경 변수 설정 (.env 파일 수정)
cp .env.example .env
# .env 파일에서 API 키 설정
```

### 2. 서비스 시작

```bash
# 도커 컴포즈로 전체 서비스 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f app
```

### 3. 리포트 생성 테스트

```bash
# 웹 인터페이스 접속
open http://localhost:7080

# 또는 API 직접 호출
curl -X POST "http://localhost:7000/generate-report" \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "데이터 분석 리포트를 만들어주세요",
    "session_id": "test_001"
  }'
```

## 💡 사용 방법

### 웹 인터페이스 (권장)

1. 브라우저에서 `http://localhost:7080` 접속
2. 텍스트 박스에 원하는 리포트 내용을 자연어로 입력
3. "리포트 생성하기" 버튼 클릭
4. 생성된 HTML 리포트 확인

### API 직접 사용

```python
import requests

# 리포트 생성 요청
response = requests.post("http://localhost:7000/generate-report", json={
    "user_query": "월별 데이터 트렌드 분석 리포트",
    "session_id": "analysis_001",
    "data_sources": ["sample_data"]
})

result = response.json()
if result["success"]:
    print(f"리포트 생성 완료: {result['report_url']}")
    print(f"처리 시간: {result['processing_time']:.2f}초")
```

### 예시 요청

**일반적인 데이터 분석**:
- "월별 트렌드 분석과 패턴 인식 리포트"
- "카테고리별 성과 비교 분석"
- "시계열 데이터의 계절성 패턴 분석"
- "통계적 요약과 주요 지표 계산"

**시각화 중심**:
- "차트와 그래프로 데이터 시각화"
- "분포 분석과 상관관계 탐색"
- "KPI 대시보드 스타일 리포트"

## 🎨 리포트 구조

### 표준 리포트 구성
1. **헤더**: 제목 + 생성일시
2. **요약**: 핵심 발견사항 요약
3. **주요 지표**: 시각적 메트릭 카드
4. **상세 분석**: 섹션별 심층 분석
5. **데이터 시각화**: 인터랙티브 차트 및 그래프
6. **인사이트**: 주요 발견사항과 권장사항
7. **푸터**: 생성정보

### 컬러 팔레트
- **주요**: `#3b82f6` (블루)
- **보조**: `#6366f1` (인디고)
- **성공**: `#10b981` (그린)
- **경고**: `#f59e0b` (앰버)
- **배경**: `#f8fafc` (그레이 50)

### 타이포그래피
- **메인 폰트**: system-ui, -apple-system, sans-serif
- **크기 계층**: H1(2.5rem) > H2(1.875rem) > H3(1.25rem) > Body(1rem)

## 🔧 개발 및 커스터마이징

### 새로운 도구 추가

```python
# MCP 서버에 새로운 도구 추가
@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="your_new_tool",
            description="새로운 도구 설명",
            inputSchema={
                "type": "object",
                "properties": {
                    "parameter": {"type": "string"}
                }
            }
        )
    ]
```

### 차트 템플릿 수정

```python
# app/agentic_html_generator.py에서 차트 생성 로직 수정
def _create_custom_chart(self, data, chart_type):
    # 새로운 차트 유형 구현
    pass
```

### 스타일 수정

```css
/* static/css/report.css에서 스타일 커스터마이징 */
.report-container {
    /* 리포트 컨테이너 스타일 수정 */
}
```

## 🔒 보안 및 컴플라이언스

### 보안 기능
- **코드 검증**: 위험한 함수 및 파일 시스템 접근 차단
- **XSS 방지**: 모든 사용자 입력 이스케이핑
- **경로 제한**: 허용된 디렉토리만 접근 가능
- **네트워크 격리**: 외부 API 호출 제한

### 데이터 보호
- **로컬 처리**: 모든 데이터 로컬에서 처리
- **세션 관리**: 세션 기반 데이터 격리
- **로그 관리**: 민감 정보 로깅 방지

## 🚀 성능 최적화

### 시스템 요구사항
- **CPU**: 4코어 이상 권장
- **메모리**: 8GB 이상
- **저장공간**: 10GB 이상
- **네트워크**: 초기 설정 시에만 필요

### 최적화 설정
```yaml
# docker-compose.yml에서 리소스 제한 설정
services:
  app:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
```

## 🛠️ 트러블슈팅

### 일반적인 문제

**1. 리포트 생성 실패**
```bash
# 로그 확인
docker-compose logs app

# 환경 확인
docker-compose exec app python -c "import requests; print('OK')"
```

**2. 차트가 표시되지 않음**
- Chart.js 라이브러리 경로 확인: `/static/js/chart.min.js`
- 브라우저 개발자 도구에서 JavaScript 오류 확인

**3. MCP 도구 연결 실패**
- MCP 서버 상태 확인
- 네트워크 연결 상태 확인

## 📈 확장 계획

### 단기 목표 (1-3개월)
- [ ] 다양한 데이터 소스 지원 (CSV, Excel, API)
- [ ] 실시간 데이터 연동
- [ ] 사용자 대시보드 개발
- [ ] 리포트 스케줄링 기능

### 중기 목표 (3-6개월)
- [ ] 다국어 리포트 지원
- [ ] 고급 ML 분석 모듈 통합
- [ ] 리포트 템플릿 라이브러리
- [ ] 모바일 앱 개발

### 장기 목표 (6-12개월)
- [ ] 엔터프라이즈 SSO 통합
- [ ] 클라우드 배포 지원
- [ ] AI 기반 리포트 추천 시스템
- [ ] 협업 기능 추가

## 🤝 기여 방법

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/NewFeature`)
3. Commit your changes (`git commit -m 'Add some NewFeature'`)
4. Push to the branch (`git push origin feature/NewFeature`)
5. Open a Pull Request

### 개발 가이드라인
- 코드 품질: Pylint 8.0+ 점수 유지
- 테스트 커버리지: 80% 이상 목표
- 문서화: 모든 공개 함수에 docstring 필수

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 지원 및 문의

- **이슈 리포팅**: [GitHub Issues](https://github.com/ChangooLee/report-generator/issues)
- **기능 요청**: [GitHub Discussions](https://github.com/ChangooLee/report-generator/discussions)

---

## 🌐 오프라인 사용 지원

본 시스템은 완전한 오프라인 환경에서 동작하도록 설계되었습니다.

### 포함된 정적 리소스

#### 폰트 파일
- **한국어 폰트 (Noto Sans KR)**: 다양한 weight 지원
- **영문 폰트 (Roboto)**: 다양한 weight 지원
- TTF 및 WOFF2 형식으로 다중 지원

#### JavaScript 라이브러리
- **Chart.js**: 다양한 차트 생성
- **D3.js**: 고급 데이터 시각화
- **Plotly.js**: 인터랙티브 플롯

#### CSS 스타일
- 반응형 레이아웃
- 오프라인 폰트 최적화
- 모던 UI 디자인

### 오프라인 환경 구성
```bash
# 모든 리소스가 이미 포함되어 있으므로 별도 설정 불필요
# 인터넷 연결 없이 바로 실행 가능
docker-compose up -d
``` 