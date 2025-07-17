"""
스트리밍 API 엔드포인트
JavaScript와 연결하여 채팅 기능을 제공
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

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
            "result": result[:200] + "..." if len(result) > 200 else result,
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

def generate_sse_data(event: str, data: Dict[str, Any]) -> str:
    """SSE 형식의 데이터 생성"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

def create_streaming_endpoints(app: FastAPI, orchestrator):
    """스트리밍 엔드포인트 생성"""
    
    @app.post("/chat/stream")
    async def chat_stream(request: ChatRequest):
        """채팅 스트리밍 엔드포인트"""
        
        async def stream_generator() -> AsyncGenerator[str, None]:
            streaming_callback = StreamingCallback()
            
            try:
                # 세션 ID 생성
                session_id = request.session_id if request.session_id else f"session_{datetime.now().timestamp()}"
                
                # 시작 상태 전송
                yield generate_sse_data("message", {"type": "status", "message": "🚀 AI 에이전트를 초기화하고 있습니다..."})
                await asyncio.sleep(0.2)
                
                # LangGraph 워크플로우 실행
                logger.info(f"사용자 쿼리 처리 시작: {request.user_query}")
                
                # 도구 초기화 상태
                yield generate_sse_data("message", {"type": "status", "message": "🔍 MCP 도구들을 자동 발견하고 있습니다..."})
                
                # 실제 워크플로우 실행 (가짜 시뮬레이션 제거)
                workflow_task = asyncio.create_task(
                    orchestrator.process_query_with_streaming(request.user_query, session_id, streaming_callback)
                )
                
                # 스트리밍 메시지 처리
                message_count = 0
                while not workflow_task.done() or not streaming_callback.queue.empty():
                    try:
                        # 큐에서 메시지 가져오기 (타임아웃 0.1초)
                        message = await asyncio.wait_for(streaming_callback.queue.get(), timeout=0.1)
                        
                        if message.get("type") == "stop":
                            break
                        
                        # UI로 메시지 전송 (올바른 SSE 형식)
                        yield generate_sse_data("message", message)
                        message_count += 1
                        
                        # 진행상황 표시
                        if message_count % 3 == 0:
                            progress = min(85, message_count * 5)
                            yield generate_sse_data("message", {"type": "progress", "value": progress})
                        
                    except asyncio.TimeoutError:
                        # 타임아웃 - 워크플로우 완료 확인
                        if workflow_task.done():
                            break
                        continue
                
                # 워크플로우 결과 대기
                result = await workflow_task
                
                # 최종 결과 전송
                yield generate_sse_data("message", {"type": "progress", "value": 100, "message": "완료"})
                
                if result.get("success"):
                    # HTML 코드 전송
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
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*"
            }
        ) 