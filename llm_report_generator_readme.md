# LLM 기반 대화형 리포트 생성 서비스

Qwen2.5-Coder를 활용하여 자연어 대화에서 인터랙티브 HTML/JS 웹 리포트를 자동 생성하는 완전 오프라인 서비스입니다.

## 🎯 프로젝트 개요

사용자가 자연어로 요청하면, AI가 해당 요청을 이해하고 JSON 데이터를 분석하여 차트와 시각화가 포함된 완전한 HTML 리포트를 생성합니다. 모든 처리는 서버 내부에서 이루어지며, 결과는 Nginx를 통해 웹 URL로 제공됩니다.

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   사용자 대화   │───▶│  오케스트레이터   │───▶│ Qwen2.5-Coder  │
│   (자연어)      │    │   (FastAPI)      │    │   (vLLM)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Nginx 서버    │◀───│   파일 시스템    │◀───│  코드 실행환경   │
│  (리포트 호스팅) │    │ (/reports/*.html)│    │   (Docker)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   MCP 데이터     │
                       │ (JSON 번들들)    │
                       └──────────────────┘
```

## 📁 프로젝트 구조

```
report-generator/
├── README.md
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 메인 애플리케이션
│   ├── orchestrator.py         # 전체 로직 오케스트레이션
│   ├── llm_client.py          # Qwen2.5-Coder 클라이언트
│   ├── code_executor.py       # 코드 실행 환경 관리
│   ├── data_manager.py        # MCP 데이터 관리
│   └── utils/
│       ├── __init__.py
│       ├── file_utils.py
│       ├── security.py
│       └── templates.py
├── data/
│   ├── mcp_bundles/           # MCP JSON 데이터 번들들
│   │   ├── sales_data.json
│   │   ├── user_analytics.json
│   │   └── financial_reports.json
│   └── schemas/               # 데이터 스키마 정의
├── templates/
│   ├── base_report.html       # 리포트 기본 템플릿
│   └── prompts/
│       ├── system_prompt.txt
│       └── code_generation_prompt.txt
├── static/
│   ├── js/
│   │   ├── chart.min.js       # Chart.js 라이브러리
│   │   ├── d3.min.js          # D3.js 라이브러리
│   │   └── plotly.min.js      # Plotly.js 라이브러리
│   ├── css/
│   │   └── report.css         # 리포트 스타일
│   └── fonts/                 # 오프라인 폰트
├── docker/
│   ├── app.Dockerfile         # 메인 애플리케이션
│   ├── executor.Dockerfile    # 코드 실행 환경
│   └── nginx.Dockerfile       # Nginx 웹서버
├── config/
│   ├── nginx.conf
│   ├── uvicorn.conf
│   └── logging.conf
├── scripts/
│   ├── setup.sh              # 초기 설정 스크립트
│   ├── start_services.sh     # 서비스 시작
│   └── download_model.py     # 모델 다운로드
└── reports/                  # 생성된 리포트 저장소
```

## 🚀 설치 및 설정

### 1. 환경 준비

```bash
# 저장소 클론
git clone <repository-url>
cd report-generator

# 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 설정값 입력

# 실행 권한 부여
chmod +x scripts/*.sh
```

### 2. 환경변수 설정 (.env)

```bash
# 서비스 설정
API_HOST=0.0.0.0
API_PORT=8000
NGINX_PORT=80

# vLLM 설정
VLLM_HOST=0.0.0.0
VLLM_PORT=8001
MODEL_NAME=Qwen/Qwen2.5-Coder-32B-Instruct
GPU_MEMORY_UTILIZATION=0.8

# 경로 설정
DATA_PATH=/app/data
REPORTS_PATH=/app/reports
STATIC_PATH=/app/static

# 보안 설정
SECRET_KEY=your-secret-key-here
MAX_EXECUTION_TIME=300
MAX_CODE_SIZE=10000

# Docker 설정
DOCKER_NETWORK=report-net
EXECUTOR_MEMORY_LIMIT=4g
EXECUTOR_CPU_LIMIT=2
```

### 3. 모델 다운로드

```bash
# Qwen2.5-Coder 모델 다운로드
python scripts/download_model.py

# 또는 HuggingFace CLI 사용
pip install huggingface_hub
huggingface-cli download Qwen/Qwen2.5-Coder-32B-Instruct --local-dir ./models/qwen2.5-coder
```

### 4. 서비스 시작

```bash
# 모든 서비스 시작
./scripts/start_services.sh

# 또는 Docker Compose 사용
docker-compose up -d
```

## 💻 핵심 구현 코드

### 1. FastAPI 메인 애플리케이션 (app/main.py)

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from .orchestrator import ReportOrchestrator

app = FastAPI(title="Report Generator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ReportRequest(BaseModel):
    user_query: str
    session_id: str = None
    data_sources: list = None

class ReportResponse(BaseModel):
    success: bool
    report_url: str = None
    error_message: str = None
    processing_time: float = None

# 오케스트레이터 초기화
orchestrator = ReportOrchestrator()

@app.post("/generate-report", response_model=ReportResponse)
async def generate_report(request: ReportRequest):
    """사용자 요청을 받아 리포트를 생성합니다."""
    try:
        result = await orchestrator.process_request(
            user_query=request.user_query,
            session_id=request.session_id,
            data_sources=request.data_sources
        )
        return ReportResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """서비스 상태 확인"""
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/data-sources")
async def list_data_sources():
    """사용 가능한 데이터 소스 목록"""
    return orchestrator.get_available_data_sources()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=True
    )
```

### 2. 오케스트레이터 (app/orchestrator.py)

```python
import asyncio
import time
import uuid
from typing import Dict, List, Optional
from .llm_client import QwenClient
from .data_manager import DataManager
from .code_executor import CodeExecutor
from .utils.templates import PromptTemplates

class ReportOrchestrator:
    def __init__(self):
        self.llm_client = QwenClient()
        self.data_manager = DataManager()
        self.code_executor = CodeExecutor()
        self.prompt_templates = PromptTemplates()
        
    async def process_request(
        self, 
        user_query: str, 
        session_id: Optional[str] = None,
        data_sources: Optional[List[str]] = None
    ) -> Dict:
        """메인 처리 로직"""
        start_time = time.time()
        
        try:
            # 1. 세션 ID 생성
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # 2. 관련 데이터 준비
            context_data = await self.data_manager.prepare_context(
                user_query, data_sources
            )
            
            # 3. LLM 프롬프트 구성
            prompt = self.prompt_templates.build_generation_prompt(
                user_query=user_query,
                context_data=context_data,
                session_id=session_id
            )
            
            # 4. LLM 응답 생성
            llm_response = await self.llm_client.generate_code(prompt)
            
            # 5. 코드 추출 및 검증
            extracted_code = self._extract_code_blocks(llm_response)
            
            # 6. 코드 실행
            execution_result = await self.code_executor.execute_code(
                code=extracted_code,
                session_id=session_id,
                context_data=context_data
            )
            
            # 7. 결과 처리
            if execution_result["success"]:
                report_url = f"/reports/{execution_result['report_filename']}"
                return {
                    "success": True,
                    "report_url": report_url,
                    "processing_time": time.time() - start_time
                }
            else:
                # 오류 시 재시도 로직
                return await self._handle_execution_error(
                    llm_response, execution_result, user_query, context_data, session_id
                )
                
        except Exception as e:
            return {
                "success": False,
                "error_message": str(e),
                "processing_time": time.time() - start_time
            }
    
    def _extract_code_blocks(self, llm_response: str) -> Dict:
        """LLM 응답에서 코드 블록을 추출합니다."""
        import re
        
        # Python 코드 블록 추출
        python_pattern = r'```python\n(.*?)\n```'
        python_matches = re.findall(python_pattern, llm_response, re.DOTALL)
        
        # HTML/JS 코드 블록 추출
        html_pattern = r'```html\n(.*?)\n```'
        html_matches = re.findall(html_pattern, llm_response, re.DOTALL)
        
        # JavaScript 코드 블록 추출
        js_pattern = r'```javascript\n(.*?)\n```'
        js_matches = re.findall(js_pattern, llm_response, re.DOTALL)
        
        return {
            "python_code": python_matches[0] if python_matches else None,
            "html_code": html_matches[0] if html_matches else None,
            "javascript_code": js_matches[0] if js_matches else None,
            "explanation": self._extract_explanation(llm_response)
        }
    
    def _extract_explanation(self, llm_response: str) -> str:
        """LLM 응답에서 설명 텍스트를 추출합니다."""
        # 코드 블록이 아닌 부분을 설명으로 간주
        import re
        explanation = re.sub(r'```.*?```', '', llm_response, flags=re.DOTALL)
        return explanation.strip()
    
    async def _handle_execution_error(self, original_response, error_result, user_query, context_data, session_id):
        """코드 실행 오류 시 재시도 로직"""
        retry_prompt = self.prompt_templates.build_error_fix_prompt(
            original_code=original_response,
            error_message=error_result["error_message"],
            user_query=user_query
        )
        
        # 재시도 (최대 2회)
        for attempt in range(2):
            try:
                fixed_response = await self.llm_client.generate_code(retry_prompt)
                fixed_code = self._extract_code_blocks(fixed_response)
                
                execution_result = await self.code_executor.execute_code(
                    code=fixed_code,
                    session_id=session_id,
                    context_data=context_data
                )
                
                if execution_result["success"]:
                    report_url = f"/reports/{execution_result['report_filename']}"
                    return {"success": True, "report_url": report_url}
                    
            except Exception as e:
                continue
        
        return {
            "success": False,
            "error_message": "코드 실행에 실패했습니다. 요청을 다시 시도해주세요."
        }
    
    def get_available_data_sources(self) -> List[Dict]:
        """사용 가능한 데이터 소스 목록 반환"""
        return self.data_manager.list_available_sources()
```

### 3. LLM 클라이언트 (app/llm_client.py)

```python
import httpx
import json
import os
from typing import Dict, List

class QwenClient:
    def __init__(self):
        self.base_url = f"http://{os.getenv('VLLM_HOST', 'localhost')}:{os.getenv('VLLM_PORT', '8001')}"
        self.model_name = os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-Coder-32B-Instruct')
        
    async def generate_code(self, prompt: str, max_tokens: int = 4000) -> str:
        """Qwen2.5-Coder로부터 코드를 생성합니다."""
        
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "top_p": 0.9,
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
    
    def _get_system_prompt(self) -> str:
        """시스템 프롬프트를 반환합니다."""
        return """
당신은 데이터 분석 및 웹 리포트 생성 전문가입니다. 
사용자의 요청에 따라 JSON 데이터를 분석하고, HTML/JavaScript를 사용하여 
인터랙티브한 시각화 리포트를 생성하는 Python 코드를 작성해야 합니다.

규칙:
1. 반드시 Python 코드와 HTML 템플릿을 생성하세요
2. Chart.js, D3.js, Plotly.js 등의 오프라인 라이브러리를 활용하세요
3. 생성된 HTML은 완전히 독립적으로 실행되어야 합니다
4. 모든 스타일과 스크립트는 로컬 경로를 사용하세요
5. 데이터는 JSON 형태로 제공되며, 이를 적절히 파싱하여 사용하세요
6. 코드는 안전하고 실행 가능해야 합니다

출력 형식:
- Python 코드: ```python ... ```
- HTML 코드: ```html ... ```
- JavaScript 코드 (필요시): ```javascript ... ```
- 설명: 마크다운 형식으로 작성

생성된 리포트는 `/reports/` 디렉토리에 저장되어야 합니다.
"""

    async def health_check(self) -> bool:
        """vLLM 서버 상태 확인"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except:
            return False
```

### 4. 코드 실행 환경 (app/code_executor.py)

```python
import docker
import tempfile
import os
import json
import asyncio
from typing import Dict, Any
import uuid

class CodeExecutor:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.network_name = os.getenv('DOCKER_NETWORK', 'report-net')
        self.reports_path = os.getenv('REPORTS_PATH', '/app/reports')
        
    async def execute_code(
        self, 
        code: Dict[str, str], 
        session_id: str, 
        context_data: Dict[str, Any]
    ) -> Dict:
        """격리된 환경에서 코드를 실행합니다."""
        
        try:
            # 임시 작업 디렉토리 생성
            with tempfile.TemporaryDirectory() as temp_dir:
                
                # 1. 컨텍스트 데이터 저장
                data_file = os.path.join(temp_dir, 'context_data.json')
                with open(data_file, 'w', encoding='utf-8') as f:
                    json.dump(context_data, f, ensure_ascii=False, indent=2)
                
                # 2. Python 코드 실행 스크립트 생성
                if code.get('python_code'):
                    python_script = self._create_python_script(
                        code['python_code'], 
                        session_id,
                        code.get('html_code'),
                        code.get('javascript_code')
                    )
                    
                    script_file = os.path.join(temp_dir, 'execute.py')
                    with open(script_file, 'w', encoding='utf-8') as f:
                        f.write(python_script)
                
                # 3. Docker 컨테이너에서 실행
                result = await self._run_in_container(temp_dir, session_id)
                
                return result
                
        except Exception as e:
            return {
                "success": False,
                "error_message": f"코드 실행 중 오류가 발생했습니다: {str(e)}"
            }
    
    def _create_python_script(
        self, 
        python_code: str, 
        session_id: str,
        html_template: str = None,
        js_code: str = None
    ) -> str:
        """실행할 Python 스크립트를 생성합니다."""
        
        script_template = f"""
import json
import os
import sys
from datetime import datetime

# 안전한 실행을 위한 제한된 환경
__builtins__ = {{
    'print': print,
    'len': len,
    'str': str,
    'int': int,
    'float': float,
    'list': list,
    'dict': dict,
    'json': json,
    'open': open,
    'range': range,
    'enumerate': enumerate,
    'zip': zip,
    'max': max,
    'min': min,
    'sum': sum,
    'sorted': sorted,
    'round': round
}}

# 컨텍스트 데이터 로드
try:
    with open('/workspace/context_data.json', 'r', encoding='utf-8') as f:
        context_data = json.load(f)
    print("컨텍스트 데이터가 성공적으로 로드되었습니다.")
except Exception as e:
    print(f"컨텍스트 데이터 로드 실패: {{e}}")
    context_data = {{}}

# 세션 정보
SESSION_ID = "{session_id}"
REPORT_FILENAME = f"report_{{SESSION_ID}}.html"
REPORTS_PATH = "/reports"

# HTML 템플릿
HTML_TEMPLATE = '''{html_template or ""}'''

# JavaScript 코드
JS_CODE = '''{js_code or ""}'''

# 사용자 정의 코드 실행
try:
{python_code}
    
    print(f"리포트가 성공적으로 생성되었습니다: {{REPORT_FILENAME}}")
    
except Exception as e:
    print(f"오류 발생: {{e}}")
    sys.exit(1)
"""
        
        return script_template
    
    async def _run_in_container(self, workspace_dir: str, session_id: str) -> Dict:
        """Docker 컨테이너에서 코드를 실행합니다."""
        
        container_name = f"executor_{session_id}"
        
        try:
            # 컨테이너 실행
            container = self.docker_client.containers.run(
                image="report-executor:latest",
                name=container_name,
                detach=True,
                remove=True,
                network=self.network_name,
                volumes={
                    workspace_dir: {'bind': '/workspace', 'mode': 'rw'},
                    self.reports_path: {'bind': '/reports', 'mode': 'rw'},
                    '/app/static': {'bind': '/static', 'mode': 'ro'}
                },
                environment={
                    'PYTHONPATH': '/workspace',
                    'SESSION_ID': session_id
                },
                command="python /workspace/execute.py",
                mem_limit=os.getenv('EXECUTOR_MEMORY_LIMIT', '4g'),
                cpu_count=int(os.getenv('EXECUTOR_CPU_LIMIT', '2')),
                security_opt=['no-new-privileges'],
                cap_drop=['ALL']
            )
            
            # 실행 완료 대기 (타임아웃 설정)
            result = container.wait(timeout=int(os.getenv('MAX_EXECUTION_TIME', '300')))
            
            # 로그 수집
            logs = container.logs().decode('utf-8')
            
            if result['StatusCode'] == 0:
                return {
                    "success": True,
                    "report_filename": f"report_{session_id}.html",
                    "logs": logs
                }
            else:
                return {
                    "success": False,
                    "error_message": f"실행 실패 (코드: {result['StatusCode']})",
                    "logs": logs
                }
                
        except docker.errors.ContainerError as e:
            return {
                "success": False,
                "error_message": f"컨테이너 실행 오류: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error_message": f"예상치 못한 오류: {str(e)}"
            }
        finally:
            # 컨테이너 정리
            try:
                container = self.docker_client.containers.get(container_name)
                container.remove(force=True)
            except:
                pass
```

### 5. 데이터 매니저 (app/data_manager.py)

```python
import json
import os
import glob
from typing import Dict, List, Any, Optional
import fnmatch

class DataManager:
    def __init__(self):
        self.data_path = os.getenv('DATA_PATH', '/app/data')
        self.mcp_bundles_path = os.path.join(self.data_path, 'mcp_bundles')
        
    async def prepare_context(
        self, 
        user_query: str, 
        requested_sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """사용자 요청에 맞는 컨텍스트 데이터를 준비합니다."""
        
        # 1. 사용자 요청 분석하여 관련 데이터 소스 식별
        relevant_sources = self._identify_relevant_sources(user_query, requested_sources)
        
        # 2. 데이터 로드 및 병합
        context_data = {}
        for source in relevant_sources:
            try:
                data = self._load_data_bundle(source)
                context_data[source] = data
            except Exception as e:
                print(f"데이터 소스 '{source}' 로드 실패: {e}")
                
        # 3. 메타데이터 추가
        context_data['_metadata'] = {
            'query': user_query,
            'sources_loaded': list(context_data.keys()),
            'total_records': sum(len(v) if isinstance(v, list) else 1 for v in context_data.values() if not v.startswith('_'))
        }
        
        return context_data
    
    def _identify_relevant_sources(
        self, 
        user_query: str, 
        requested_sources: Optional[List[str]] = None
    ) -> List[str]:
        """사용자 쿼리를 분석하여 관련 데이터 소스를 식별합니다."""
        
        # 명시적으로 요청된 소스가 있으면 우선 사용
        if requested_sources:
            return requested_sources
        
        # 키워드 기반 매칭
        available_sources = self.list_available_sources()
        relevant_sources = []
        
        query_lower = user_query.lower()
        
        # 키워드 매칭 규칙
        keyword_mapping = {
            'sales': ['sales_data', 'revenue_data'],
            'user': ['user_analytics', 'user_behavior'],
            'finance': ['financial_reports', 'budget_data'],
            'marketing': ['marketing_campaigns', 'ad_performance'],
            'product': ['product_analytics', 'inventory_data'],
            'traffic': ['web_analytics', 'user_analytics'],
            'conversion': ['conversion_data', 'funnel_analytics']
        }
        
        for keyword, sources in keyword_mapping.items():
            if keyword in query_lower:
                for source in sources:
                    if any(s['name'] == source for s in available_sources):
                        relevant_sources.append(source)
        
        # 매칭되는 소스가 없으면 기본 소스 사용
        if not relevant_sources and available_sources:
            relevant_sources = [available_sources[0]['name']]
        
        return list(set(relevant_sources))  # 중복 제거
    
    def _load_data_bundle(self, source_name: str) -> Any:
        """특정 데이터 번들을 로드합니다."""
        
        bundle_file = os.path.join(self.mcp_bundles_path, f"{source_name}.json")
        
        if not os.path.exists(bundle_file):
            raise FileNotFoundError(f"데이터 번들 '{source_name}' 파일을 찾을 수 없습니다.")
        
        with open(bundle_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_available_sources(self) -> List[Dict[str, Any]]:
        """사용 가능한 데이터 소스 목록을 반환합니다."""
        
        sources = []
        
        # JSON 파일들을 스캔
        pattern = os.path.join(self.mcp_bundles_path, "*.json")
        
        for file_path in glob.glob(pattern):
            source_name = os.path.splitext(os.path.basename(file_path))[0]
            
            try:
                # 파일 메타데이터 수집
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 데이터 구조 분석
                record_count = len(data) if isinstance(data, list) else 1
                
                sources.append({
                    'name': source_name,
                    'file_path': file_path,
                    'record_count': record_count,
                    'size_mb': round(os.path.getsize(file_path) / 1024 / 1024, 2),
                    'description': self._generate_description(source_name, data)
                })
                
            except Exception as e:
                print(f"소스 '{source_name}' 분석 실패: {e}")
        
        return sorted(sources, key=lambda x: x['name'])
    
    def _generate_description(self, source_name: str, data: Any) -> str:
        """데이터 소스에 대한 설명을 생성합니다."""
        
        if isinstance(data, list) and data:
            sample = data[0]
            if isinstance(sample, dict):
                keys = list(sample.keys())[:5]  # 처음 5개 키만
                return f"{len(data)}개 레코드, 주요 필드: {', '.join(keys)}"
        
        return f"데이터 타입: {type(data).__name__}"
```

### 6. Docker 설정

#### docker-compose.yml

```yaml
version: '3.8'

services:
  # vLLM 서빙 서버
  vllm-server:
    image: vllm/vllm-openai:latest
    container_name: vllm-server
    ports:
      - "${VLLM_PORT:-8001}:8000"
    volumes:
      - ./models:/models
      - ./cache:/root/.cache
    environment:
      - CUDA_VISIBLE_DEVICES=0
    command: >
      --model /models/qwen2.5-coder
      --served-model-name ${MODEL_NAME}
      --host 0.0.0.0
      --port 8000
      --gpu-memory-utilization ${GPU_MEMORY_UTILIZATION:-0.8}
      --max-model-len 32768
      --dtype auto
      --api-key ${VLLM_API_KEY:-your-api-key}
    networks:
      - report-net
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # 메인 애플리케이션
  app:
    build:
      context: .
      dockerfile: docker/app.Dockerfile
    container_name: report-app
    ports:
      - "${API_PORT:-8000}:8000"
    volumes:
      - ./data:/app/data:ro
      - ./reports:/app/reports:rw
      - ./static:/app/static:ro
      - ./templates:/app/templates:ro
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - VLLM_HOST=vllm-server
      - VLLM_PORT=8000
      - DATA_PATH=/app/data
      - REPORTS_PATH=/app/reports
      - STATIC_PATH=/app/static
    depends_on:
      - vllm-server
    networks:
      - report-net

  # Nginx 웹서버
  nginx:
    build:
      context: .
      dockerfile: docker/nginx.Dockerfile
    container_name: report-nginx
    ports:
      - "${NGINX_PORT:-80}:80"
    volumes:
      - ./reports:/usr/share/nginx/html/reports:ro
      - ./static:/usr/share/nginx/html/static:ro
      - ./config/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - app
    networks:
      - report-net

  # 코드 실행 환경 (베이스 이미지)
  executor:
    build:
      context: .
      dockerfile: docker/executor.Dockerfile
    image: report-executor:latest
    container_name: report-executor-base
    profiles: ["build-only"]  # 직접 실행하지 않음
    networks:
      - report-net

networks:
  report-net:
    driver: bridge

volumes:
  model-cache:
```

#### docker/app.Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    docker.io \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### docker/executor.Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /workspace

# 분석 라이브러리 설치
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    matplotlib \
    seaborn \
    plotly \
    jinja2 \
    beautifulsoup4

# 보안 설정
RUN useradd -m -s /bin/bash executor
USER executor

# 기본 실행 명령
CMD ["python", "/workspace/execute.py"]
```

#### docker/nginx.Dockerfile

```dockerfile
FROM nginx:alpine

# Nginx 설정 파일 복사
COPY config/nginx.conf /etc/nginx/nginx.conf

# 정적 파일 디렉토리 생성
RUN mkdir -p /usr/share/nginx/html/reports \
    && mkdir -p /usr/share/nginx/html/static

# 포트 노출
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 7. 프롬프트 템플릿 (app/utils/templates.py)

```python
from typing import Dict, Any, List

class PromptTemplates:
    
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
   - JSON 데이터를 분석하고 처리
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

# 데이터 로드 및 분석
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
    </style>
</head>
<body>
    <!-- 리포트 내용 -->
</body>
</html>
'''

# 파일 저장
with open(f'/reports/report_{SESSION_ID}.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
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

수정된 코드:
"""

    @staticmethod  
    def _prepare_data_preview(context_data: Dict[str, Any]) -> str:
        """컨텍스트 데이터의 미리보기를 생성합니다."""
        
        preview_lines = []
        
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
                    
            preview_lines.append("")
        
        return "\n".join(preview_lines)
```

## 🔧 설정 파일들

### config/nginx.conf

```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    sendfile on;
    keepalive_timeout 65;
    
    # 보안 헤더
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    server {
        listen 80;
        server_name localhost;
        
        # 정적 파일 서빙
        location /static/ {
            alias /usr/share/nginx/html/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
        
        # 리포트 파일 서빙
        location /reports/ {
            alias /usr/share/nginx/html/reports/;
            expires 1h;
            add_header Cache-Control "public";
        }
        
        # API 프록시
        location /api/ {
            proxy_pass http://app:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
        
        # 기본 페이지
        location / {
            return 301 /static/index.html;
        }
    }
}
```

### requirements.txt

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
httpx==0.25.2
docker==6.1.3
jinja2==3.1.2
python-multipart==0.0.6
python-dotenv==1.0.0
aiofiles==23.2.1
pandas==2.1.3
numpy==1.25.2
```

## 🚀 사용 방법

### 1. 서비스 시작

```bash
# 모든 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f app
```

### 2. 데이터 준비

```bash
# MCP 데이터 번들 예시 생성
mkdir -p data/mcp_bundles

# 샘플 데이터 생성
cat > data/mcp_bundles/sales_data.json << 'EOF'
[
  {
    "date": "2024-01-01",
    "product": "Product A",
    "sales": 1500,
    "revenue": 45000,
    "region": "Seoul"
  },
  {
    "date": "2024-01-01", 
    "product": "Product B",
    "sales": 800,
    "revenue": 32000,
    "region": "Busan"
  }
]
EOF
```

### 3. API 호출 예시

```bash
# 리포트 생성 요청
curl -X POST "http://localhost:8000/generate-report" \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "지난 달 제품별 매출 현황을 차트로 보여주세요",
    "session_id": "test123",
    "data_sources": ["sales_data"]
  }'

# 응답 예시
{
  "success": true,
  "report_url": "/reports/report_test123.html",
  "processing_time": 15.3
}
```

### 4. 웹 인터페이스

`static/index.html` 파일을 생성하여 사용자 친화적인 인터페이스 제공:

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 리포트 생성기</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .input-area { margin-bottom: 20px; }
        textarea { width: 100%; height: 100px; padding: 10px; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        .result { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>🤖 AI 리포트 생성기</h1>
    
    <div class="input-area">
        <label for="query">요청사항을 입력하세요:</label>
        <textarea id="query" placeholder="예: 지난 분기 매출 현황을 차트로 보여주세요"></textarea>
        <button onclick="generateReport()">리포트 생성</button>
    </div>
    
    <div id="result" class="result" style="display:none;"></div>

    <script>
        async function generateReport() {
            const query = document.getElementById('query').value;
            const resultDiv = document.getElementById('result');
            
            if (!query.trim()) {
                alert('요청사항을 입력해주세요.');
                return;
            }
            
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '리포트를 생성하고 있습니다...';
            
            try {
                const response = await fetch('/api/generate-report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_query: query,
                        session_id: 'web_' + Date.now()
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    resultDiv.innerHTML = `
                        <h3>✅ 리포트가 생성되었습니다!</h3>
                        <p>처리 시간: ${result.processing_time.toFixed(1)}초</p>
                        <a href="${result.report_url}" target="_blank" style="display: inline-block; background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">리포트 보기</a>
                    `;
                } else {
                    resultDiv.innerHTML = `<h3>❌ 오류 발생</h3><p>${result.error_message}</p>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<h3>❌ 네트워크 오류</h3><p>${error.message}</p>`;
            }
        }
    </script>
</body>
</html>
```

## 🔒 보안 고려사항

### 1. 코드 실행 환경 격리
- Docker 컨테이너로 완전 격리
- 네트워크 접근 차단
- 파일시스템 접근 제한
- 리소스 사용량 제한

### 2. 입력 검증
```python
# app/utils/security.py
import re
from typing import List

class SecurityValidator:
    
    @staticmethod
    def validate_user_query(query: str) -> bool:
        """사용자 쿼리의 안전성을 검증합니다."""
        
        # 길이 제한
        if len(query) > 1000:
            return False
        
        # 위험한 키워드 필터링
        dangerous_keywords = [
            'import os', 'import sys', 'subprocess', 
            'eval(', 'exec(', '__import__',
            'file://', 'http://', 'https://'
        ]
        
        query_lower = query.lower()
        for keyword in dangerous_keywords:
            if keyword in query_lower:
                return False
        
        return True
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """파일명을 안전하게 정리합니다."""
        
        # 알파벳, 숫자, 하이픈, 언더스코어만 허용
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', filename)
        
        # 길이 제한
        return sanitized[:50]
```

### 3. 파일 시스템 보안
```python
# 안전한 경로 검증
def validate_file_path(path: str, allowed_base: str) -> bool:
    """파일 경로가 허용된 디렉토리 내에 있는지 확인합니다."""
    
    import os
    
    try:
        # 절대 경로로 변환
        abs_path = os.path.abspath(path)
        abs_base = os.path.abspath(allowed_base)
        
        # 공통 경로 확인
        return os.path.commonpath([abs_path, abs_base]) == abs_base
    
    except (ValueError, OSError):
        return False
```

## 🔄 확장 가능성

### 1. 다양한 차트 라이브러리 지원
- D3.js 고급 시각화
- Plotly.js 과학적 차트
- Three.js 3D 시각화

### 2. 추가 데이터 소스
- 실시간 API 연동
- 데이터베이스 직접 연결
- 파일 업로드 지원

### 3. 고급 기능
- 사용자 인증 시스템
- 리포트 버전 관리
- 이메일 자동 발송
- PDF 내보내기

### 4. 성능 최적화
- Redis 캐싱
- 비동기 큐 시스템
- GPU 메모리 최적화
- 분산 처리

## 🐛 트러블슈팅

### 일반적인 문제들

1. **GPU 메모리 부족**
```bash
# GPU 사용량 확인
nvidia-smi

# vLLM 메모리 설정 조정
# .env에서 GPU_MEMORY_UTILIZATION 값을 0.7로 낮춤
```

2. **Docker 권한 문제**
```bash
# Docker 그룹에 사용자 추가
sudo usermod -aG docker $USER
sudo systemctl restart docker
```

3. **포트 충돌**
```bash
# 사용 중인 포트 확인
sudo netstat -tulpn | grep :8000

# .env에서 포트 번호 변경
```

### 로그 확인

```bash
# 전체 서비스 로그
docker-compose logs

# 특정 서비스 로그
docker-compose logs app
docker-compose logs vllm-server

# 실시간 로그 모니터링
docker-compose logs -f
```

## 📈 성능 최적화 팁

### 1. vLLM 최적화
```bash
# GPU 메모리 사용률 조정
export GPU_MEMORY_UTILIZATION=0.8

# 배치 크기 최적화
export MAX_NUM_SEQS=256

# KV 캐시 최대 토큰 수
export MAX_MODEL_LEN=8192
```

### 2. 컨테이너 리소스 최적화
```yaml
# docker-compose.yml에서 리소스 제한
services:
  executor:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 2G
          cpus: '1.0'
```

### 3. 캐싱 전략
```python
# app/utils/cache.py
import asyncio
from functools import wraps
from typing import Dict, Any

class ReportCache:
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._max_size = 100
    
    def get_cache_key(self, user_query: str, data_sources: list) -> str:
        """캐시 키 생성"""
        import hashlib
        key_data = f"{user_query}:{','.join(sorted(data_sources or []))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, key: str) -> Any:
        """캐시에서 값 조회"""
        return self._cache.get(key)
    
    async def set(self, key: str, value: Any):
        """캐시에 값 저장"""
        if len(self._cache) >= self._max_size:
            # LRU 방식으로 오래된 항목 제거
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[key] = value
```

## 🧪 테스트

### 1. 단위 테스트
```python
# tests/test_data_manager.py
import pytest
from app.data_manager import DataManager

@pytest.fixture
def data_manager():
    return DataManager()

@pytest.mark.asyncio
async def test_prepare_context(data_manager):
    """컨텍스트 데이터 준비 테스트"""
    
    query = "매출 현황을 보여주세요"
    context = await data_manager.prepare_context(query)
    
    assert isinstance(context, dict)
    assert '_metadata' in context
    assert 'query' in context['_metadata']
```

### 2. 통합 테스트
```python
# tests/test_integration.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_generate_report_endpoint():
    """리포트 생성 API 테스트"""
    
    response = client.post("/generate-report", json={
        "user_query": "테스트 리포트를 생성해주세요",
        "session_id": "test123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "report_url" in data
```

### 3. 성능 테스트
```python
# tests/test_performance.py
import time
import asyncio
from app.orchestrator import ReportOrchestrator

async def test_response_time():
    """응답 시간 테스트"""
    
    orchestrator = ReportOrchestrator()
    
    start_time = time.time()
    result = await orchestrator.process_request(
        user_query="간단한 차트를 생성해주세요",
        session_id="perf_test"
    )
    end_time = time.time()
    
    response_time = end_time - start_time
    assert response_time < 30.0  # 30초 이내 응답
    assert result["success"] is True
```

## 📊 모니터링

### 1. 시스템 메트릭
```python
# app/monitoring.py
import psutil
import time
from typing import Dict

class SystemMonitor:
    
    @staticmethod
    def get_system_metrics() -> Dict:
        """시스템 메트릭 수집"""
        
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "timestamp": time.time()
        }
    
    @staticmethod
    def get_gpu_metrics() -> Dict:
        """GPU 메트릭 수집 (nvidia-smi 필요)"""
        
        try:
            import subprocess
            result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total', '--format=csv,nounits,noheader'], 
                                 capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                gpu_data = []
                
                for i, line in enumerate(lines):
                    parts = line.split(', ')
                    gpu_data.append({
                        "gpu_id": i,
                        "utilization": float(parts[0]),
                        "memory_used": float(parts[1]),
                        "memory_total": float(parts[2])
                    })
                
                return {"gpus": gpu_data}
                
        except Exception as e:
            return {"error": str(e)}
        
        return {"gpus": []}
```

### 2. 애플리케이션 메트릭
```python
# app/metrics.py
from collections import defaultdict
import time

class ApplicationMetrics:
    def __init__(self):
        self.request_count = defaultdict(int)
        self.response_times = []
        self.error_count = 0
        self.success_count = 0
    
    def record_request(self, endpoint: str):
        """요청 기록"""
        self.request_count[endpoint] += 1
    
    def record_response_time(self, duration: float):
        """응답 시간 기록"""
        self.response_times.append(duration)
        
        # 최근 100개만 유지
        if len(self.response_times) > 100:
            self.response_times.pop(0)
    
    def record_success(self):
        """성공 응답 기록"""
        self.success_count += 1
    
    def record_error(self):
        """오류 응답 기록"""
        self.error_count += 1
    
    def get_metrics(self) -> dict:
        """메트릭 조회"""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        return {
            "total_requests": sum(self.request_count.values()),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "average_response_time": avg_response_time,
            "requests_by_endpoint": dict(self.request_count)
        }
```

## 📝 추가 스크립트

### scripts/setup.sh
```bash
#!/bin/bash

echo "🚀 Report Generator 설정을 시작합니다..."

# 1. 환경 변수 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다. .env.example을 복사하여 설정하세요."
    exit 1
fi

# 2. 디렉토리 생성
echo "📁 디렉토리를 생성합니다..."
mkdir -p data/mcp_bundles
mkdir -p data/schemas
mkdir -p reports
mkdir -p static/js
mkdir -p static/css
mkdir -p static/fonts
mkdir -p models
mkdir -p cache

# 3. Chart.js 다운로드
echo "📊 Chart.js를 다운로드합니다..."
curl -L https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.min.js -o static/js/chart.min.js

# 4. D3.js 다운로드  
echo "📈 D3.js를 다운로드합니다..."
curl -L https://d3js.org/d3.v7.min.js -o static/js/d3.min.js

# 5. Plotly.js 다운로드
echo "📉 Plotly.js를 다운로드합니다..."
curl -L https://cdn.plot.ly/plotly-2.27.0.min.js -o static/js/plotly.min.js

# 6. 기본 CSS 생성
echo "🎨 기본 스타일을 생성합니다..."
cat > static/css/report.css << 'EOF'
/* 리포트 기본 스타일 */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 0;
    padding: 20px;
    background-color: #f8f9fa;
}

