"""
스트리밍 API 엔드포인트
JavaScript와 연결하여 채팅 기능을 제공
"""

import asyncio
import json
import logging
from typing import Dict, Any, AsyncGenerator, Optional
from datetime import datetime
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import os
import glob
from app.utils.templates import get_latest_report

logger = logging.getLogger(__name__)

# 실행 중인 세션 추적
running_sessions = {}

class ChatRequest(BaseModel):
    user_query: str
    session_id: Optional[str] = None
    format: str = "html"

class StreamingCallback:
    """스트리밍 콜백 클래스"""
    
    def __init__(self):
        self.queue = asyncio.Queue()
    
    async def send_status(self, message: str):
        """상태 메시지 전송"""
        await self.queue.put({
            "type": "status",
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_tool_start(self, tool_name: str, server_name: str = ""):
        """도구 시작 알림"""
        await self.queue.put({
            "type": "tool_start",
            "tool_name": tool_name,
            "server_name": server_name,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_tool_complete(self, tool_name: str, result: str):
        """도구 완료 알림"""
        await self.queue.put({
            "type": "tool_complete",
            "tool_name": tool_name,
            "result": result,  # 길이 제한 제거 - 전체 결과 표시
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_tool_error(self, tool_name: str, error: str):
        """도구 오류 알림"""
        await self.queue.put({
            "type": "tool_error",
            "tool_name": tool_name,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_tool_abort(self, tool_name: str, message: str):
        """도구 중단 알림"""
        await self.queue.put({
            "type": "tool_abort", 
            "tool_name": tool_name,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_llm_start(self, model_name: str):
        """LLM 응답 시작 알림"""
        await self.queue.put({
            "type": "llm_start",
            "model": model_name,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_llm_chunk(self, content: str):
        """LLM 응답 청크 전송"""
        if content and content.strip():
            await self.queue.put({
                "type": "content",
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
    
    async def send_analysis_step(self, step_name: str, description: str):
        """분석 단계 알림"""
        await self.queue.put({
            "type": "analysis_step",
            "step": step_name,
            "description": description,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_progress(self, value: int, message: str = ""):
        """진행률 업데이트"""
        await self.queue.put({
            "type": "progress",
            "value": min(100, max(0, value)),
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_complete(self, result: Dict[str, Any]):
        """완료 알림"""
        await self.queue.put({
            "type": "complete",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_error(self, error: str):
        """오류 알림"""
        await self.queue.put({
            "type": "error",
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_report_update(self, report_path: str):
        """리포트 생성 완료 및 목록 갱신 알림"""
        # 상대 경로로 변환 (웹에서 접근 가능한 URL)
        project_root = os.getenv('PROJECT_ROOT', os.getcwd())
        relative_path = report_path.replace(f'{project_root}/', '')
        report_url = f"/{relative_path}"
        
        # complete 이벤트 전송
        await self.queue.put({
            "type": "complete",
            "report_url": report_url,
            "timestamp": datetime.now().isoformat()
        })
        
        # 리포트 목록 갱신 알림도 전송
        await self.queue.put({
            "type": "report_update",
            "report_path": report_path,
            "report_url": report_url,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_code(self, html_content: str, filename: str = "report.html"):
        """HTML 코드 전송"""
        logger.info(f"🔍 send_code 호출됨: 코드 길이={len(html_content)}, 파일명={filename}")
        await self.queue.put({
            "type": "code",
            "code": html_content,
            "filename": filename,
            "timestamp": datetime.now().isoformat()
        })
        logger.info("📤 HTML 코드 이벤트가 큐에 추가됨")

def generate_sse_data(event: str, data: Dict[str, Any]) -> str:
    """SSE 형식의 데이터 생성"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

def create_streaming_endpoints(app: FastAPI, orchestrator):
    """스트리밍 엔드포인트 생성"""
    
    @app.post("/chat/stream")
    async def chat_stream(request: ChatRequest):
        """채팅 스트리밍 엔드포인트"""
        
        async def stream_generator() -> AsyncGenerator[str, None]:
            session_id = request.session_id if request.session_id else f"session_{datetime.now().timestamp()}"
            
            # 세션 시작 추적
            running_sessions[session_id] = {
                "abort": False, 
                "start_time": datetime.now(),
                "user_query": request.user_query
            }
            
            streaming_callback = StreamingCallback()
            
            try:
                # 중단 체크 함수
                def should_abort():
                    return running_sessions.get(session_id, {}).get("abort", False)
                
                # 시작 상태 전송
                if should_abort():
                    yield generate_sse_data("message", {"type": "abort", "message": "사용자 요청으로 중단되었습니다."})
                    return
                    
                yield generate_sse_data("message", {"type": "status", "message": "🚀 AI 에이전트를 초기화하고 있습니다..."})
                await asyncio.sleep(0.2)
                
                # 중단 체크
                if should_abort():
                    yield generate_sse_data("message", {"type": "abort", "message": "사용자 요청으로 중단되었습니다."})
                    return
                
                # LangGraph 워크플로우 실행
                logger.info(f"사용자 쿼리 처리 시작: {request.user_query}")
                
                # 도구 초기화 상태
                yield generate_sse_data("message", {"type": "status", "message": "🔍 MCP 도구들을 자동 발견하고 있습니다..."})
                
                # 중단 체크
                if should_abort():
                    yield generate_sse_data("message", {"type": "abort", "message": "사용자 요청으로 중단되었습니다."})
                    return
                
                # 실제 워크플로우 실행
                # orchestrator가 함수인 경우 실제 인스턴스 가져오기
                if callable(orchestrator):
                    actual_orchestrator = orchestrator()
                else:
                    actual_orchestrator = orchestrator
                    
                logger.info(f"🔍 orchestrator 타입: {type(actual_orchestrator)}")
                logger.info(f"🔍 process_query 존재 여부: {hasattr(actual_orchestrator, 'process_query')}")
                
                workflow_task = asyncio.create_task(
                    actual_orchestrator.process_query(request.user_query, session_id, streaming_callback)
                )
                
                # 스트리밍 메시지 처리 (중단 체크 포함)
                message_count = 0
                while not workflow_task.done() or not streaming_callback.queue.empty():
                    # 중단 체크
                    if should_abort():
                        logger.info(f"🛑 세션 {session_id} 중단 요청 감지")
                        workflow_task.cancel()  # 워크플로우 태스크 취소
                        
                        # 모든 대기 중인 메시지 제거
                        while not streaming_callback.queue.empty():
                            try:
                                streaming_callback.queue.get_nowait()
                            except:
                                break
                        
                        # 중단 메시지 전송
                        yield generate_sse_data("message", {"type": "abort", "message": "사용자 요청으로 분석이 중단되었습니다."})
                        yield generate_sse_data("message", {"type": "complete", "success": False, "message": "중단됨"})
                        return
                    
                    try:
                        # 큐에서 메시지 가져오기 (타임아웃 0.1초)
                        message = await asyncio.wait_for(streaming_callback.queue.get(), timeout=0.1)
                        
                        if message.get("type") == "stop":
                            break
                        
                        # UI로 메시지 전송 (올바른 SSE 형식)
                        yield generate_sse_data("message", message)
                        message_count += 1
                        
                        # 🔍 디버깅: 모든 메시지 타입 로깅
                        if message.get("type") == "tool_complete":
                            logger.info(f"🔍 tool_complete 감지: tool_name={message.get('tool_name')}, result={str(message.get('result', ''))}")
                        
                        # 🔥 리포트 완료 메시지 감지 시 즉시 처리 (수정된 조건)
                        is_report_complete = (
                            message.get("type") == "tool_complete" and 
                            message.get("tool_name") == "html_report"
                        ) or (
                            "HTML 리포트" in str(message.get("result", "")) and 
                            ("생성되고 저장되었습니다" in str(message.get("result", "")) or "저장 완료" in str(message.get("result", "")))
                        )
                        
                        if is_report_complete:
                            logger.info("🎉 html_report 완료 감지 - 즉시 리포트 처리")
                            try:
                                reports_dir = os.getenv('REPORTS_PATH', './reports')
                                report_files = glob.glob(os.path.join(reports_dir, "report_*.html"))
                                
                                if report_files:
                                    latest_report = get_latest_report(reports_dir)
                                    if latest_report:  # None 체크 추가
                                        logger.info(f"🎉 즉시 리포트 감지: {latest_report}")
                                        
                                        # HTML 파일 읽기
                                        with open(latest_report, 'r', encoding='utf-8') as f:
                                            html_content = f.read()
                                        
                                        # 즉시 UI로 전송
                                        yield generate_sse_data("message", {
                                            "type": "code", 
                                            "code": html_content,
                                            "filename": os.path.basename(latest_report)
                                        })
                                        
                                        yield generate_sse_data("message", {
                                            "type": "report_update",
                                            "report_path": latest_report
                                        })
                                        
                                        logger.info("🎨 즉시 HTML 코드 및 리포트 업데이트 전송 완료")
                            except Exception as e:
                                logger.error(f"❌ 즉시 리포트 처리 실패: {e}")
                        
                        # 진행상황 표시
                        if message_count % 3 == 0:
                            progress = min(85, message_count * 5)
                            yield generate_sse_data("message", {"type": "progress", "value": progress})
                        
                    except asyncio.TimeoutError:
                        # 타임아웃 - 워크플로우 완료 확인
                        if workflow_task.done():
                            logger.info(f"🔍 워크플로우 완료 감지 - 루프 종료")
                            break
                        continue
                    except asyncio.CancelledError:
                        # 태스크가 취소됨
                        logger.info(f"🛑 워크플로우 태스크 취소됨: {session_id}")
                        yield generate_sse_data("message", {"type": "abort", "message": "분석이 중단되었습니다."})
                        return
                
                # 워크플로우 결과 대기
                result = await workflow_task
                logger.info(f"🔍 워크플로우 결과: success={result.get('success', False)}")
                
                # 🔥 리포트 생성 완료 감지 및 UI 알림 (무조건 실행)
                logger.info("🔍 리포트 감지 시작")
                try:
                    reports_dir = os.getenv('REPORTS_PATH', './reports')
                    report_files = glob.glob(os.path.join(reports_dir, "report_*.html"))
                    logger.info(f"🔍 발견된 리포트 파일 수: {len(report_files)}")
                    
                    if report_files:
                        # 파일명의 타임스탬프 기준으로 최신 파일 찾기 (더 정확함)
                        def extract_timestamp(filepath):
                            filename = os.path.basename(filepath)
                            # report_1753164168.html에서 1753164168 추출
                            import re
                            match = re.search(r'report_(\d+)\.html', filename)
                            return int(match.group(1)) if match else 0
                        
                        latest_report = max(report_files, key=extract_timestamp)
                        logger.info(f"🎉 streaming_api에서 최신 리포트 감지: {latest_report}")
                        
                        # HTML 파일 내용을 코드 뷰에 전송
                        with open(latest_report, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        
                        yield generate_sse_data("message", {
                            "type": "code", 
                            "code": html_content,
                            "filename": os.path.basename(latest_report)
                        })
                        
                        yield generate_sse_data("message", {
                            "type": "report_update",
                            "report_path": latest_report
                        })
                        
                        logger.info("🎨 streaming_api에서 HTML 코드 및 리포트 업데이트 전송 완료")
                        
                except Exception as e:
                    logger.error(f"❌ streaming_api 리포트 알림 실패: {e}")
                
                # 🔥 워크플로우 완료 후 무조건 리포트 감지 및 UI 알림
                logger.info("🔍 워크플로우 완료 - 리포트 감지 시작")
                try:
                    reports_dir = os.getenv('REPORTS_PATH', './reports')
                    report_files = glob.glob(os.path.join(reports_dir, "report_*.html"))
                    logger.info(f"🔍 발견된 리포트 파일 수: {len(report_files)}")
                    
                    if report_files:
                        # 파일명의 타임스탬프 기준으로 최신 파일 찾기
                        latest_report = get_latest_report(reports_dir)
                        if latest_report:  # None 체크 추가
                            logger.info(f"🎉 최신 리포트 감지: {latest_report}")
                            
                            # HTML 파일 내용을 코드 뷰에 전송
                            with open(latest_report, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            
                            # 1. HTML 코드 이벤트 전송
                            yield generate_sse_data("message", {
                                "type": "code", 
                                "code": html_content,
                                "filename": os.path.basename(latest_report)
                            })
                            
                            # 2. 리포트 업데이트 이벤트 전송
                            yield generate_sse_data("message", {
                                "type": "report_update",
                                "report_path": latest_report
                            })
                            
                            logger.info("🎨 HTML 코드 및 리포트 업데이트 이벤트 전송 완료")
                            
                except Exception as e:
                    logger.error(f"❌ 리포트 감지 및 전송 실패: {e}")
                
                # 최종 결과 전송
                yield generate_sse_data("message", {"type": "progress", "value": 100, "message": "완료"})
                
                if result.get("success"):
                    # HTML 코드 전송 (추가 보장)
                    if result.get("html_content"):
                        yield generate_sse_data("message", {
                            "type": "code",
                            "code": result["html_content"],
                            "filename": f"report_{session_id}.html"
                        })
                    
                    yield generate_sse_data("message", {
                        "type": "complete",
                        "success": True,
                        "analysis": result.get("analysis", "분석이 완료되었습니다."),
                        "report_url": result.get("report_url"),
                        "session_id": session_id
                    })
                else:
                    yield generate_sse_data("message", {
                        "type": "error",
                        "message": result.get("error", "알 수 없는 오류가 발생했습니다.")
                    })
                
            except Exception as e:
                logger.error(f"스트리밍 처리 중 오류: {e}")
                yield generate_sse_data("error", {"message": f"처리 중 오류가 발생했습니다: {str(e)}"})
        
            finally:
                # 🔥 세션 종료 전 최종 리포트 감지 및 UI 알림 (무조건 실행)
                logger.info("🔍 세션 종료 전 최종 리포트 감지 시작")
                try:
                    reports_dir = os.getenv('REPORTS_PATH', './reports')
                    report_files = glob.glob(os.path.join(reports_dir, "report_*.html"))
                    logger.info(f"🔍 세션 종료 시점 리포트 파일 수: {len(report_files)}")
                    
                    if report_files:
                        # 생성 시간 기준 최신 파일
                        latest_report = max(report_files, key=os.path.getctime)
                        logger.info(f"🎉 세션 종료 시점 최신 리포트: {latest_report}")
                        
                        # HTML 파일 내용을 코드 뷰에 전송
                        try:
                            with open(latest_report, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            
                            # 최종 이벤트 전송
                            yield generate_sse_data("message", {
                                "type": "code", 
                                "code": html_content,
                                "filename": os.path.basename(latest_report)
                            })
                            
                            yield generate_sse_data("message", {
                                "type": "report_update",
                                "report_path": latest_report
                            })
                            
                            logger.info("🎨 세션 종료 시점 HTML 코드 및 리포트 업데이트 최종 전송 완료")
                            
                        except Exception as read_error:
                            logger.error(f"HTML 파일 읽기 실패: {read_error}")
                        
                except Exception as e:
                    logger.error(f"❌ 세션 종료 시점 리포트 감지 실패: {e}")
                
                # 세션 종료 시 추적에서 제거
                if session_id in running_sessions:
                    del running_sessions[session_id]
                    logger.info(f"🔄 세션 {session_id} 정리 완료")


        
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*"
            }
        ) 
    
    @app.post("/chat/abort")
    async def abort_chat(request: dict):
        """실행 중인 채팅 세션을 강제 종료"""
        session_id = request.get("session_id")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id가 필요합니다")
        
        try:
            # 실행 중인 세션이 있다면 종료 플래그 설정
            if session_id in running_sessions:
                session_info = running_sessions[session_id]
                session_info["abort"] = True  # type: ignore
                user_query = session_info.get("user_query", "알 수 없음")  # type: ignore
                logger.info(f"🛑 세션 {session_id} 강제 종료 요청 (쿼리: {str(user_query)[:50]}...)")
                
                return {
                    "success": True,
                    "message": f"세션 {session_id} 강제 종료 요청이 처리되었습니다.",
                    "session_id": session_id
                }
            else:
                return {
                    "success": False,
                    "message": f"세션 {session_id}가 실행 중이지 않습니다.",
                    "session_id": session_id,
                    "running_sessions": list(running_sessions.keys())
                }
                
        except Exception as e:
            logger.error(f"강제 종료 처리 실패: {e}")
            raise HTTPException(status_code=500, detail=f"강제 종료 실패: {str(e)}")
    
    @app.get("/chat/sessions")
    async def get_active_sessions():
        """현재 실행 중인 세션 목록 조회"""
        sessions = []
        for session_id, info in running_sessions.items():
            sessions.append({
                "session_id": session_id,
                "start_time": info["start_time"].isoformat(),
                "user_query": info["user_query"],
                "running_duration_seconds": (datetime.now() - info["start_time"]).total_seconds()
            })
        
        return {
            "success": True,
            "active_sessions": sessions,
            "total_count": len(sessions)
        } 