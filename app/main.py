from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import os
import logging
from typing import Optional, List, Dict, Any
from .orchestrator import ReportOrchestrator
from .llm_client import OpenRouterClient
from .mcp_client import MCPClient

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Report Generator API", 
    version="1.0.0",
    description="AI 기반 대화형 리포트 생성 서비스"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청/응답 모델 정의
class ReportRequest(BaseModel):
    user_query: str
    session_id: Optional[str] = None
    data_sources: Optional[List[str]] = None
    mcp_tools: Optional[List[str]] = None

class ReportResponse(BaseModel):
    success: bool
    report_url: Optional[str] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    session_id: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    version: str
    models: Dict[str, Any]
    mcp_servers: Dict[str, bool]

class DataSourceInfo(BaseModel):
    name: str
    description: str
    available_tools: List[str]

# 전역 인스턴스
orchestrator = None
llm_client = None
mcp_client = None

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 초기화"""
    global orchestrator, llm_client, mcp_client
    
    try:
        # LLM 클라이언트 초기화
        llm_client = OpenRouterClient()
        logger.info("OpenRouter LLM 클라이언트 초기화 완료")
        
        # MCP 클라이언트 초기화
        mcp_client = MCPClient()
        logger.info("MCP 클라이언트 초기화 완료")
        
        # 한국 부동산 MCP 서버 연결 테스트
        try:
            # 부동산 MCP 서버 탐색
            discovery_result = await mcp_client.discover_mcp_server("/app/mcp_external/kr-realestate")
            if "error" not in discovery_result:
                logger.info(f"부동산 MCP 서버 발견: {discovery_result.get('tools', [])}")
            else:
                logger.warning(f"부동산 MCP 서버 연결 실패: {discovery_result['error']}")
        except Exception as e:
            logger.warning(f"부동산 MCP 서버 탐색 실패: {e}")
        
        # 오케스트레이터 초기화
        orchestrator = ReportOrchestrator(llm_client, mcp_client)
        logger.info("리포트 오케스트레이터 초기화 완료")
        
    except Exception as e:
        logger.error(f"애플리케이션 초기화 실패: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 정리"""
    global mcp_client
    
    if mcp_client:
        await mcp_client.shutdown_all()
        logger.info("MCP 서버 종료 완료")

@app.post("/generate-report", response_model=ReportResponse)
async def generate_report(request: ReportRequest, background_tasks: BackgroundTasks):
    """사용자 요청을 받아 리포트를 생성합니다."""
    
    if not orchestrator:
        raise HTTPException(status_code=500, detail="서비스가 초기화되지 않았습니다.")
    
    try:
        result = await orchestrator.process_request(
            user_query=request.user_query,
            session_id=request.session_id,
            data_sources=request.data_sources,
            mcp_tools=request.mcp_tools
        )
        
        return ReportResponse(**result)
        
    except Exception as e:
        logger.error(f"리포트 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"리포트 생성 중 오류가 발생했습니다: {str(e)}")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """서비스 상태 확인"""
    
    try:
        # LLM 클라이언트 상태 확인
        llm_status = await llm_client.health_check() if llm_client else False
        
        # MCP 서버 상태 확인
        mcp_status = mcp_client.get_server_status() if mcp_client else {}
        
        # 모델 정보 조회
        model_info = llm_client.get_model_info() if llm_client else {}
        
        return HealthResponse(
            status="healthy" if llm_status else "degraded",
            version="1.0.0",
            models=model_info,
            mcp_servers=mcp_status
        )
        
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return HealthResponse(
            status="unhealthy",
            version="1.0.0",
            models={},
            mcp_servers={}
        )

@app.get("/data-sources", response_model=List[DataSourceInfo])
async def list_data_sources():
    """사용 가능한 데이터 소스 목록"""
    
    if not orchestrator:
        raise HTTPException(status_code=500, detail="서비스가 초기화되지 않았습니다.")
    
    try:
        sources = await orchestrator.get_available_data_sources()
        return [DataSourceInfo(**source) for source in sources]
        
    except Exception as e:
        logger.error(f"데이터 소스 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"데이터 소스 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/models")
async def list_models():
    """사용 가능한 모델 목록"""
    
    if not llm_client:
        raise HTTPException(status_code=500, detail="LLM 클라이언트가 초기화되지 않았습니다.")
    
    try:
        models = await llm_client.list_available_models()
        return {"models": models}
        
    except Exception as e:
        logger.error(f"모델 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"모델 목록 조회 중 오류가 발생했습니다: {str(e)}")

@app.get("/mcp-servers")
async def list_mcp_servers():
    """MCP 서버 목록 및 상태"""
    
    if not mcp_client:
        raise HTTPException(status_code=500, detail="MCP 클라이언트가 초기화되지 않았습니다.")
    
    try:
        status = mcp_client.get_server_status()
        servers = {}
        
        for server_name in mcp_client.mcp_configs.keys():
            tools = await mcp_client.list_tools(server_name)
            servers[server_name] = {
                "status": status.get(server_name, {}).get("running", False),
                "tools": tools
            }
        
        return {"servers": servers}
        
    except Exception as e:
        logger.error(f"MCP 서버 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"MCP 서버 조회 중 오류가 발생했습니다: {str(e)}")

@app.post("/mcp-call")
async def call_mcp_tool(
    server_name: str,
    tool_name: str,
    arguments: Dict[str, Any]
):
    """MCP 도구 직접 호출"""
    
    if not mcp_client:
        raise HTTPException(status_code=500, detail="MCP 클라이언트가 초기화되지 않았습니다.")
    
    try:
        result = await mcp_client.call_tool(server_name, tool_name, arguments)
        if result:
            return {"success": True, "result": result}
        else:
            return {"success": False, "error": "도구 호출 실패"}
            
    except Exception as e:
        logger.error(f"MCP 도구 호출 실패: {e}")
        raise HTTPException(status_code=500, detail=f"MCP 도구 호출 중 오류가 발생했습니다: {str(e)}")

@app.post("/test-simple-report")
async def test_simple_report(request: ReportRequest):
    """간단한 테스트 리포트 생성"""
    try:
        from .test_executor import TestCodeExecutor
        
        test_executor = TestCodeExecutor()
        
        # 가짜 코드와 컨텍스트 데이터 생성
        fake_code = {
            "python_code": "print('Hello, World!')",
            "html_code": None,
            "javascript_code": None
        }
        
        fake_context = {
            "test_data": {"message": "이것은 테스트입니다"},
            "_metadata": {"query": request.user_query}
        }
        
        result = await test_executor.execute_code(
            code=fake_code,
            session_id=request.session_id or "test_session",
            context_data=fake_context
        )
        
        if result["success"]:
            return {
                "success": True,
                "report_url": f"/reports/{result['report_filename']}",
                "session_id": request.session_id,
                "message": "테스트 리포트가 성공적으로 생성되었습니다."
            }
        else:
            return {
                "success": False,
                "error_message": result.get("error", "알 수 없는 오류"),
                "session_id": request.session_id
            }
            
    except Exception as e:
        logger.error(f"테스트 리포트 생성 실패: {e}")
        return {
            "success": False,
            "error_message": f"테스트 리포트 생성 실패: {str(e)}",
            "session_id": request.session_id
        }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """전역 예외 처리"""
    logger.error(f"예상치 못한 오류: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_message": "내부 서버 오류가 발생했습니다."
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 7000)),
        reload=True,
        log_level="info"
    ) 