.report-container {
    max-width: 1200px;
    margin: 0 auto;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    padding: 30px;
}

.report-title {
    color: #2c3e50;
    border-bottom: 3px solid #3498db;
    padding-bottom: 10px;
    margin-bottom: 30px;
}

.chart-container {
    margin: 30px 0;
    padding: 20px;
    background: #fafafa;
    border-radius: 6px;
    border-left: 4px solid #3498db;
}

.insight-box {
    background: #e8f5e8;
    border: 1px solid #d4edda;
    border-radius: 6px;
    padding: 15px;
    margin: 20px 0;
}

.metric-card {
    display: inline-block;
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 20px;
    margin: 10px;
    min-width: 150px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.metric-value {
    font-size: 2em;
    font-weight: bold;
    color: #2980b9;
}

.metric-label {
    color: #7f8c8d;
    margin-top: 5px;
}

@media (max-width: 768px) {
    .report-container {
        padding: 15px;
    }
    
    .metric-card {
        display: block;
        margin: 10px 0;
    }
}
EOF

# 7. 샘플 데이터 생성
echo "📊 샘플 데이터를 생성합니다..."
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
  }
]
EOF

echo "✅ 설정이 완료되었습니다!"
echo "🔧 다음 단계: docker-compose up -d 실행"
```

### scripts/start_services.sh
```bash
#!/bin/bash

