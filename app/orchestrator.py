import asyncio
import time
import uuid
import logging
import re
import json
from typing import Dict, List, Optional, Any
from .llm_client import OpenRouterClient, ModelType
from .mcp_client import MCPClient
from .code_executor import CodeExecutor
from .utils.templates import PromptTemplates
from .utils.security import SecurityValidator

logger = logging.getLogger(__name__)

class ReportOrchestrator:
    def __init__(self, llm_client: OpenRouterClient, mcp_client: MCPClient):
        self.llm_client = llm_client
        self.mcp_client = mcp_client
        self.code_executor = CodeExecutor()
        self.prompt_templates = PromptTemplates()
        self.security_validator = SecurityValidator()
        
    async def process_request(
        self, 
        user_query: str, 
        session_id: Optional[str] = None,
        data_sources: Optional[List[str]] = None,
        mcp_tools: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """메인 처리 로직"""
        start_time = time.time()
        
        try:
            # 1. 입력 검증
            if not self.security_validator.validate_user_query(user_query):
                return {
                    "success": False,
                    "error_message": "유효하지 않은 요청입니다.",
                    "processing_time": time.time() - start_time
                }
            
            # 2. 세션 ID 생성
            if not session_id:
                session_id = str(uuid.uuid4())
            
            logger.info(f"리포트 생성 시작 - 세션: {session_id}")
            
            # 3. MCP 데이터 수집
            context_data = await self._collect_mcp_data(user_query, mcp_tools)
            
            # 4. 프롬프트 생성
            prompt = self.prompt_templates.build_generation_prompt(
                user_query=user_query,
                context_data=context_data,
                session_id=session_id
            )
            
            # 5. 코드 생성 (Qwen 사용)
            llm_response = await self.llm_client.generate_code(
                prompt=prompt,
                model_type=ModelType.QWEN_CODER,
                max_tokens=4000,
                temperature=0.1
            )
            
            # 6. 코드 추출
            logger.info(f"LLM 응답 받음 - 세션: {session_id}, 응답 길이: {len(llm_response)}")
            logger.info(f"LLM 응답 미리보기 (처음 500자):\n{llm_response[:500]}...")
            
            # LLM 응답을 파일로 저장 (디버깅용)
            try:
                with open(f"/tmp/llm_response_{session_id}.txt", "w", encoding="utf-8") as f:
                    f.write(llm_response)
                logger.info(f"LLM 응답을 파일로 저장: /tmp/llm_response_{session_id}.txt")
            except Exception as e:
                logger.warning(f"LLM 응답 파일 저장 실패: {e}")
            
            extracted_code = self._extract_code_blocks(llm_response)
            
            # 추출된 코드를 파일로 저장 (디버깅용)
            try:
                with open(f"/tmp/extracted_code_{session_id}.json", "w", encoding="utf-8") as f:
                    json.dump(extracted_code, f, ensure_ascii=False, indent=2)
                logger.info(f"추출된 코드를 파일로 저장: /tmp/extracted_code_{session_id}.json")
            except Exception as e:
                logger.warning(f"추출된 코드 파일 저장 실패: {e}")
            
            # 7. 코드 실행
            logger.info(f"추출된 코드 확인 - 세션: {session_id}")
            logger.info(f"Python 코드 존재: {extracted_code.get('python_code') is not None}")
            logger.info(f"HTML 코드 존재: {extracted_code.get('html_code') is not None}")
            logger.info(f"JavaScript 코드 존재: {extracted_code.get('javascript_code') is not None}")
            
            if extracted_code.get('python_code'):
                logger.info(f"Python 코드 (처음 300자):\n{extracted_code['python_code'][:300]}...")
            else:
                logger.warning(f"Python 코드가 추출되지 않았습니다!")
                logger.info(f"전체 응답:\n{llm_response}")
            
            try:
                logger.info(f"코드 실행기 호출 시작 - 세션: {session_id}")
                logger.info(f"전달할 컨텍스트 데이터: {type(context_data)}, 키: {list(context_data.keys()) if isinstance(context_data, dict) else 'N/A'}")
                
                execution_result = await self.code_executor.execute_code(
                    code=extracted_code,
                    session_id=session_id,
                    context_data=context_data
                )
                
                logger.info(f"코드 실행기 호출 완료 - 세션: {session_id}")
                logger.info(f"실행 결과: success={execution_result.get('success')}")
                if not execution_result.get('success'):
                    logger.error(f"실행 실패 이유: {execution_result.get('error', 'Unknown')}")
                    
            except Exception as executor_error:
                logger.error(f"코드 실행기 호출 중 예외 발생 - 세션: {session_id}")
                logger.error(f"예외 타입: {type(executor_error).__name__}")
                logger.error(f"예외 메시지: {str(executor_error)}")
                logger.error(f"예외 repr: {repr(executor_error)}")
                import traceback
                logger.error(f"예외 스택 트레이스:\n{traceback.format_exc()}")
                
                execution_result = {
                    "success": False,
                    "error": f"코드 실행기 호출 실패: {str(executor_error)}",
                    "output": ""
                }
            
            # 8. 결과 처리
            if execution_result["success"]:
                report_url = f"/reports/{execution_result['report_filename']}"
                return {
                    "success": True,
                    "report_url": report_url,
                    "session_id": session_id,
                    "processing_time": time.time() - start_time
                }
            else:
                # 9. 오류 시 Claude로 수정 시도
                return await self._handle_execution_error(
                    llm_response, execution_result, user_query, context_data, session_id, start_time
                )
                
        except Exception as e:
            logger.error(f"리포트 생성 중 오류 발생: {e}")
            return {
                "success": False,
                "error_message": f"리포트 생성 중 오류가 발생했습니다: {str(e)}",
                "session_id": session_id,
                "processing_time": time.time() - start_time
            }
    
    async def _collect_mcp_data(self, user_query: str, mcp_tools: Optional[List[str]] = None) -> Dict[str, Any]:
        """MCP 서버에서 데이터를 수집합니다."""
        context_data = {
            "_metadata": {
                "query": user_query,
                "collected_at": time.time(),
                "sources": []
            }
        }
        
        try:
            # 사용 가능한 서버 목록 조회
            server_status = self.mcp_client.get_server_status()
            
            for server_name, is_active in server_status.items():
                if not is_active:
                    continue
                    
                try:
                    # 서버의 도구 목록 조회
                    available_tools = await self.mcp_client.list_tools(server_name)
                    
                    if mcp_tools:
                        # 특정 도구만 사용
                        tools_to_use = [t for t in available_tools if t.get("name") in mcp_tools]
                    else:
                        # 자동으로 적절한 도구 선택
                        tools_to_use = self._select_relevant_tools(user_query, available_tools)
                    
                    # 선택된 도구 실행
                    for tool in tools_to_use:
                        tool_name = tool.get("name")
                        if not tool_name:
                            continue
                            
                        tool_args = self._generate_tool_arguments(user_query, tool)
                        
                        result = await self.mcp_client.call_tool(server_name, tool_name, tool_args)
                        
                        if result:
                            context_data[f"{server_name}_{tool_name}"] = result
                            context_data["_metadata"]["sources"].append({
                                "server": server_name,
                                "tool": tool_name,
                                "args": tool_args
                            })
                            
                except Exception as e:
                    logger.warning(f"MCP 서버 {server_name} 데이터 수집 실패: {e}")
                    
        except Exception as e:
            logger.error(f"MCP 데이터 수집 중 오류: {e}")
            
        return context_data
    
    def _select_relevant_tools(self, user_query: str, available_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """사용자 쿼리와 관련된 도구를 선택합니다."""
        query_lower = user_query.lower()
        relevant_tools = []
        
        # 키워드 기반 매칭
        keyword_mapping = {
            "file": ["read", "list", "search", "find"],
            "data": ["read", "query", "search", "get"],
            "database": ["query", "select", "find"],
            "web": ["scrape", "fetch", "get"],
            "api": ["call", "get", "post", "fetch"]
        }
        
        for tool in available_tools:
            tool_name = tool.get("name", "").lower()
            tool_description = tool.get("description", "").lower()
            
            # 키워드 매칭으로 관련 도구 찾기
            for keyword, actions in keyword_mapping.items():
                if keyword in query_lower:
                    if any(action in tool_name or action in tool_description for action in actions):
                        relevant_tools.append(tool)
                        break
        
        # 관련 도구가 없으면 기본 도구 사용
        if not relevant_tools and available_tools:
            relevant_tools = available_tools[:2]  # 처음 2개 도구만 사용
            
        return relevant_tools
    
    def _generate_tool_arguments(self, user_query: str, tool_definition: Dict[str, Any]) -> Dict[str, Any]:
        """도구 호출을 위한 인수를 생성합니다."""
        args = {}
        
        # 도구 스키마에서 필수 인수 추출
        input_schema = tool_definition.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        
        for prop_name, prop_def in properties.items():
            prop_type = prop_def.get("type", "string")
            
            # 사용자 쿼리에서 인수 추출 시도
            if prop_name in ["query", "search", "term"]:
                args[prop_name] = user_query
            elif prop_name in ["path", "directory"]:
                args[prop_name] = "/app/data"  # 기본 경로
            elif prop_name in ["limit", "max_results"]:
                args[prop_name] = 10  # 기본 제한
            elif prop_def.get("default") is not None:
                args[prop_name] = prop_def["default"]
                
        return args
    
    def _extract_code_blocks(self, llm_response: str) -> Dict[str, Any]:
        """LLM 응답에서 코드 블록을 추출합니다."""
        
        # Python 코드 블록 추출
        python_pattern = r'```python\n(.*?)\n```'
        python_matches = re.findall(python_pattern, llm_response, re.DOTALL)
        
        # HTML 코드 블록 추출
        html_pattern = r'```html\n(.*?)\n```'
        html_matches = re.findall(html_pattern, llm_response, re.DOTALL)
        
        # JavaScript 코드 블록 추출
        js_pattern = r'```javascript\n(.*?)\n```'
        js_matches = re.findall(js_pattern, llm_response, re.DOTALL)
        
        return {
            "python_code": python_matches[0] if python_matches else None,
            "html_code": html_matches[0] if html_matches else None,
            "javascript_code": js_matches[0] if js_matches else None,
            "explanation": self._extract_explanation(llm_response),
            "full_response": llm_response
        }
    
    def _extract_explanation(self, llm_response: str) -> str:
        """LLM 응답에서 설명 텍스트를 추출합니다."""
        # 코드 블록이 아닌 부분을 설명으로 간주
        explanation = re.sub(r'```.*?```', '', llm_response, flags=re.DOTALL)
        return explanation.strip()
    
    async def _handle_execution_error(
        self, 
        original_response: str, 
        error_result: Dict[str, Any], 
        user_query: str, 
        context_data: Dict[str, Any], 
        session_id: str,
        start_time: float
    ) -> Dict[str, Any]:
        """코드 실행 오류 시 Claude를 사용하여 수정을 시도합니다."""
        
        logger.info(f"코드 실행 실패, Claude로 수정 시도 - 세션: {session_id}")
        
        try:
            # Claude를 사용하여 코드 수정
            fixed_response = await self.llm_client.analyze_and_fix_code(
                original_code=original_response,
                error_message=error_result.get("error_message", ""),
                user_query=user_query
            )
            
            # 수정된 코드 추출
            fixed_code = self._extract_code_blocks(fixed_response)
            
            # 수정된 코드 실행
            execution_result = await self.code_executor.execute_code(
                code=fixed_code,
                session_id=session_id,
                context_data=context_data
            )
            
            if execution_result["success"]:
                report_url = f"/reports/{execution_result['report_filename']}"
                return {
                    "success": True,
                    "report_url": report_url,
                    "session_id": session_id,
                    "processing_time": time.time() - start_time,
                    "fixed_by_claude": True
                }
                
        except Exception as e:
            logger.error(f"Claude 코드 수정 실패: {e}")
            
        return {
            "success": False,
            "error_message": "코드 실행에 실패했습니다. 요청을 다시 시도해주세요.",
            "session_id": session_id,
            "processing_time": time.time() - start_time,
            "original_error": error_result.get("error_message", ""),
            "logs": error_result.get("logs", "")
        }
    
    async def get_available_data_sources(self) -> List[Dict[str, Any]]:
        """사용 가능한 데이터 소스 목록을 반환합니다."""
        sources = []
        
        try:
            server_status = self.mcp_client.get_server_status()
            
            for server_name, is_active in server_status.items():
                if not is_active:
                    continue
                    
                try:
                    tools = await self.mcp_client.list_tools(server_name)
                    
                    sources.append({
                        "name": server_name,
                        "description": f"MCP 서버: {server_name}",
                        "available_tools": [tool.get("name") for tool in tools],
                        "status": "active" if is_active else "inactive"
                    })
                    
                except Exception as e:
                    logger.warning(f"서버 {server_name} 도구 목록 조회 실패: {e}")
                    
        except Exception as e:
            logger.error(f"데이터 소스 목록 조회 실패: {e}")
            
        return sources
    
    async def enhance_report(self, session_id: str, user_feedback: str) -> Dict[str, Any]:
        """사용자 피드백을 바탕으로 리포트를 개선합니다."""
        
        start_time = time.time()
        
        try:
            # 기존 리포트 내용 읽기 (구현 필요)
            # 여기서는 간단히 새로운 리포트 생성
            
            enhanced_response = await self.llm_client.enhance_report(
                basic_report="기존 리포트 내용",  # 실제로는 파일에서 읽어야 함
                user_feedback=user_feedback
            )
            
            # 개선된 코드 추출 및 실행
            enhanced_code = self._extract_code_blocks(enhanced_response)
            
            execution_result = await self.code_executor.execute_code(
                code=enhanced_code,
                session_id=f"{session_id}_enhanced",
                context_data={}
            )
            
            if execution_result["success"]:
                report_url = f"/reports/{execution_result['report_filename']}"
                return {
                    "success": True,
                    "report_url": report_url,
                    "session_id": f"{session_id}_enhanced",
                    "processing_time": time.time() - start_time
                }
                
        except Exception as e:
            logger.error(f"리포트 개선 실패: {e}")
            
        return {
            "success": False,
            "error_message": "리포트 개선에 실패했습니다.",
            "processing_time": time.time() - start_time
        } 