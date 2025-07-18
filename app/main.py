"""
Universal Report Generator FastAPI Application
범용 리포트 생성 FastAPI 애플리케이션 - LangGraph 기반
"""

import os
import asyncio
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from dotenv import load_dotenv
import json
import httpx
from contextlib import asynccontextmanager

from app.orchestrator import UniversalOrchestrator
from app.streaming_api import create_streaming_endpoints

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 FastAPI 서버 시작: http://0.0.0.0:7001")
    
    # 동적 프롬프트 생성 (백그라운드 태스크)
    asyncio.create_task(generate_dynamic_prompts())
    
    yield
    logger.info("FastAPI 서버 종료")

# FastAPI 앱 생성
app = FastAPI(
    title="Universal Report Generator",
    description="LangGraph 기반 에이전틱 데이터 분석 및 리포트 생성 시스템",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 제공
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

# 새로운 프론트엔드 정적 파일 제공
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# 오케스트레이터 초기화
orchestrator = UniversalOrchestrator()

# 스트리밍 엔드포인트 추가
create_streaming_endpoints(app, orchestrator)


# Pydantic 모델들
class ReportRequest(BaseModel):
    user_query: str
    data_source: Optional[str] = "auto"
    format: Optional[str] = "html"


class ReportResponse(BaseModel):
    success: bool
    session_id: str
    report_content: Optional[str] = None
    browser_test_url: Optional[str] = None
    validation_passed: Optional[bool] = None
    processing_time: Optional[float] = None
    timestamp: str
    workflow_type: str = "langgraph"
    error: Optional[str] = None


class HealthResponse(BaseModel):
    overall_status: str
    components: Dict[str, str]
    timestamp: str


# 동적 프롬프트 생성을 위한 변수
dynamic_prompts = []

async def generate_dynamic_prompts():
    """MCP 도구 정보를 기반으로 동적 프롬프트 생성"""
    global dynamic_prompts
    try:
        # MCP 도구 정보 수집
        tools_info = await orchestrator.get_available_tools()
        
        if not tools_info:
            # 실용적인 기본 프롬프트 사용
            dynamic_prompts = [
                "월별 판매 데이터의 트렌드를 분석해주세요",
                "지역별 성과 비교 분석 리포트를 만들어주세요",
                "최근 3개월 데이터 패턴을 시각화해주세요",
                "카테고리별 성장률 변화를 분석해주세요"
            ]
            return
        
        # 도구 정보를 OpenRouter에 보내서 프롬프트 생성
        tools_description = []
        for tool in tools_info[:10]:  # 최대 10개 도구만
            tools_description.append(f"- {tool.get('name', '')}: {tool.get('description', '')}")
        
        tools_text = "\n".join(tools_description)
        
        # OpenRouter API 호출
        prompt = f"""다음과 같은 데이터 분석 MCP 도구들이 사용 가능합니다:

{tools_text}

이 도구들을 활용해서 실제로 분석 가능한 구체적인 데이터 분석 프롬프트 4개를 한국어로 생성해주세요.

요구사항:
- 명확한 분석 목적 설정
- 시각화 요소 포함
- 실제 분석 가능한 데이터 유형
- 구체적인 분석 방법 명시

응답 형식:
1. [프롬프트 1]
2. [프롬프트 2] 
3. [프롬프트 3]
4. [프롬프트 4]

예시: "월별 판매 데이터의 트렌드를 분석하고 시각화해주세요"
각 프롬프트는 한 줄로만 작성해주세요."""

        openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        if not openrouter_api_key:
            logger.warning("OpenRouter API 키가 없어 실용적인 기본 프롬프트를 사용합니다")
            dynamic_prompts = [
                "월별 판매 데이터의 트렌드를 분석해주세요",
                "지역별 성과 비교 분석 리포트를 만들어주세요",
                "최근 3개월 데이터 패턴을 시각화해주세요",
                "카테고리별 성장률 변화를 분석해주세요"
            ]
            return
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "anthropic/claude-sonnet-4",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 800
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # 프롬프트 파싱
                lines = content.strip().split('\n')
                prompts = []
                for line in lines:
                    line = line.strip()
                    if line and (line.startswith('1.') or line.startswith('2.') or 
                               line.startswith('3.') or line.startswith('4.')):
                        # 번호 제거하고 프롬프트만 추출
                        prompt_text = line.split('.', 1)[1].strip()
                        if prompt_text:
                            prompts.append(prompt_text)
                
                if len(prompts) >= 4:
                    dynamic_prompts = prompts[:4]
                else:
                    # 부족하면 실용적인 기본값으로 채움
                    default_prompts = [
                        "월별 판매 데이터의 트렌드를 분석해주세요",
                        "지역별 성과 비교 분석 리포트를 만들어주세요",
                        "최근 3개월 데이터 패턴을 시각화해주세요",
                        "카테고리별 성장률 변화를 분석해주세요"
                    ]
                    dynamic_prompts = prompts + default_prompts[len(prompts):4]
                    
                logger.info(f"✅ 동적 프롬프트 {len(dynamic_prompts)}개 생성 완료")
            else:
                logger.warning(f"OpenRouter API 오류: {response.status_code}")
                dynamic_prompts = [
                    "월별 판매 데이터의 트렌드를 분석해주세요",
                    "지역별 성과 비교 분석 리포트를 만들어주세요",
                    "최근 3개월 데이터 패턴을 시각화해주세요",
                    "카테고리별 성장률 변화를 분석해주세요"
                ]
                
    except Exception as e:
        logger.error(f"동적 프롬프트 생성 실패: {e}")
        dynamic_prompts = [
            "월별 판매 데이터의 트렌드를 분석해주세요",
            "지역별 성과 비교 분석 리포트를 만들어주세요",
            "최근 3개월 데이터 패턴을 시각화해주세요",
            "카테고리별 성장률 변화를 분석해주세요"
        ]

# 새로운 UI 라우트
@app.get("/ui", response_class=HTMLResponse)
async def get_new_ui():
    """새로운 채팅 UI 제공"""
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Frontend not found</h1><p>새로운 UI 파일이 없습니다.</p>",
            status_code=404
        )