echo "🚀 Report Generator 서비스를 시작합니다..."

# 1. 환경 확인
./scripts/setup.sh

# 2. Docker 네트워크 생성
echo "🌐 Docker 네트워크를 생성합니다..."
docker network create report-net 2>/dev/null || echo "네트워크가 이미 존재합니다."

# 3. 이미지 빌드
echo "🏗️ Docker 이미지를 빌드합니다..."
docker-compose build

# 4. 서비스 시작
echo "▶️ 서비스를 시작합니다..."
docker-compose up -d

# 5. 서비스 상태 확인
echo "🔍 서비스 상태를 확인합니다..."
sleep 10

if docker-compose ps | grep -q "Up"; then
    echo "✅ 서비스가 성공적으로 시작되었습니다!"
    echo ""
    echo "🌐 서비스 URL:"
    echo "  - 웹 인터페이스: http://localhost"
    echo "  - API 문서: http://localhost:8000/docs"
    echo "  - 헬스체크: http://localhost:8000/health"
    echo ""
    echo "📊 사용 방법:"
    echo "  1. 브라우저에서 http://localhost 접속"
    echo "  2. 원하는 리포트를 자연어로 요청"
    echo "  3. 생성된 리포트 URL 클릭하여 확인"
else
    echo "❌ 서비스 시작에 실패했습니다."
    echo "로그를 확인하세요: docker-compose logs"
