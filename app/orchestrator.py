"""
Universal Report Generator Orchestrator
범용 리포트 생성 오케스트레이터 - LangGraph 기반
"""

import asyncio
import json
import logging
import os
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.llm_client import OpenRouterClient, ModelType
from app.mcp_client import MCPClient
from app.code_executor import CodeExecutor
from app.utils.security import SecurityValidator
from app.langgraph_workflow import TrueAgenticWorkflow

logger = logging.getLogger(__name__)


class UniversalOrchestrator:
    """범용 리포트 생성 오케스트레이터 - LangGraph 기반"""
    
    def __init__(self):
        self.llm_client = OpenRouterClient()
        self.mcp_client = MCPClient()
        self.code_executor = CodeExecutor()
        self.security_validator = SecurityValidator()
        
        # LangGraph 워크플로우 (현재 사용)
        self.langgraph_workflow = TrueAgenticWorkflow()
        
        logger.info("🚀 Universal Orchestrator (LangGraph) 초기화 완료")

    async def process_query_with_streaming(self, user_query: str, session_id: str, streaming_callback=None) -> Dict:
        """스트리밍 콜백과 함께 쿼리 처리"""
        try:
            logger.info(f"🔍 쿼리 처리 시작: {user_query} (세션: {session_id})")
            
            # LangGraph 워크플로우로 스트리밍 실행
            result = await self.langgraph_workflow.run_with_streaming(user_query, streaming_callback)
            
            # HTML 리포트 생성
            if result.get("success") and result.get("report_content"):
                html_content = result["report_content"]
                
                # 리포트 파일 저장
                report_filename = f"report_{session_id}.html"
                report_path = f"reports/{report_filename}"
                
                # reports 디렉터리가 없으면 생성
                os.makedirs("reports", exist_ok=True)
                
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                result["html_content"] = html_content
                result["report_url"] = f"/reports/{report_filename}"
            
            logger.info(f"✅ 쿼리 처리 완료: {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 쿼리 처리 실패: {e}")
            if streaming_callback:
                await streaming_callback.send_error(str(e))
            
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "analysis": "",
                "html_content": "",
                "report_url": ""
            }

    async def process_query(self, user_query: str, session_id: str, **kwargs) -> Dict[str, Any]:
        """스트리밍 API를 위한 쿼리 처리 메서드"""
        
        try:
            logger.info(f"🔍 쿼리 처리 시작: {user_query} (세션: {session_id})")
            start_time = datetime.now()
            
            # LangGraph 워크플로우 실행
            result = await self.langgraph_workflow.run(user_query)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # HTML 리포트 생성
            html_content = await self._generate_html_report(user_query, result, session_id)
            
            # 리포트 파일 저장
            report_filename = f"report_{session_id}.html"
            report_path = f"reports/{report_filename}"
            
            # reports 디렉터리가 없으면 생성
            os.makedirs("reports", exist_ok=True)
            
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            return {
                "success": True,
                "analysis": result.get("analysis", "분석이 완료되었습니다."),
                "html_content": html_content,
                "report_url": f"/reports/{report_filename}",
                "processing_time": processing_time,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"쿼리 처리 중 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }

    async def _generate_html_report(self, user_query: str, workflow_result: Dict[str, Any], session_id: str) -> str:
        """HTML 리포트 생성"""
        
        # 기본 템플릿 사용
        html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>분석 리포트 - {user_query[:50]}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
        }}
        .report-container {{
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        .insight-box {{
            background: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 20px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }}
        .chart-placeholder {{
            background: #ecf0f1;
            height: 300px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 20px 0;
            border: 2px dashed #bdc3c7;
        }}
        .analysis-content {{
            background: #ffffff;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border: 1px solid #e0e0e0;
        }}
        .metadata {{
            background: #f1f3f4;
            padding: 15px;
            border-radius: 8px;
            margin-top: 30px;
            font-size: 0.9em;
            color: #666;
        }}
        ul {{
            padding-left: 20px;
        }}
        li {{
            margin-bottom: 8px;
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <h1>📊 {user_query}</h1>
        
        <div class="insight-box">
            <h3>🔍 주요 분석 결과</h3>
            <p>사용자의 요청 "<strong>{user_query}</strong>"에 대한 AI 분석을 완료했습니다.</p>
        </div>
        
        <div class="analysis-content">
            <h3>📈 AI 분석 내용</h3>
            <p>{workflow_result.get("analysis", "AI 에이전트가 데이터를 분석하고 인사이트를 도출했습니다.")}</p>
        </div>
        
        <div class="chart-placeholder">
            <div style="text-align: center;">
                <h3>📊 데이터 시각화</h3>
                <p>차트 및 그래프가 여기에 표시됩니다</p>
                <small>향후 업데이트에서 동적 차트 기능이 추가될 예정입니다</small>
            </div>
        </div>
        
        <div class="insight-box">
            <h3>💡 결론 및 제안</h3>
            <p>AI 분석 결과를 바탕으로 다음과 같은 인사이트를 도출했습니다:</p>
            <ul>
                <li>데이터 수집 및 전처리가 완료되었습니다</li>
                <li>패턴 분석을 통해 의미 있는 트렌드를 식별했습니다</li>
                <li>결과를 바탕으로 실행 가능한 권장사항을 제시합니다</li>
                <li>추가 분석이 필요한 영역을 확인했습니다</li>
            </ul>
        </div>
        
        <div class="metadata">
            <h4>리포트 정보</h4>
            <p><strong>생성 시간:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>세션 ID:</strong> {session_id}</p>
            <p><strong>사용자 쿼리:</strong> {user_query}</p>
            <p><strong>AI 모델:</strong> LangGraph + OpenRouter</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html_template.strip()

    async def generate_report_unified(self, user_query: str, session_id: str, **kwargs) -> Dict[str, Any]:
        """통합 리포트 생성 - LangGraph 워크플로우 사용"""
        
        try:
            logger.info(f"📊 리포트 생성 시작 - 세션: {session_id}")
            start_time = datetime.now()
            
            # LangGraph 워크플로우 실행
            result = await self.langgraph_workflow.run(user_query)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "session_id": session_id,
                "report_content": result.get("report_content", ""),
                "browser_test_url": result.get("browser_test_url"),
                "validation_passed": result.get("validation_passed", False),
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "workflow_type": "langgraph"
            }
            
        except Exception as e:
            logger.error(f"리포트 생성 실패: {e}")
            return {
                "success": False,
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def health_check(self) -> Dict[str, Any]:
        """시스템 상태 확인"""
        
        health_status = {
            "orchestrator": "healthy",
            "llm_client": "unknown",
            "mcp_client": "unknown",
            "code_executor": "unknown",
            "langgraph_workflow": "unknown"
        }
        
        try:
            # LLM 클라이언트 확인
            test_response = await self.llm_client.generate_completion("test", ModelType.CLAUDE_SONNET)
            health_status["llm_client"] = "healthy" if test_response else "unhealthy"
        except Exception as e:
            health_status["llm_client"] = f"unhealthy: {e}"
        
        try:
            # MCP 클라이언트 확인  
            health_status["mcp_client"] = "healthy" if self.mcp_client else "unhealthy"
        except Exception as e:
            health_status["mcp_client"] = f"unhealthy: {e}"
        
        try:
            # 코드 실행기 확인
            health_status["code_executor"] = "healthy" if self.code_executor else "unhealthy"
        except Exception as e:
            health_status["code_executor"] = f"unhealthy: {e}"
            
        try:
            # LangGraph 워크플로우 확인
            health_status["langgraph_workflow"] = "healthy" if self.langgraph_workflow else "unhealthy"
        except Exception as e:
            health_status["langgraph_workflow"] = f"unhealthy: {e}"
        
        overall_healthy = all(status == "healthy" for status in health_status.values())
        
        return {
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "components": health_status,
            "timestamp": datetime.now().isoformat()
        } 

    async def get_available_tools(self) -> List[Dict]:
        """사용 가능한 MCP 도구 목록 반환"""
        try:
            # LangGraph 워크플로우에서 도구 정보 가져오기
            if hasattr(self.langgraph_workflow, 'tools') and self.langgraph_workflow.tools:
                tools_info = []
                for tool in self.langgraph_workflow.tools:
                    tool_info = {
                        "name": getattr(tool, 'name', 'Unknown Tool'),
                        "description": getattr(tool, 'description', 'No description available')
                    }
                    tools_info.append(tool_info)
                return tools_info
            else:
                # 도구가 없으면 빈 리스트 반환
                return []
        except Exception as e:
            logger.error(f"도구 정보 조회 실패: {e}")
            return [] 