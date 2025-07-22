"""
부동산 MCP 전용 오케스트레이터 - 에이전틱 워크플로우 복원
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.streaming_api import StreamingCallback

from app.langgraph_workflow import TrueAgenticWorkflow

logger = logging.getLogger(__name__)

class RealestateOrchestrator:
    """부동산 MCP 에이전틱 오케스트레이터 - LLM이 도구를 자율 선택"""
    
    def __init__(self):
        self.workflow = TrueAgenticWorkflow()
        self.initialized = False
    
    async def initialize(self) -> bool:
        """에이전틱 워크플로우 초기화"""
        if not self.initialized:
            await self.workflow.initialize_tools()
            self.initialized = True
        return self.initialized
    
    async def process_query(
        self,
        query: str,
        session_id: str = "default",
        streaming_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """에이전틱 쿼리 처리 - LLM이 도구를 자율 선택"""
        
        start_time = datetime.now()
        
        try:
            logger.info(f"🤖 에이전틱 쿼리 처리 시작: {query}")
            
            # 초기화 확인
            if not self.initialized:
                await self.initialize()
            
            if streaming_callback:
                await streaming_callback.send_status("🤖 AI 에이전트가 도구를 자율 선택합니다...")  # type: ignore
            
            # 에이전틱 워크플로우 실행
            result = await self.workflow.run_with_streaming(query, streaming_callback)
            
            # 실행 시간 계산
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 결과 보강
            result.update({
                "session_id": session_id,
                "execution_time": execution_time,
                "timestamp": start_time.isoformat(),
                "system_type": "agentic_mcp_workflow"
            })
            
            if result["success"]:
                logger.info(f"✅ 에이전틱 쿼리 처리 완료 ({execution_time:.2f}초)")
                if streaming_callback:
                    await streaming_callback.send_status("✅ AI 에이전트 분석이 완료되었습니다")  # type: ignore
            else:
                logger.error(f"❌ 에이전틱 쿼리 처리 실패: {result.get('error')}")
                if streaming_callback:
                    await streaming_callback.send_status(f"❌ 처리 실패: {result.get('error', '알 수 없는 오류')}")  # type: ignore
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"에이전틱 오케스트레이터 오류: {str(e)}"
            
            logger.error(f"❌ {error_msg}")
            
            if streaming_callback:
                await streaming_callback.send_status(f"❌ {error_msg}")  # type: ignore
            
            return {
                "success": False,
                "error": error_msg,
                "report_content": "",
                "analysis_content": "",
                "session_id": session_id,
                "execution_time": execution_time,
                "timestamp": start_time.isoformat(),
                "system_type": "agentic_mcp_workflow"
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """헬스 체크"""
        try:
            if not self.initialized:
                await self.initialize()
            
            return {
                "status": "healthy",
                "system_type": "agentic_mcp_workflow",
                "tools_count": len(self.workflow.tools) if self.workflow.tools else 0,
                "initialized": self.initialized
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "system_type": "agentic_mcp_workflow"
            }
    
    async def get_available_tools(self) -> list:
        """사용 가능한 도구 목록"""
        try:
            if not self.initialized:
                await self.initialize()
            
            tools_data = []
            if self.workflow.tools:
                for tool in self.workflow.tools:
                    tools_data.append({
                        "name": tool.name,
                        "description": tool.description,
                        "server": getattr(tool, 'server_name', 'builtin')
                    })
            
            return tools_data
            
        except Exception as e:
            logger.error(f"도구 목록 조회 실패: {e}")
            return [] 