fi
```

### scripts/download_model.py
```python
#!/usr/bin/env python3
"""
Qwen2.5-Coder 모델 다운로드 스크립트
"""

import os
import sys
from pathlib import Path
from huggingface_hub import snapshot_download
from dotenv import load_dotenv

def main():
    # 환경변수 로드
    load_dotenv()
    
    model_name = os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-Coder-32B-Instruct')
    model_dir = Path('./models/qwen2.5-coder')
    
    print(f"🤖 {model_name} 모델을 다운로드합니다...")
    print(f"📁 저장 경로: {model_dir.absolute()}")
    
    try:
        # 모델 디렉토리 생성
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # 모델 다운로드
        snapshot_download(
            repo_id=model_name,
            local_dir=str(model_dir),
            resume_download=True
        )
        
        print("✅ 모델 다운로드가 완료되었습니다!")
        
        # 모델 파일 확인
        model_files = list(model_dir.rglob('*'))
        total_size = sum(f.stat().st_size for f in model_files if f.is_file())
        
        print(f"📊 다운로드 완료:")
        print(f"  - 파일 수: {len([f for f in model_files if f.is_file()])}")
        print(f"  - 총 크기: {total_size / (1024**3):.2f} GB")
        
    except Exception as e:
        print(f"❌ 모델 다운로드 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## 📝 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 상업적 사용이 가능하며, 자유롭게 수정 및 배포할 수 있습니다.

---

이 README를 참고하여 완전한 오프라인 AI 리포트 생성 서비스를 구축할 수 있습니다. 각 구성 요소는 독립적으로 개발 및 테스트가 가능하며, 전체 시스템은 확장 가능한 구조로 설계되었습니다.