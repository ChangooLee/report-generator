"""
Universal Orchestrator - LangGraph 기반 범용 쿼리 처리 오케스트레이터
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable

from app.langgraph_workflow import TrueAgenticWorkflow
from app.llm_client import OpenRouterClient
from app.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class UniversalOrchestrator:
    """범용 쿼리 처리를 위한 오케스트레이터"""
    
    def __init__(self):
        """초기화"""
        try:
            # 각 컴포넌트 초기화
            self.llm_client = OpenRouterClient()
            self.mcp_client = MCPClient()
            self.langgraph_workflow = TrueAgenticWorkflow()
            
            logger.info("🚀 Universal Orchestrator (LangGraph) 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ Orchestrator 초기화 실패: {e}")
            raise

    async def process_query_with_streaming(self, user_query: str, session_id: str, streaming_callback) -> Dict[str, Any]:
        """스트리밍과 함께 쿼리 처리"""
        
        try:
            logger.info(f"🔄 Orchestrator 쿼리 처리 시작: {session_id}")
            logger.info(f"🔍 process_query_with_streaming 호출됨!")
            logger.info(f"🔍 streaming_callback 타입: {type(streaming_callback)}")
            
            # 중단 체크 함수
            def should_abort():
                try:
                    from .streaming_api import running_sessions
                    return running_sessions.get(session_id, {}).get("abort", False)
                except:
                    return False
            
            # 중단 체크
            if should_abort():
                logger.info(f"🛑 쿼리 처리 시작 전 중단 감지: {session_id}")
                return {"success": False, "error": "중단됨", "analysis": "", "report_content": ""}
            
            # LangGraph 워크플로우 실행
            result = await self.langgraph_workflow.run_with_streaming(
                user_query, 
                streaming_callback,
                abort_check=should_abort
            )
            
            # 🔥 워크플로우 완료 후 리포트 감지 및 이벤트 전송
            await self._send_report_events_if_exists(streaming_callback)
            
            # 🔥 리포트 생성 완료 감지 및 UI 알림 (항상 수행, 강화된 예외 처리)
            logger.info(f"🔍 Orchestrator 결과 확인: success={result.get('success', False)}")
            try:
                import os
                import glob
                logger.info("🔍 Orchestrator 리포트 감지 시작")
                
                reports_dir = os.getenv('REPORTS_PATH', './reports')
                logger.info(f"🔍 리포트 디렉토리: {reports_dir}")
                
                report_files = glob.glob(os.path.join(reports_dir, "report_*.html"))
                logger.info(f"🔍 발견된 리포트 파일 수: {len(report_files)}")
                
                if report_files:
                    # 생성 시간 기준 최신 파일
                    latest_report = max(report_files, key=os.path.getctime)
                    logger.info(f"🎉 Orchestrator에서 최신 리포트 감지: {latest_report}")
                    
                    # 파일 크기 확인
                    file_size = os.path.getsize(latest_report)
                    logger.info(f"🔍 리포트 파일 크기: {file_size} bytes")
                    
                    # UI에 리포트 업데이트 알림
                    logger.info("🔍 send_report_update 호출 시작")
                    await streaming_callback.send_report_update(latest_report)
                    logger.info("🔍 send_report_update 완료")
                    
                    # HTML 파일 내용을 코드 뷰에 전송
                    logger.info("🔍 HTML 파일 읽기 시작")
                    with open(latest_report, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    logger.info(f"🔍 HTML 내용 읽기 완료: {len(html_content)} 문자")
                    
                    logger.info("🔍 send_code 호출 시작")
                    await streaming_callback.send_code(html_content)
                    logger.info("🎨 Orchestrator에서 HTML 코드를 UI로 전송 완료")
                else:
                    logger.warning("🔍 리포트 파일을 찾을 수 없음")
                    
            except Exception as e:
                logger.error(f"❌ Orchestrator 리포트 알림 실패: {e}")
                import traceback
                logger.error(f"❌ 예외 상세: {traceback.format_exc()}")
            
            logger.info(f"✅ Orchestrator 쿼리 처리 완료: {session_id}")
            return result
            
        except asyncio.CancelledError:
            logger.info(f"🛑 쿼리 처리 취소됨: {session_id}")
            return {"success": False, "error": "중단됨", "analysis": "", "report_content": ""}
        except Exception as e:
            logger.error(f"❌ 쿼리 처리 실패: {e}")
            return {"success": False, "error": str(e), "analysis": "", "report_content": ""}

    async def process_query(self, user_query: str, session_id: str, **kwargs) -> Dict[str, Any]:
        """스트리밍 API를 위한 쿼리 처리 메서드"""
        
        try:
            logger.info(f"🔍 쿼리 처리 시작: {user_query} (세션: {session_id})")
            start_time = datetime.now()
            
            # LangGraph 워크플로우 실행
            result = await self.langgraph_workflow.run(user_query)
            
            # 🔥 워크플로우 완료 후 리포트 감지 및 이벤트 전송 (kwargs에서 streaming_callback 가져오기)
            streaming_callback = kwargs.get('streaming_callback')
            await self._send_report_events_if_exists(streaming_callback)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ 쿼리 처리 완료: {session_id} (소요시간: {duration:.2f}초)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 쿼리 처리 실패 ({session_id}): {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis": "",
                "report_content": ""
            }

    async def _send_report_events_if_exists(self, streaming_callback):
        """워크플로우 완료 후 리포트 파일을 감지하고 UI에 이벤트 전송"""
        try:
            import os
            import glob
            
            reports_dir = os.getenv('REPORTS_PATH', './reports')
            report_files = glob.glob(os.path.join(reports_dir, "report_*.html"))
            
            if report_files:
                # 생성 시간 기준 최신 파일
                latest_report = max(report_files, key=os.path.getctime)
                logger.info(f"🎉 orchestrator에서 최신 리포트 감지: {latest_report}")
                
                # HTML 파일 내용 읽기
                with open(latest_report, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # 스트리밍 콜백으로 UI에 이벤트 전송
                if streaming_callback:
                    # 1. HTML 코드 이벤트 전송
                    await streaming_callback.send_code(html_content, os.path.basename(latest_report))
                    
                    # 2. 리포트 업데이트 이벤트 전송
                    await streaming_callback.send_report_update(latest_report)
                    
                    logger.info("🎨 orchestrator에서 HTML 코드 및 리포트 업데이트 이벤트 전송 완료")
                else:
                    logger.warning("⚠️ streaming_callback이 None이므로 이벤트 전송 불가")
                    
        except Exception as e:
            logger.error(f"❌ orchestrator 리포트 이벤트 전송 실패: {e}")

    def health_check(self) -> Dict[str, str]:
        """헬스 체크"""
        try:
            # 각 컴포넌트 상태 확인
            status = {
                "orchestrator": "healthy",
                "llm_client": "healthy" if self.llm_client else "unhealthy",
                "mcp_client": "healthy" if self.mcp_client else "unhealthy",
                "langgraph_workflow": "healthy" if self.langgraph_workflow else "unhealthy"
            }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ 헬스 체크 실패: {e}")
            return {"error": str(e)} 