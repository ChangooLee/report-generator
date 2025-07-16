"""
Universal Report Generator FastAPI Application
범용 리포트 생성 FastAPI 애플리케이션
"""

import os
import asyncio
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from dotenv import load_dotenv

from app.orchestrator import UniversalOrchestrator

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Universal Report Generator",
    description="클로드 데스크탑 스타일의 범용 데이터 분석 및 리포트 생성 시스템",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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

# 오케스트레이터 초기화
orchestrator = UniversalOrchestrator()


# Pydantic 모델들
class ReportRequest(BaseModel):
    user_query: str
    data_sources: Optional[List[str]] = None
    report_style: str = "executive"  # executive, analytical, presentation, dashboard, narrative
    insight_level: str = "intermediate"  # basic, intermediate, advanced
    use_legacy: bool = False


class ReportResponse(BaseModel):
    success: bool
    session_id: str
    report_url: Optional[str] = None
    report_path: Optional[str] = None
    report_type: Optional[str] = None
    processing_time: float
    sections_count: Optional[int] = None
    insights_count: Optional[int] = None
    error: Optional[str] = None
    config: Optional[dict] = None


@app.get("/", response_class=HTMLResponse)
async def root():
    """메인 페이지"""
    return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Universal Report Generator</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
            }
            .container {
                text-align: center;
                max-width: 800px;
                padding: 40px;
                background: rgba(255,255,255,0.1);
                border-radius: 20px;
                backdrop-filter: blur(10px);
                box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            }
            h1 {
                font-size: 3rem;
                font-weight: 300;
                margin-bottom: 20px;
                letter-spacing: -0.02em;
            }
            .subtitle {
                font-size: 1.3rem;
                margin-bottom: 40px;
                opacity: 0.9;
            }
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 40px 0;
            }
            .feature {
                background: rgba(255,255,255,0.1);
                padding: 25px;
                border-radius: 15px;
                border: 1px solid rgba(255,255,255,0.2);
            }
            .feature h3 {
                font-size: 1.2rem;
                margin-bottom: 10px;
            }
            .feature p {
                font-size: 0.9rem;
                opacity: 0.8;
            }
            .api-links {
                margin-top: 40px;
            }
            .api-links a {
                color: white;
                text-decoration: none;
                background: rgba(255,255,255,0.2);
                padding: 12px 24px;
                border-radius: 25px;
                margin: 0 10px;
                display: inline-block;
                transition: all 0.3s ease;
                border: 1px solid rgba(255,255,255,0.3);
            }
            .api-links a:hover {
                background: rgba(255,255,255,0.3);
                transform: translateY(-2px);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Universal Report Generator</h1>
            <p class="subtitle">클로드 데스크탑 스타일의 전략적 데이터 분석 및 리포트 생성 시스템</p>
            
            <div class="features">
                <div class="feature">
                    <h3>🎯 전략적 리포트</h3>
                    <p>Executive, Analytical, Presentation, Dashboard, Narrative 스타일 지원</p>
                </div>
                <div class="feature">
                    <h3>🔄 범용 데이터 처리</h3>
                    <p>JSON, CSV, MCP 응답 등 다양한 데이터 소스 자동 인식</p>
                </div>
                <div class="feature">
                    <h3>📊 인텔리전트 시각화</h3>
                    <p>데이터 특성 기반 자동 차트 타입 추천 및 생성</p>
                </div>
                <div class="feature">
                    <h3>💡 다단계 인사이트</h3>
                    <p>Basic, Intermediate, Advanced 수준의 분석 및 권장사항</p>
                </div>
            </div>
            
            <div class="api-links">
                <a href="/docs">API 문서</a>
                <a href="/system/status">시스템 상태</a>
                <a href="/system/styles">지원 스타일</a>
            </div>
        </div>
    </body>
    </html>
    """


@app.post("/generate-report", response_model=ReportResponse)
async def generate_report(request: ReportRequest, background_tasks: BackgroundTasks):
    """리포트 생성 API"""
    
    try:
        logger.info(f"리포트 생성 요청: {request.user_query[:50]}...")
        
        # 세션 ID 생성
        session_id = str(uuid.uuid4())
        
        # 입력 검증
        available_styles = orchestrator.get_available_styles()
        if request.report_style not in available_styles:
            raise HTTPException(
                status_code=400, 
                detail=f"지원되지 않는 리포트 스타일: {request.report_style}. 사용 가능: {available_styles}"
            )
        
        available_levels = orchestrator.get_available_insight_levels()
        if request.insight_level not in available_levels:
            raise HTTPException(
                status_code=400,
                detail=f"지원되지 않는 인사이트 수준: {request.insight_level}. 사용 가능: {available_levels}"
            )
        
        # 리포트 생성
        result = await orchestrator.generate_report(
            user_query=request.user_query,
            session_id=session_id,
            data_sources=request.data_sources,
            report_style=request.report_style,
            insight_level=request.insight_level,
            use_legacy=request.use_legacy
        )
        
        # 응답 생성
        response = ReportResponse(
            success=result.get("success", False),
            session_id=session_id,
            report_url=result.get("report_url"),
            report_path=result.get("report_path"),
            report_type=result.get("report_type"),
            processing_time=result.get("processing_time", 0),
            sections_count=result.get("sections_count"),
            insights_count=result.get("insights_count"),
            error=result.get("error"),
            config=result.get("config")
        )
        
        if response.success:
            logger.info(f"✅ 리포트 생성 성공: {session_id}")
        else:
            logger.error(f"❌ 리포트 생성 실패: {session_id} - {response.error}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"리포트 생성 API 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/system/status")
async def get_system_status():
    """시스템 상태 확인"""
    
    try:
        status = orchestrator.get_system_status()
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"시스템 상태 확인 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/system/styles")
async def get_available_styles():
    """사용 가능한 리포트 스타일"""
    
    try:
        return {
            "styles": orchestrator.get_available_styles(),
            "insight_levels": orchestrator.get_available_insight_levels(),
            "descriptions": {
                "executive": "경영진용 - 간결하고 핵심적인 인사이트",
                "analytical": "분석가용 - 상세하고 기술적인 분석",
                "presentation": "발표용 - 시각적이고 임팩트 있는 구성",
                "dashboard": "대시보드 - 실시간 모니터링용 메트릭",
                "narrative": "스토리텔링 - 논리적 흐름 중심의 구성"
            },
            "insight_descriptions": {
                "basic": "기본 통계 및 요약 정보",
                "intermediate": "패턴 분석 및 상관관계 탐지",
                "advanced": "예측 모델링 및 실행 가능한 권장사항"
            }
        }
    except Exception as e:
        logger.error(f"스타일 정보 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports/{session_id}")
async def get_report(session_id: str):
    """생성된 리포트 조회"""
    
    try:
        # 전략적 리포트 확인
        strategic_path = f"./reports/strategic_report_{session_id}.html"
        if os.path.exists(strategic_path):
            return FileResponse(
                path=strategic_path,
                media_type="text/html",
                filename=f"strategic_report_{session_id}.html"
            )
        
        # 일반 리포트 확인
        general_path = f"./reports/report_{session_id}.html"
        if os.path.exists(general_path):
            return FileResponse(
                path=general_path,
                media_type="text/html",
                filename=f"report_{session_id}.html"
            )
        
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다.")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"리포트 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
async def run_test():
    """시스템 테스트 실행"""
    
    try:
        logger.info("시스템 테스트 실행 시작")
        
        # 간단한 테스트 실행
        test_session_id = f"test_{int(datetime.now().timestamp())}"
        
        result = await orchestrator.generate_report(
            user_query="샘플 데이터를 분석한 executive 리포트를 생성해주세요",
            session_id=test_session_id,
            data_sources=None,
            report_style="executive",
            insight_level="intermediate",
            use_legacy=False
        )
        
        return {
            "test_status": "completed",
            "test_result": result,
            "system_status": orchestrator.get_system_status()
        }
        
    except Exception as e:
        logger.error(f"테스트 실행 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """헬스 체크"""
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "system": "Universal Report Generator"
    }


# 애플리케이션 시작 시 실행
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 초기화"""
    
    logger.info("🚀 Universal Report Generator 시작")
    
    # 필요한 디렉토리 생성
    os.makedirs("reports", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # 시스템 상태 확인
    try:
        status = orchestrator.get_system_status()
        logger.info(f"✅ 시스템 초기화 완료 - 버전: {status['version']}")
        logger.info(f"📊 지원 스타일: {', '.join(status['supported_styles'])}")
        logger.info(f"💡 인사이트 수준: {', '.join(status['supported_insight_levels'])}")
    except Exception as e:
        logger.error(f"❌ 시스템 초기화 실패: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 정리"""
    
    logger.info("👋 Universal Report Generator 종료")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 