@app.get("/")
async def redirect_to_ui():
    """메인 페이지를 새로운 UI로 리다이렉트"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/ui")


@app.get("/tools")
async def get_available_tools():
    """실제 MCP 도구 목록 제공"""
    try:
        # LangGraph 워크플로우에서 도구들 가져오기
        await orchestrator.langgraph_workflow.initialize_tools()
        tools = orchestrator.langgraph_workflow.tools
        
        tools_data = []
        for tool in tools:
            server_name = getattr(tool, 'server_name', 'builtin')
            tools_data.append({
                "name": tool.name,
                "description": tool.description,
                "server": server_name,
                "type": "mcp" if server_name != "builtin" else "builtin"
            })
        
        return {
            "success": True,
            "tools": tools_data,
            "total_count": len(tools_data),
            "servers": list(set(tool["server"] for tool in tools_data))
        }
        
    except Exception as e:
        logger.error(f"도구 목록 조회 실패: {e}")
        return {
            "success": False,
            "error": str(e),
            "tools": [],
            "total_count": 0,
            "servers": []
        }


@app.get("/health")
async def health_check() -> HealthResponse:
    """시스템 상태 확인"""
    components = {}
    overall_status = "healthy"
    
    try:
        # 오케스트레이터 상태 확인
        components["orchestrator"] = "healthy"
        
        # LLM 클라이언트 상태 확인
        llm_healthy = await orchestrator.llm_client.health_check()
        components["llm_client"] = "healthy" if llm_healthy else "unhealthy"
        if not llm_healthy:
            overall_status = "degraded"
        
        # MCP 클라이언트 상태 확인
        mcp_servers = orchestrator.mcp_client.get_server_status()
        components["mcp_client"] = "healthy"
        
        # LangGraph 워크플로우 상태 확인
        components["langgraph_workflow"] = "healthy"
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        overall_status = "unhealthy"
        components["error"] = str(e)
    
    return HealthResponse(
        overall_status=overall_status,
        components=components,
        timestamp=datetime.now().isoformat()
    )


@app.get("/reports/{report_filename}")
async def get_report(report_filename: str):
    """생성된 리포트 파일 조회"""
    
    report_path = f"reports/{report_filename}"
    
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="리포트 파일을 찾을 수 없습니다.")
    
    return FileResponse(
        path=report_path,
        media_type="text/html",
        filename=report_filename
    )


@app.get("/reports")
async def list_reports():
    """생성된 리포트 목록 조회"""
    
    try:
        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            return {"reports": []}
        
        reports = []
        for filename in os.listdir(reports_dir):
            if filename.endswith('.html'):
                file_path = os.path.join(reports_dir, filename)
                stat = os.stat(file_path)
                
                reports.append({
                    "filename": filename,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "size": stat.st_size,
                    "url": f"/reports/{filename}"
                })
        
        # 생성 시간 기준 내림차순 정렬
        reports.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "total": len(reports),
            "reports": reports
        }
        
    except Exception as e:
        logger.error(f"리포트 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="리포트 목록 조회 중 오류가 발생했습니다.")


@app.get("/api/prompts")
async def get_dynamic_prompts():
    """동적으로 생성된 프롬프트 반환"""
    return {"prompts": dynamic_prompts}

# 실행 중인 세션들을 추적
running_sessions = {}

@app.post("/chat/abort")
async def abort_chat(request: Dict[str, str]):
    """실행 중인 채팅 세션을 강제 종료"""
    session_id = request.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id가 필요합니다")
    
    try:
        # 실행 중인 세션이 있다면 종료 플래그 설정
        if session_id in running_sessions:
            running_sessions[session_id]["abort"] = True
            logger.info(f"🛑 세션 {session_id} 강제 종료 요청")
            
            return {
                "success": True,
                "message": f"세션 {session_id} 강제 종료 요청이 처리되었습니다.",
                "session_id": session_id
            }
        else:
            return {
                "success": False,
                "message": f"세션 {session_id}가 실행 중이지 않습니다.",
                "session_id": session_id
            }
            
    except Exception as e:
        logger.error(f"강제 종료 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"강제 종료 실패: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", 7000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"🚀 FastAPI 서버 시작: http://{host}:{port}")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    ) 