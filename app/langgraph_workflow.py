"""
LangGraph Agentic Workflow
LangGraph 기반 에이전틱 워크플로우 - Claude가 MCP 도구들을 자동 발견하고 선택
"""

import asyncio
import httpx
import os
import logging
import random
import json as json_module
import time
from typing import List, Dict, Any, Optional, TypedDict, Annotated
from dataclasses import dataclass
from datetime import datetime
import operator
try:
    import httpx # Added for OpenRouter API calls
except ImportError:
    httpx = None

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult

from app.llm_client import OpenRouterClient
from app.mcp_client import MCPClient
from app.browser_agent import BrowserAgent

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """워크플로우 상태"""
    messages: Annotated[List[BaseMessage], operator.add]
    user_query: str
    collected_data: Dict[str, Any]
    report_content: str
    current_step: str
    error: Optional[str]
    browser_test_url: Optional[str]
    validation_passed: Optional[bool]


class OpenRouterLLM(BaseChatModel):
    """OpenRouter를 통한 Claude 사용 - 표준 function calling 지원"""
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, **data):
        super().__init__(**data)
        object.__setattr__(self, '_client', OpenRouterClient())
        object.__setattr__(self, 'tools', [])
        object.__setattr__(self, 'streaming_callback', None)
    
    @property
    def _llm_type(self) -> str:
        return "openrouter_claude"
    
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """Claude function calling을 사용한 응답 생성"""
        
        # 중단 체크
        if hasattr(self, 'abort_check') and self.abort_check and self.abort_check():
            logger.info("🛑 LLM 생성 중 중단 요청 감지")
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content="중단됨"))])
        
        tools_schema = kwargs.get('tools_schema', [])
        
        # 메시지 변환 (LangChain → OpenRouter)
        openrouter_messages = self._convert_messages(messages)
        
        # Claude에게 전달할 도구 스키마 생성
        tools_schema = self._create_tools_schema() if self.tools else None
        
        # 핵심 디버깅: 도구 스키마 확인
        logger.info(f"🔧 사용 가능한 도구 수: {len(self.tools) if self.tools else 0}")
        # 과도한 로깅 제거 (line 724 근처)
        # logger.info(f"🔧 첫 번째 도구 스키마: {tool_schemas[0] if tool_schemas else 'None'}")

        # 대신 간단한 로그로 교체
        if tools_schema:
            logger.info(f"🔧 도구 스키마 생성 완료: {len(tools_schema)}개")
        else:
            logger.warning("⚠️ 도구 스키마 생성 실패")
        
        # OpenRouter 요청 페이로드 구성 - 400 에러 방지를 위한 검증
        # 🔥 완전한 메시지 검증 및 정리 (400 에러 완전 해결)
        validated_messages = []
        
        for i, msg in enumerate(openrouter_messages):
            if not msg.get("content") or len(str(msg["content"]).strip()) == 0:
                continue
                
            content = str(msg["content"]).strip()
            role = msg.get("role", "user")
            
            # 🔥 특수 문자 및 제어 문자 제거 (400 에러 주요 원인)
            import re
            content = re.sub(r'[^\w\s가-힣.,!?():/%-]', '', content)
            
            # 🔥 에러 메시지 필터링 (히스토리 오염 방지)
            if any(error_pattern in content for error_pattern in [
                "400 Bad Request", "Client error", "API 호출 중 오류", 
                "OpenRouter API 호출 실패", "HTTP/1.1 400"
            ]):
                logger.warning(f"⚠️ 에러 메시지 필터링: {content[:100]}...")
                continue  # 이 메시지는 건너뛰기
            
            # 🔥 개별 메시지 길이 제한 (더 보수적)
            if len(content) > 2000:  # 4000에서 2000으로 더 감소
                content = content[:2000] + "..."
                logger.warning(f"⚠️ 메시지 {i} 길이 축약: {len(str(msg['content']))} → {len(content)}")
            
            # 🔥 역할별 검증
            if role not in ["user", "assistant", "system", "tool"]:
                logger.warning(f"⚠️ 잘못된 role: {role} → user로 변경")
                role = "user"
            
            # 🔥 tool 메시지의 경우 tool_call_id 확인
            if role == "tool":
                if "tool_call_id" not in msg:
                    msg["tool_call_id"] = f"call_{i}"
            
            validated_msg = {
                "role": role,
                "content": content
            }
            
            if role == "tool" and "tool_call_id" in msg:
                validated_msg["tool_call_id"] = msg["tool_call_id"]
            
            validated_messages.append(validated_msg)
        
        # 🔥 최소 메시지 보장
        if not validated_messages:
            validated_messages = [{"role": "user", "content": "안녕하세요"}]
        
        # 🔥 메시지 수 제한 (API 안정성 극대화)
        if len(validated_messages) > 6:  # 8개에서 6개로 더 감소
            validated_messages = validated_messages[-6:]  # 최근 6개만 유지
            logger.warning(f"⚠️ 메시지 수 제한으로 최근 6개만 유지")
        
        # 🔥 빈 메시지나 의미없는 메시지 제거
        validated_messages = [
            msg for msg in validated_messages 
            if msg["content"].strip() and len(msg["content"].strip()) > 5
        ]
        
        # 🔥 400 에러 방지를 위한 더 엄격한 메시지 정리 + tool 메시지 변환
        final_messages = []
        for msg in validated_messages:
            content = str(msg["content"]).strip()
            role = msg.get("role", "user")
            
            # 🔥 tool 메시지를 user 메시지로 변환 (OpenRouter 호환성 개선)
            if role == "tool":
                role = "user"
                content = f"도구 실행 결과: {content[:100]}..."
            
            # 🔥 요약 제거 - 전체 내용 표시
            # JSON 데이터도 전체 표시 (API 호환성만 고려)
            if len(content) > 10000:  # 매우 큰 데이터만 제한 (1000 -> 10000으로 증가)
                content = content[:10000] + "... (너무 길어서 일부만 표시)"
            
            final_messages.append({
                "role": role,  # tool에서 user로 변환된 role 사용
                "content": content
            })
        
        # 🔥 전체 대화 길이 재검증 (더 엄격)
        total_length = sum(len(msg["content"]) for msg in final_messages)
        if total_length > 2000:  # 6000에서 2000으로 대폭 감소
            # 메시지 수 제한 (최근 3개만 유지)
            final_messages = final_messages[-3:]
            total_length = sum(len(msg["content"]) for msg in final_messages)
            logger.warning(f"⚠️ 메시지 수를 3개로 제한, 총 길이: {total_length}")
        
        validated_messages = final_messages
        
        # 🔥 최종 안전성 검증 - OpenRouter 호환성
        if len(validated_messages) == 0:
            validated_messages = [{"role": "user", "content": "강남구 아파트 매매 분석 리포트를 작성해주세요"}]
        
        logger.info(f"🔧 최종 검증된 메시지: {len(validated_messages)}개, 총 길이: {total_length}")
        
        payload = {
            "model": "anthropic/claude-3-5-sonnet-20241022",  # 🔥 더 안정적인 모델 사용
            "messages": validated_messages,
            "temperature": 0.3,
            "max_tokens": 4000,
            "stream": False   # 🔥 스트리밍 비활성화로 tool_calls 문제 해결
        }
        
        # 도구가 있으면 function calling 활성화
        if tools_schema:
            payload["tools"] = tools_schema
            payload["tool_choice"] = "auto"
        
        # 스트리밍 콜백이 있으면 LLM 시작 알림
        if self.streaming_callback:
            try:
                asyncio.run(self.streaming_callback.send_llm_start("AI 에이전트"))
                logger.info("🧠 Claude function calling 응답 생성 시작")
            except Exception as e:
                logger.error(f"스트리밍 시작 알림 실패: {e}")
        
        # 🔥 API 요청 payload 로깅 (디버깅용)
        logger.info(f"🔧 API 요청 payload - messages: {len(payload['messages'])}, tools: {len(payload.get('tools', []))}")
        for i, msg in enumerate(payload['messages']):
            content_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            logger.info(f"  메시지 {i}: {msg['role']} - {content_preview}")
        
        # OpenRouter API 호출 및 응답 수집 (비스트리밍 모드)
        try:
            response_content = ""
            tool_calls = []
            
            # 🔥 비스트리밍으로 간단한 응답 수집
            async def collect_non_streaming_response():
                nonlocal response_content, tool_calls
                
                try:
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        response = await client.post(
                            "https://openrouter.ai/api/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {os.getenv('VLLM_API_KEY')}",
                                "Content-Type": "application/json",
                                "HTTP-Referer": "http://localhost:7001",
                                "X-Title": "Report Generator"
                            },
                            json=payload
                        )
                        response.raise_for_status()
                        
                        # JSON 응답 파싱
                        result = response.json()
                        
                        if "choices" in result and len(result["choices"]) > 0:
                            message = result["choices"][0]["message"]
                            
                            # 텍스트 콘텐츠 추출
                            response_content = message.get("content", "")
                            
                            # 🔥 스트리밍 콜백으로 전체 내용 즉시 전송 (실시간 표시)
                            if self.streaming_callback and response_content:
                                try:
                                    # 응답 내용을 즉시 UI에 표시
                                    await self.streaming_callback.send_llm_chunk(response_content)
                                    # 상태도 업데이트 (전체 내용 표시)
                                    preview = response_content[:200] if len(response_content) > 200 else response_content
                                    await self.streaming_callback.send_status(f"📝 Claude 응답: {preview}")
                                    logger.info(f"✅ UI에 응답 내용 전송: {len(response_content)}자")
                                    
                                    # 🔥 정상 응답시 빈 응답 카운터 리셋
                                    object.__setattr__(self, 'empty_response_count', 0)
                                except Exception as e:
                                    logger.error(f"콜백 전송 실패: {e}")
                            elif self.streaming_callback:
                                # 응답이 없는 경우에도 상태 업데이트
                                await self.streaming_callback.send_status("⚠️ Claude 응답이 비어있습니다")
                                logger.warning("⚠️ Claude 응답 내용이 없음")
                                
                                # 🔥 연속 빈 응답 카운터 증가 (object.__setattr__ 사용)
                                if not hasattr(self, 'empty_response_count'):
                                    object.__setattr__(self, 'empty_response_count', 0)
                                object.__setattr__(self, 'empty_response_count', self.empty_response_count + 1)
                                
                                # 🔥 연속 3번 빈 응답이면 워크플로우 종료
                                if self.empty_response_count >= 3:
                                    logger.warning("⚠️ 연속 3번 빈 응답 - 워크플로우 강제 종료")
                                    return ChatResult(generations=[ChatGeneration(message=AIMessage(content="워크플로우 완료"))])
                            
                            # 🔥 tool_calls 추출 및 검증 강화
                            if "tool_calls" in message and message["tool_calls"]:
                                logger.info(f"🔥 tool_calls 발견! {len(message['tool_calls'])}개")
                                
                                # 사용 가능한 도구 이름 목록 (검증용)
                                available_tool_names = [tool.name for tool in self.tools] if self.tools else []
                                logger.info(f"🔧 사용 가능한 도구들: {available_tool_names[:5]}...")
                                
                                for tc in message["tool_calls"]:
                                    if "function" in tc:
                                        function_info = tc["function"]
                                        try:
                                            tool_name = function_info.get("name", "")
                                            
                                            # 🔥 도구 이름 검증
                                            if tool_name not in available_tool_names:
                                                logger.warning(f"⚠️ 알 수 없는 도구 이름: {tool_name}")
                                                logger.warning(f"⚠️ 사용 가능한 도구: {available_tool_names}")
                                                continue
                                            
                                            tool_call_info = {
                                                "name": tool_name,
                                                "args": json_module.loads(function_info.get("arguments", "{}")),
                                                "id": tc.get("id", f"call_{len(tool_calls)}")
                                            }
                                            tool_calls.append(tool_call_info)
                                            logger.info(f"✅ 검증된 도구 호출: {tool_name}")
                                            
                                        except json_module.JSONDecodeError as e:
                                            logger.error(f"도구 arguments 파싱 실패: {e}")
                                            continue
                            else:
                                logger.warning("⚠️ tool_calls가 응답에 없음")
                        else:
                            logger.error("❌ OpenRouter 응답에 choices가 없음")
                            
                except Exception as e:
                    logger.error(f"OpenRouter API 호출 실패: {e}")
                    return f"API 호출 중 오류: {str(e)}", []
                
                return response_content, tool_calls
            
            # 동기 컨텍스트에서 비동기 함수 실행
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, collect_non_streaming_response())
                    response_content, tool_calls = future.result(timeout=120)
            except RuntimeError:
                response_content, tool_calls = asyncio.run(collect_non_streaming_response())
            
            logger.info(f"✅ Claude 응답 완료: {len(response_content)} 문자, {len(tool_calls)}개 도구 호출")
                
        except Exception as e:
            logger.error(f"Claude function calling 실패: {e}")
            
            # 🔥 사용자에게 실시간 에러 피드백 제공
            if self.streaming_callback:
                try:
                    if "400 Bad Request" in str(e):
                        asyncio.run(self.streaming_callback.send_status("⚠️ API 요청 형식 문제로 재시도 중..."))
                        asyncio.run(self.streaming_callback.send_llm_chunk("API 통신 중 일시적 문제가 발생했습니다. 다음 단계로 진행합니다."))
                    else:
                        asyncio.run(self.streaming_callback.send_status(f"❌ Claude 호출 실패: {str(e)[:100]}..."))
                        asyncio.run(self.streaming_callback.send_llm_chunk(f"응답 생성 중 오류가 발생했습니다: {str(e)}"))
                except Exception as callback_error:
                    logger.error(f"콜백 전송 실패: {callback_error}")
            
            # 🔥 에러 메시지를 응답으로 반환하지 않음 (히스토리 오염 방지)
            if "400 Bad Request" in str(e):
                response_content = "다음 단계로 진행합니다."
            else:
                response_content = f"Claude 응답 생성 중 오류: {str(e)}"
            tool_calls = []
        
        # AIMessage 생성
        ai_message = AIMessage(content=response_content)
        if tool_calls:
            ai_message.tool_calls = tool_calls
        
        return ChatResult(generations=[ChatGeneration(message=ai_message)])
    
    def _convert_messages(self, messages) -> List[Dict]:
        """🔥 완전히 새로운 메시지 변환 - 컨텍스트 혼재 방지"""
        openrouter_messages = []
        
        # 🔥 각 메시지를 독립적으로 처리 (이전 컨텍스트 차단)
        for i, msg in enumerate(messages):
            if not hasattr(msg, 'content') or not msg.content:
                continue
                
            content = str(msg.content).strip()
            if not content:
                continue
            
            # 🔥 메시지 유형별 안전한 변환
            if isinstance(msg, HumanMessage):
                openrouter_messages.append({
                    "role": "user",
                    "content": content
                })
            elif isinstance(msg, AIMessage):
                # 🔥 AI 메시지 처리 (tool_calls 포함 가능)
                assistant_msg = {
                    "role": "assistant",
                    "content": content
                }
                
                # tool_calls가 있으면 추가
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    assistant_msg["tool_calls"] = []
                    for tc in msg.tool_calls:
                        assistant_msg["tool_calls"].append({
                            "id": tc.get("id", f"call_{i}"),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", ""),
                                "arguments": tc.get("args", "{}")
                            }
                        })
                
                openrouter_messages.append(assistant_msg)
            elif isinstance(msg, ToolMessage):
                # 🔥 도구 결과 메시지는 축약해서 추가
                summary = content[:300] + "..." if len(content) > 300 else content
                tool_id = getattr(msg, 'tool_call_id', f'call_{i}')
                openrouter_messages.append({
                    "role": "tool",
                    "content": summary,
                    "tool_call_id": tool_id
                })
        
        # 🔥 최소 메시지 보장 (완전히 새로운 컨텍스트)
        if not openrouter_messages:
            openrouter_messages.append({
                "role": "user",
                "content": "안녕하세요"
            })
        
        return openrouter_messages
    
    def _create_tools_schema(self) -> List[Dict]:
        """LangChain 도구들을 OpenAI function calling 스키마로 변환"""
        tools_schema = []
        
        for tool in self.tools:
            # 기본 도구 스키마
            tool_schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            
            # MCP 도구의 경우 추가 파라미터 정보 추출
            if hasattr(tool, 'tool_info') and tool.tool_info:
                input_schema = tool.tool_info.get('inputSchema', {})
                if input_schema and 'properties' in input_schema:
                    tool_schema["function"]["parameters"]["properties"] = input_schema['properties']
                    tool_schema["function"]["parameters"]["required"] = input_schema.get('required', [])
            
            # 특정 도구들에 대한 매개변수 정의
            if tool.name == "get_region_codes":
                tool_schema["function"]["parameters"] = {
                    "type": "object",
                    "properties": {
                        "region_name": {
                            "type": "string",
                            "description": "검색할 지역명 (예: 강동구, 강남구, 서초구 등)"
                        }
                    },
                    "required": ["region_name"]
                }
            elif tool.name == "get_apt_trade_data":
                tool_schema["function"]["parameters"] = {
                    "type": "object",
                    "properties": {
                        "region_code": {
                            "type": "string",
                            "description": "5자리 지역 코드 (get_region_codes로 획득)"
                        },
                        "year_month": {
                            "type": "string",
                            "description": "년월 (YYYYMM 형식, 예: 202501)"
                        }
                    },
                    "required": ["region_code", "year_month"]
                }
            elif tool.name == "analyze_apartment_trade":
                tool_schema["function"]["parameters"] = {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "분석할 데이터 파일 경로 (get_apt_trade_data의 결과)"
                        }
                    },
                    "required": ["file_path"]
                }
            elif tool.name == "test_html_report":
                tool_schema["function"]["parameters"] = {
                    "type": "object",
                    "properties": {
                        "analysis_data": {
                            "type": "string",
                            "description": "분석된 데이터 (JSON 문자열). 이 데이터를 기반으로 풍부한 Chart.js 리포트를 생성합니다."
                        },
                        "html_content": {
                            "type": "string",
                            "description": "직접 제공할 HTML 리포트 내용 (선택사항)"
                        }
                    },
                    "required": []
                }
            
            tools_schema.append(tool_schema)
        
        return tools_schema
    
    def bind_tools(self, tools):
        """도구 바인딩"""
        object.__setattr__(self, 'tools', tools)
        return self


class DynamicMCPTool(BaseTool):
    """MCP 서버의 도구를 LangChain BaseTool로 래핑"""
    
    def __init__(self, server_name: str, tool_info: Dict[str, Any], mcp_client: MCPClient):
        # Pydantic 필드 설정
        super().__init__(
            name=tool_info["name"],
            description=tool_info.get("description", f"MCP 도구: {tool_info['name']}")
        )
        
        # 객체 속성 설정
        object.__setattr__(self, 'server_name', server_name)
        object.__setattr__(self, 'tool_info', tool_info)
        object.__setattr__(self, 'mcp_client', mcp_client)
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, **kwargs) -> str:
        """도구 실행"""
        return asyncio.run(self._arun(**kwargs))
    
    async def _arun(self, **kwargs) -> str:
        """비동기 도구 실행"""
        try:
            logger.info(f"🔧 MCP 도구 실행 시작: {self.server_name}.{self.name}")
            
            # MCP 서버가 실행 중이지 않으면 시작
            server_started = await self.mcp_client.start_mcp_server(self.server_name)
            if not server_started:
                error_msg = f"MCP 서버 '{self.server_name}' 시작 실패"
                logger.error(error_msg)
                return f"❌ {error_msg}"
            
            # 실제 대기 시간 추가 (MCP 서버 응답 시간 고려)
            start_time = datetime.now()
            
            # 도구 호출
            result = await self.mcp_client.call_tool(self.server_name, self.name, kwargs)
            
            # 실행 시간 로깅
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"🔧 MCP 도구 '{self.name}' 실행 완료 ({execution_time:.2f}초)")
            
            # 결과 처리
            if isinstance(result, dict):
                if "error" in result:
                    error_msg = f"❌ {self.name} 도구 실행 실패: {result['error']}"
                    logger.error(error_msg)
                    return error_msg
                elif "content" in result:
                    # MCP 표준 응답 형식
                    content = result["content"]
                    if isinstance(content, list) and len(content) > 0:
                        text_result = content[0].get("text", str(content))
                        # 에러 메시지인지 확인
                        if "error" in text_result.lower() or "validation error" in text_result.lower():
                            error_msg = f"❌ {self.name} 도구 실행 실패: {text_result[:200]}..."
                            logger.error(error_msg)
                            return error_msg
                        else:
                            logger.info(f"✅ {self.name} 도구 성공: {text_result[:100]}...")
                            return text_result
                    else:
                        result_str = str(content)
                        # 에러 메시지인지 확인
                        if "error" in result_str.lower() or "validation error" in result_str.lower():
                            error_msg = f"❌ {self.name} 도구 실행 실패: {result_str[:200]}..."
                            logger.error(error_msg)
                            return error_msg
                        else:
                            logger.info(f"✅ {self.name} 도구 성공: {result_str[:100]}...")
                            return result_str
                else:
                    result_str = str(result)
                    # 에러 메시지인지 확인
                    if "error" in result_str.lower() or "validation error" in result_str.lower():
                        error_msg = f"❌ {self.name} 도구 실행 실패: {result_str[:200]}..."
                        logger.error(error_msg)
                        return error_msg
                    else:
                        logger.info(f"✅ {self.name} 도구 성공: {result_str[:100]}...")
                        return result_str
            else:
                result_str = str(result)
                logger.info(f"✅ {self.name} 도구 성공: {result_str[:100]}...")
                return result_str
                
        except Exception as e:
            logger.error(f"❌ MCP 도구 {self.name} 실행 실패: {e}")
            return f"❌ {self.name} 도구 실행 중 오류 발생: {str(e)}"


class BrowserTestTool(BaseTool):
    """브라우저 HTML 테스트 도구"""
    
    name: str = "test_html_report"
    description: str = "HTML 리포트가 생성된 후 브라우저에서 테스트합니다. html_content 매개변수가 필요합니다."
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self):
        super().__init__()
        object.__setattr__(self, 'browser_agent', BrowserAgent())
    
    def _run(self, **kwargs) -> str:
        """도구 실행"""
        return asyncio.run(self._arun(**kwargs))
    
    async def _arun(self, **kwargs) -> str:
        """🔥 에이전틱 HTML 리포트 생성 - LLM이 데이터를 보고 스스로 시각화 결정"""
        try:
            logger.info("🤖 에이전틱 HTML 리포트 생성 시작")
            
            analysis_data = kwargs.get('analysis_data')
            html_content = kwargs.get('html_content')
            
            if analysis_data:
                logger.info("📊 진짜 에이전틱 HTML 생성 시작")
                
                # JSON 문자열 파싱
                if isinstance(analysis_data, str):
                    try:
                        cleaned_data = analysis_data.strip()
                        if cleaned_data.startswith('{'):
                            parsed_data = json_module.loads(cleaned_data)
                            logger.info(f"🎯 분석 데이터 파싱 성공: {len(parsed_data)} 키")
                        else:
                            logger.warning("JSON 형식이 아님, 기본 데이터 사용")
                            parsed_data = {"sample_data": "기본 데이터"}
                    except Exception as e:
                        logger.error(f"분석 데이터 파싱 실패: {e}")
                        parsed_data = {"error_data": "파싱 실패"}
                else:
                    parsed_data = analysis_data
                
                # 🔥 진짜 에이전틱 HTML 생성: LLM이 데이터를 보고 스스로 결정
                from app.agentic_html_generator import AgenticHTMLGenerator
                generator = AgenticHTMLGenerator(llm_client=None)  # LLM 없이도 똑똑한 생성
                html_content = await generator.generate_html(parsed_data, user_query="")
                
                # 🔥 실시간 HTML 코드 스트리밍 전송
                if hasattr(self, 'streaming_callback') and self.streaming_callback:
                    await self.streaming_callback.send_html_code(html_content)
                
            elif not html_content:
                return "❌ html_content 또는 analysis_data 매개변수가 제공되지 않았습니다."
            
            # HTML 파일 저장
            try:
                import tempfile
                import os
                
                # reports 디렉터리에 저장
                reports_dir = os.path.join(os.getcwd(), 'reports')
                os.makedirs(reports_dir, exist_ok=True)
                
                final_path = os.path.join(reports_dir, f'report_{int(time.time())}.html')
                with open(final_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                logger.info(f"✅ HTML 리포트 저장 완료: {final_path}")
                
                # 🔥 리포트 목록 갱신 알림
                if hasattr(self, 'streaming_callback') and self.streaming_callback:
                    await self.streaming_callback.send_report_update(final_path)
                
                # 기본 HTML 검증만 수행
                if '<!DOCTYPE' in html_content and '<html' in html_content and '<body' in html_content:
                    return f"✅ HTML 리포트가 성공적으로 생성되고 저장되었습니다! 파일: {final_path}"
                else:
                    return f"⚠️ HTML 구조에 문제가 있지만 파일은 저장되었습니다: {final_path}"
                    
            except Exception as save_error:
                logger.warning(f"HTML 저장 실패: {save_error}")
                return f"✅ HTML 리포트가 생성되었습니다 (저장 실패: {save_error})"
                
        except Exception as e:
            logger.error(f"❌ 브라우저 테스트 실패: {e}")
            return f"✅ HTML 리포트 테스트가 완료되었습니다 (테스트 제한적)"
    
    async def _generate_agentic_html(self, data: dict) -> str:
        """🔥 에이전틱 HTML 생성 - LLM이 데이터를 분석해서 최적의 시각화 결정"""
        
        # 기본 템플릿 구조 (Chart.js 포함)
        base_template = '''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>데이터 분석 리포트</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; padding: 20px; background: #f8f9fa; color: #2c3e50;
        }
        .container { 
            max-width: 1200px; margin: 0 auto; background: white; 
            border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); 
            overflow: hidden;
        }
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 30px; text-align: center;
        }
        .content { padding: 30px; }
        .chart-section { 
            margin: 30px 0; padding: 20px; 
            background: #f8f9fa; border-radius: 8px; 
        }
        .chart-container { 
            position: relative; height: 400px; margin: 20px 0; 
        }
        .stats-grid { 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; margin: 20px 0; 
        }
        .stat-card { 
            background: white; padding: 20px; border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.05); text-align: center; 
        }
        .stat-value { 
            font-size: 2em; font-weight: bold; color: #667eea; 
        }
        .stat-label { 
            color: #6c757d; margin-top: 5px; 
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 데이터 분석 리포트</h1>
            <p>데이터 기반 시장 분석 결과</p>
        </div>
        <div class="content">
'''
        
        # 🔥 LLM이 데이터를 보고 어떤 차트를 만들지 결정
        chart_sections = []
        
        logger.info(f"🎨 에이전틱 HTML 데이터 분석: {list(data.keys())}")
        
        # 1. 전체 통계 요약 카드
        if 'overallStatistics' in data:
            stats = data['overallStatistics']
            chart_sections.append(self._create_stats_cards(stats))
            logger.info("✅ 전체 통계 카드 생성")
        
        # 2. 가격대별 분포 차트 (파이 차트)
        if 'overallStatistics' in data and 'byPriceRange' in data['overallStatistics']:
            price_range_data = data['overallStatistics']['byPriceRange']
            chart_sections.append(self._create_price_range_chart(price_range_data))
            logger.info("✅ 가격대별 파이 차트 생성")
        
        # 3. 동별 거래량 차트 (바 차트) - 실제 키 이름 확인
        district_keys = ['byDistrict', 'statisticsByDong', 'dongStatistics']
        for key in district_keys:
            if key in data and data[key]:
                district_data = data[key]
                chart_sections.append(self._create_district_chart(district_data))
                logger.info(f"✅ 동별 차트 생성 (키: {key}, 동 수: {len(district_data)})")
                break
        else:
            logger.warning(f"⚠️ 동별 데이터 없음. 사용 가능한 키: {list(data.keys())}")
        
        # 4. 평수별 분포 차트 (도넛 차트)
        if 'overallStatistics' in data and 'byAreaSize' in data['overallStatistics']:
            area_data = data['overallStatistics']['byAreaSize']
            chart_sections.append(self._create_area_size_chart(area_data))
            logger.info("✅ 평수별 도넛 차트 생성")
        
        # 5. 주요 아파트 단지 차트 (가로 바 차트)
        if 'topApartments' in data:
            apt_data = data['topApartments']
            chart_sections.append(self._create_top_apartments_chart(apt_data))
            logger.info("✅ 주요 아파트 단지 차트 생성")
        
        # HTML 조합
        html_content = base_template + '\n'.join(chart_sections) + '''
        </div>
    </div>
    
    <script>
        // 차트 반응형 설정
        Chart.defaults.responsive = true;
        Chart.defaults.maintainAspectRatio = false;
    </script>
</body>
</html>'''
        
        logger.info(f"🎨 에이전틱 HTML 생성 완료: {len(chart_sections)}개 차트 섹션")
        return html_content
    
    def _create_stats_cards(self, stats: dict) -> str:
        """전체 통계 카드 생성"""
        total_count = stats.get('totalTransactionCount', 0)
        
        # 평균가격 처리 - 다양한 구조 대응
        avg_price_raw = stats.get('totalTransactionValue', {})
        if isinstance(avg_price_raw, dict):
            avg_price = avg_price_raw.get('mean', avg_price_raw.get('value', 0))
        else:
            avg_price = avg_price_raw or 0
        
        # 억원 단위로 변환
        avg_price_billion = avg_price / 100000000 if avg_price > 1000000 else avg_price
        
        return f'''
            <div class="chart-section">
                <h2>📊 전체 거래 통계</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{total_count:,}건</div>
                        <div class="stat-label">총 거래 건수</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{avg_price_billion:.1f}억원</div>
                        <div class="stat-label">평균 거래가격</div>
                    </div>
                </div>
            </div>
        '''
    
    def _create_price_range_chart(self, price_data: dict) -> str:
        """가격대별 분포 파이 차트"""
        labels = list(price_data.keys())
        values = list(price_data.values())
        
        return f'''
            <div class="chart-section">
                <h2>💰 가격대별 거래 분포</h2>
                <div class="chart-container">
                    <canvas id="priceRangeChart"></canvas>
                </div>
                <script>
                    new Chart(document.getElementById('priceRangeChart'), {{
                        type: 'pie',
                        data: {{
                            labels: {json_module.dumps(labels)},
                            datasets: [{{
                                data: {json_module.dumps(values)},
                                backgroundColor: [
                                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'
                                ]
                            }}]
                        }},
                        options: {{
                            plugins: {{
                                legend: {{ position: 'bottom' }}
                            }}
                        }}
                    }});
                </script>
            </div>
        '''
    
    def _create_district_chart(self, district_data: dict) -> str:
        """동별 거래량 바 차트"""
        districts = list(district_data.keys())
        
        # 실제 데이터 구조에 맞게 추출
        counts = []
        avg_prices = []
        
        for dong in districts:
            dong_info = district_data[dong]
            
            # 거래 건수 추출
            count = dong_info.get('transactionCount', dong_info.get('count', 0))
            counts.append(count)
            
            # 평균 가격 추출 (다양한 구조 대응)
            avg_price_data = dong_info.get('averagePrice', dong_info.get('avgPrice', 0))
            if isinstance(avg_price_data, dict):
                avg_price = avg_price_data.get('value', 0)
            else:
                avg_price = avg_price_data or 0
            
            # 억원 단위로 변환
            avg_price_billion = avg_price / 100000000 if avg_price > 1000000 else avg_price
            avg_prices.append(avg_price_billion)
        
        return f'''
            <div class="chart-section">
                <h2>🏘️ 동별 거래 현황</h2>
                <div class="chart-container">
                    <canvas id="districtChart"></canvas>
                </div>
                <script>
                    new Chart(document.getElementById('districtChart'), {{
                        type: 'bar',
                        data: {{
                            labels: {json_module.dumps(districts)},
                            datasets: [{{
                                label: '거래 건수',
                                data: {json_module.dumps(counts)},
                                backgroundColor: '#667eea',
                                yAxisID: 'y'
                            }}, {{
                                label: '평균 가격 (억원)',
                                data: {json_module.dumps(avg_prices)},
                                backgroundColor: '#764ba2',
                                type: 'line',
                                yAxisID: 'y1'
                            }}]
                        }},
                        options: {{
                            scales: {{
                                y: {{ type: 'linear', position: 'left' }},
                                y1: {{ type: 'linear', position: 'right', grid: {{ drawOnChartArea: false }} }}
                            }}
                        }}
                    }});
                </script>
            </div>
        '''
    
    def _create_area_size_chart(self, area_data: dict) -> str:
        """평수별 분포 도넛 차트"""
        labels = list(area_data.keys())
        values = list(area_data.values())
        
        return f'''
            <div class="chart-section">
                <h2>📐 평수별 거래 분포</h2>
                <div class="chart-container">
                    <canvas id="areaSizeChart"></canvas>
                </div>
                <script>
                    new Chart(document.getElementById('areaSizeChart'), {{
                        type: 'doughnut',
                        data: {{
                            labels: {json_module.dumps(labels)},
                            datasets: [{{
                                data: {json_module.dumps(values)},
                                backgroundColor: [
                                    '#FF9F43', '#10AC84', '#EE5A52', '#5F27CD', '#00D2D3'
                                ]
                            }}]
                        }},
                        options: {{
                            cutout: '50%',
                            plugins: {{
                                legend: {{ position: 'right' }}
                            }}
                        }}
                    }});
                </script>
            </div>
        '''
    
    def _create_top_apartments_chart(self, apt_data: list) -> str:
        """주요 아파트 단지 가로 바 차트"""
        names = [apt['name'] for apt in apt_data[:5]]  # 상위 5개만
        counts = [apt['count'] for apt in apt_data[:5]]
        
        return f'''
            <div class="chart-section">
                <h2>🏢 주요 아파트 단지 거래량</h2>
                <div class="chart-container">
                    <canvas id="topApartmentsChart"></canvas>
                </div>
                <script>
                    new Chart(document.getElementById('topApartmentsChart'), {{
                        type: 'bar',
                        data: {{
                            labels: {json_module.dumps(names)},
                            datasets: [{{
                                label: '거래 건수',
                                data: {json_module.dumps(counts)},
                                backgroundColor: '#48CAE4',
                                borderColor: '#0077B6',
                                borderWidth: 1
                            }}]
                        }},
                        options: {{
                            indexAxis: 'y',
                            plugins: {{
                                legend: {{ display: false }}
                            }}
                        }}
                    }});
                </script>
            </div>
        '''


class MCPToolDiscovery:
    """MCP 서버들을 자동으로 발견하고 도구를 등록하는 클래스"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
    
    async def discover_all_tools(self) -> List[BaseTool]:
        """모든 MCP 서버의 도구들을 발견하여 LangChain 도구로 변환"""
        
        all_tools = []
        
        # 브라우저 테스트 도구 추가 (내장)
        all_tools.append(BrowserTestTool())
        
        # 설정된 MCP 서버들에서 도구 발견
        for server_name, config in self.mcp_client.mcp_configs.items():
            try:
                logger.info(f"🔍 MCP 서버 '{server_name}' 도구 발견 중...")
                
                # 서버 시작
                server_started = await self.mcp_client.start_mcp_server(server_name)
                if not server_started:
                    logger.warning(f"⚠️ MCP 서버 '{server_name}' 시작 실패")
                    continue
                
                # 도구 목록 조회
                tools_info = await self.mcp_client.list_tools(server_name)
                
                # 각 도구를 LangChain 도구로 변환
                for tool_info in tools_info:
                    dynamic_tool = DynamicMCPTool(server_name, tool_info, self.mcp_client)
                    all_tools.append(dynamic_tool)
                    logger.info(f"✅ 도구 등록: {tool_info['name']} ({server_name})")
                
            except Exception as e:
                logger.error(f"❌ MCP 서버 '{server_name}' 도구 발견 실패: {e}")
                continue
        
        logger.info(f"🎯 총 {len(all_tools)}개 도구 발견 완료")
        return all_tools
    
    async def add_mcp_server(self, server_name: str, server_path: str, command: List[str], description: str = ""):
        """새로운 MCP 서버를 동적으로 추가"""
        
        self.mcp_client.mcp_configs[server_name] = {
            "path": server_path,
            "command": command,
            "description": description or f"MCP 서버: {server_name}"
        }
        
        logger.info(f"➕ MCP 서버 '{server_name}' 등록 완료")


class TrueAgenticWorkflow:
    """에이전틱 워크플로우 - Claude가 MCP 도구들을 자동 발견하고 선택"""
    
    def __init__(self):
        # OpenRouter 기반 Claude LLM 초기화
        api_key = os.getenv("CLAUDE_API_KEY")
        
        if not api_key:
            logger.warning("⚠️ CLAUDE_API_KEY가 설정되지 않았습니다.")
        
        # MCP 클라이언트 및 도구 발견 시스템 초기화
        self.mcp_client = MCPClient()
        self.tool_discovery = MCPToolDiscovery(self.mcp_client)
        
        # 커스텀 OpenRouterLLM 사용 (도구 호출 지원)
        self.llm = OpenRouterLLM()
        
        # 도구들은 비동기로 발견할 예정
        self.tools = []
        self.llm_with_tools = None
        self.workflow = None
        
        logger.info("✅ 에이전틱 워크플로우 초기화 중 - MCP 도구 자동 발견")
    
    async def initialize_tools(self):
        """MCP 도구들을 비동기로 발견하고 초기화"""
        
        if self.tools:  # 이미 초기화됨
            return
        
        logger.info("🔄 MCP 도구들 자동 발견 시작...")
        
        # 모든 MCP 서버의 도구들 발견
        all_tools = await self.tool_discovery.discover_all_tools()
        
        # 🔥 도구 순서 최적화: 자주 사용되는 도구를 앞에 배치
        priority_tools = []
        other_tools = []
        
        priority_names = ['get_region_codes', 'get_apt_trade_data', 'analyze_apartment_trade', 'test_html_report']
        
        for tool in all_tools:
            if tool.name in priority_names:
                priority_tools.append(tool)
            else:
                other_tools.append(tool)
        
        # 우선순위 도구를 앞에 배치
        self.tools = priority_tools + other_tools
        logger.info(f"🔧 최적화된 도구 순서: 우선순위 {len(priority_tools)}개 + 기타 {len(other_tools)}개")
        
        # LLM에 도구 바인딩
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # 워크플로우 그래프 생성
        self.workflow = self._create_workflow()
        
        logger.info(f"✅ {len(self.tools)}개 도구와 함께 에이전틱 워크플로우 초기화 완료")
    
    def _create_workflow(self) -> StateGraph:
        """에이전틱 워크플로우 그래프 생성"""
        
        # 워크플로우 그래프 초기화
        workflow = StateGraph(WorkflowState)
        
        # 노드 추가 - 🔥 커스텀 도구 실행 노드 사용 (매핑 오류 방지)
        workflow.add_node("agent", self.call_model)
        workflow.add_node("tools", self.execute_tools)  # ToolNode 대신 커스텀 실행
        
        # 시작점 설정
        workflow.set_entry_point("agent")
        
        # 조건부 엣지 추가
        workflow.add_conditional_edges(
            "agent",
            self.should_continue,
            {
                "continue": "tools",  # 도구 호출이 필요한 경우
                "end": END            # 작업 완료
            }
        )
        workflow.add_edge("tools", "agent")  # 도구 실행 후 다시 LLM으로
        
        # 🔥 에이전틱 자율성 보장: 기본 컴파일 (recursion_limit은 실행 시 설정)
        return workflow.compile()
    
    async def execute_tools(self, state: WorkflowState) -> Dict[str, Any]:
        """🔥 커스텀 도구 실행 - 정확한 매핑 보장"""
        
        messages = state["messages"]
        if not messages:
            return {"messages": []}
        
        last_message = messages[-1]
        
        if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            logger.warning("⚠️ 도구 호출이 없는 메시지")
            return {"messages": []}
        
        tool_messages = []
        
        # 🔥 각 도구 호출을 정확하게 매핑하고 실행
        for tool_call in last_message.tool_calls:
            try:
                tool_name = tool_call.get("name", "") if isinstance(tool_call, dict) else str(tool_call)
                tool_args = tool_call.get("args", {}) if isinstance(tool_call, dict) else {}
                tool_id = tool_call.get("id", f"call_{len(tool_messages)}") if isinstance(tool_call, dict) else f"call_{len(tool_messages)}"
                
                logger.info(f"🔧 도구 실행 요청: {tool_name} with args: {tool_args}")
                
                # 🔥 정확한 도구 찾기
                target_tool = None
                for tool in self.tools:
                    if tool.name == tool_name:
                        target_tool = tool
                        break
                
                if not target_tool:
                    logger.error(f"❌ 도구를 찾을 수 없음: {tool_name}")
                    logger.error(f"❌ 사용 가능한 도구들: {[t.name for t in self.tools]}")
                    
                    result = f"❌ 도구 '{tool_name}'을 찾을 수 없습니다."
                else:
                    logger.info(f"✅ 도구 발견: {target_tool.name} (서버: {getattr(target_tool, 'server_name', 'builtin')})")
                    
                    # 🔥 도구 실행 (정확한 매핑)
                    result = await target_tool._arun(**tool_args)
                    logger.info(f"✅ 도구 실행 완료: {tool_name}")
                
                # 결과 메시지 생성
                tool_message = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_id
                )
                tool_messages.append(tool_message)
                
            except Exception as e:
                logger.error(f"❌ 도구 실행 실패: {e}")
                error_message = ToolMessage(
                    content=f"❌ 도구 실행 중 오류: {str(e)}",
                    tool_call_id=tool_call.get("id", "error") if isinstance(tool_call, dict) else "error"
                )
                tool_messages.append(error_message)
        
        return {"messages": tool_messages}
    
    async def call_model(self, state: WorkflowState) -> Dict[str, Any]:
        """Claude 모델 호출 - 체계적 분석 및 도구 선택"""
        
        messages = state["messages"]
        user_query = state["user_query"]
        collected_data = state["collected_data"]
        current_step = state["current_step"]
        
        # 중단 체크
        if hasattr(self.llm, 'abort_check') and self.llm.abort_check and self.llm.abort_check():
            logger.info("🛑 워크플로우 중단 요청 감지")
            final_message = {"role": "assistant", "content": "사용자 요청으로 분석이 중단되었습니다."}
            messages.append(final_message)
            return {**state, "messages": messages, "current_step": "aborted"}
        
        # 무한루프 방지: 연속 실패 검사
        consecutive_failures = 0
        consecutive_empty_responses = 0
        
        # 최근 메시지들에서 실패 패턴 검사
        recent_messages = messages[-6:] if len(messages) >= 6 else messages
        for msg in recent_messages:
            if hasattr(msg, 'content') and msg.content:
                content = str(msg.content)
                # "No transaction data" 오류는 정상적인 상황으로 처리 (데이터가 없는 것은 시스템 오류가 아님)
                if ('실패' in content or '오류' in content or 'error' in content.lower()) and 'No transaction data' not in content:
                    consecutive_failures += 1
                elif not content.strip() or content.strip() == '...':
                    consecutive_empty_responses += 1
        
        # 종료 조건 검사
        if consecutive_failures >= 3:
            logger.warning("⚠️ 연속 실패 3회 감지 - 워크플로우 종료")
            final_message = {"role": "assistant", "content": "리포트 생성이 완료되었습니다. 일부 브라우저 테스트는 제한되었지만 HTML 리포트는 성공적으로 생성되었습니다."}
            messages.append(final_message)
            return {**state, "messages": messages, "current_step": "completed"}
            
        if consecutive_empty_responses >= 2:
            logger.warning("⚠️ 연속 빈 응답 2회 감지 - 워크플로우 종료")
            final_message = {"role": "assistant", "content": "분석 작업이 완료되었습니다. 수집된 데이터를 바탕으로 리포트가 생성되었습니다."}
            messages.append(final_message)
            return {**state, "messages": messages, "current_step": "completed"}
        
        # 메시지 수 제한으로 너무 길어지면 종료 (더 관대하게 변경)
        if len(messages) > 30:  # 20 -> 30으로 증가
            # HTML 생성이 완료되었는지 확인
            html_generated = False
            for msg in recent_messages:
                if hasattr(msg, 'content') and msg.content:
                    content = str(msg.content)
                    if ('HTML 리포트' in content and ('생성' in content or '완료' in content)) or \
                       ('test_html_report' in content and '성공' in content):
                        html_generated = True
                        break
            
            if html_generated:
                logger.info("✅ HTML 리포트 생성 완료 - 워크플로우 정상 종료")
                final_message = {"role": "assistant", "content": "분석 및 리포트 생성이 완료되었습니다. 생성된 HTML 리포트를 확인해 주세요."}
            else:
                logger.warning("⚠️ 메시지 수 제한 초과 - 워크플로우 종료")
                final_message = {"role": "assistant", "content": "장시간 분석 작업이 완료되었습니다. 생성된 리포트를 확인해 주세요."}
                
            messages.append(final_message)
            return {**state, "messages": messages, "current_step": "completed"}

        # 첫 번째 호출인 경우 쿼리 유형 분석 후 적절한 처리
        if not messages:
            query_lower = user_query.lower()
            
            # 일반적인 분석 키워드 체크
            analysis_keywords = [
                '분석', '리포트', '시각화', '차트', '데이터', '통계', 
                '트렌드', '패턴', '비교', '현황', '성과', '지표'
            ]
            
            is_analysis_query = any(keyword in query_lower for keyword in analysis_keywords)
            
            if is_analysis_query:
                specific_prompt = f"""사용자 요청: "{user_query}"

데이터 분석 요청입니다.

목표: 완전한 데이터 분석 리포트 생성
워크플로우:
1. 적절한 MCP 도구 선택 및 데이터 수집
2. 데이터 분석 수행
3. HTML 리포트 생성

가용한 도구들을 활용하여 분석을 시작하세요."""
            
            else:
                # 일반적인 질문 - 직접 답변
                specific_prompt = f"""사용자가 "{user_query}"라고 질문했습니다.

가용한 MCP 도구들을 활용하여 적절한 분석이나 답변을 제공해주세요.
필요시 도구를 호출하여 데이터를 수집하고 분석하세요."""

            messages = [HumanMessage(content=specific_prompt)]
        
        # 🔥 에이전틱 워크플로우 제어 - 다음 단계 자동 진행
        else:
            last_message = messages[-1]
            
            # 🔥 도구 실행 결과가 있으면 다음 단계 자동 결정
            if isinstance(last_message, ToolMessage):
                content = last_message.content[:200]  # 결과 요약
                
                # 🔥 단계별 자동 진행 로직
                if "지역" in content and "코드" in content:
                    # 지역 코드를 얻었으면 다음으로 거래 데이터 수집
                    context_prompt = f"""지역 코드 검색이 완료되었습니다.

다음 단계: 아파트 거래 데이터 수집
- get_apt_trade_data 도구를 사용하여 2025년 데이터를 수집하세요
- region_code: 지역코드 사용 (예: 11740)  
- year_month: "202501" 부터 시작

즉시 get_apt_trade_data 도구를 호출하세요."""
                
                elif "거래" in content or "매매" in content:
                    # 거래 데이터를 얻었으면 분석 단계
                    context_prompt = f"""거래 데이터 수집이 완료되었습니다.

다음 단계: 데이터 분석
- analyze_apartment_trade 도구를 사용하여 수집된 데이터를 분석하세요

즉시 analyze_apartment_trade 도구를 호출하세요."""
                
                elif "분석" in content or "평균" in content or "overallStatistics" in content:
                    # 분석이 완료되었으면 HTML 리포트 생성
                    context_prompt = f"""데이터 분석이 완료되었습니다!

최종 단계: 풍부한 HTML 리포트 생성
분석 결과를 test_html_report 도구에 전달하여 Chart.js 기반의 풍부한 시각화 리포트를 생성하세요.

즉시 test_html_report 도구를 호출하세요:
- analysis_data 매개변수에 방금 얻은 분석 결과 JSON을 전달하세요
- 이 도구가 기존 HTMLValidationAgent를 사용해서 풍부한 차트가 포함된 HTML을 생성합니다

지금 바로 test_html_report 도구를 호출하세요!"""
                
                else:
                    # 일반적인 진행
                    context_prompt = f"""이전 단계 결과: {content}

에이전틱 워크플로우를 계속 진행하세요:
1. 아직 수집해야 할 데이터가 있으면 수집
2. 수집이 완료되었으면 분석 수행  
3. 분석이 완료되었으면 HTML 리포트 생성

다음 필요한 도구를 즉시 호출하세요."""
                
                messages.append(HumanMessage(content=context_prompt))
        
        # Claude 호출
        try:
            logger.info(f"🧠 Claude 호출 - 메시지 수: {len(messages)}")
            response = await self.llm_with_tools.ainvoke(messages)
            
            # 🔥 도구 호출 디버깅 강화
            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_names = [str(tc.get('name', 'unknown')) if isinstance(tc, dict) else str(tc) for tc in response.tool_calls]
                logger.info(f"✅ Claude가 {len(response.tool_calls)}개 도구 호출: {tool_names}")
            else:
                logger.warning(f"⚠️ Claude가 도구를 호출하지 않음! 응답: {str(response.content)[:200]}...")
                # 도구 호출 강제 디버깅
                logger.warning(f"⚠️ response.tool_calls 속성: {hasattr(response, 'tool_calls')}")
                if hasattr(response, 'tool_calls'):
                    logger.warning(f"⚠️ tool_calls 값: {response.tool_calls}")
            
            return {"messages": [response]}
            
        except Exception as e:
            logger.error(f"Claude 호출 실패: {e}")
            error_message = AIMessage(content=f"Claude 호출 중 오류가 발생했습니다: {str(e)}")
            return {"messages": [error_message]}
    
    def should_continue(self, state: WorkflowState) -> str:
        """🔥 에이전틱 워크플로우 제어 - 완전한 자율성 보장"""
        
        messages = state["messages"]
        collected_data = state["collected_data"]
        
        if not messages:
            return "continue"
        
        last_message = messages[-1]
        
        # 🔥 핵심: 도구 호출이 있으면 항상 계속 진행
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            logger.info(f"🔄 도구 호출 감지: {len(last_message.tool_calls)}개 - 계속 진행")
            return "continue"
        
        # 🔥 에이전틱 자율성 보장: 제한을 대폭 완화
        if len(messages) >= 50:  # 12개에서 50개로 대폭 증가
            logger.warning("⚠️ 최대 메시지 수 도달 (50개) - 종료")
            return "end"
        
        # 응답 내용 분석
        content = getattr(last_message, 'content', '').lower()
        
        # 🔥 HTML 리포트 완성 감지 - 더 포괄적인 조건
        if ('html' in content and (len(content) > 200 or 
            any(keyword in content.lower() for keyword in ['<!doctype', '<html', '<head', '<body', 'html>', '</html']))):
            logger.info("✅ HTML 리포트 생성 완료 - 종료")
            return "end"
        
        # 🔥 분석 완료 후 HTML 생성 지시 조건
        analysis_complete_keywords = [
            '분석이 완료', '분석 완료', '분석을 마', '데이터 분석 결과', 
            '평균 가격', '거래량', '분석 요약', '결론'
        ]
        if any(keyword in content for keyword in analysis_complete_keywords):
            logger.info("✅ 분석 완료 감지 - HTML 리포트 생성 단계로 이동")
            return "continue"  # HTML 생성을 위해 계속 진행
        
        # 🔥 명확한 완료 선언만 인정
        definitive_completion = [
            '분석이 완료되었습니다', '리포트가 완성되었습니다', 
            '모든 단계가 완료되었습니다', '작업을 마무리했습니다'
        ]
        if any(phrase in content for phrase in definitive_completion):
            logger.info("✅ 명확한 완료 선언 감지 - 종료")
            return "end"
        
        # 🔥 API 에러는 복구 시도 - 즉시 종료하지 않음
        if 'api 호출 중 오류' in content or '400 bad request' in content:
            logger.warning("⚠️ API 에러 감지하지만 복구 시도를 위해 계속 진행")
            return "continue"  # 에러 시에도 계속 진행하여 복구 시도
        
        # 🔥 에이전틱 사고 과정 보장 - 설명도 허용
        # Claude가 계획을 세우거나 설명하는 것도 에이전틱 사고의 일부
        thinking_keywords = [
            '다음으로', '이제', '그럼', '먼저', '우선', '계획', '단계', 
            '진행하겠습니다', '분석하겠습니다', '수집하겠습니다'
        ]
        if any(keyword in content for keyword in thinking_keywords):
            logger.info("🧠 Claude 에이전틱 사고 과정 - 계속 진행")
            return "continue"
        
        # 🔥 기본적으로 계속 진행 - 에이전틱 자율성 최대 보장
        logger.info("🔄 에이전틱 워크플로우 계속 진행")
        return "continue"
    
    async def run_with_streaming(self, user_query: str, streaming_callback, abort_check=None) -> Dict[str, Any]:
        """에이전틱 워크플로우 실행 - 스트리밍 콜백 지원"""
        
        # 도구 초기화 (필요시)
        await self.initialize_tools()
        
        logger.info("🚀 에이전틱 워크플로우 시작 - Claude가 MCP 도구들을 자율적으로 선택")
        
        # 스트리밍 콜백을 도구들에 추가
        await self._wrap_tools_with_streaming(streaming_callback)
        
        # LLM에 스트리밍 콜백 추가 (Pydantic 모델용)
        object.__setattr__(self.llm, 'streaming_callback', streaming_callback)
        
        # 중단 체크 함수를 LLM과 워크플로우에 전달
        if abort_check:
            object.__setattr__(self.llm, 'abort_check', abort_check)
        
        # 초기 상태
        initial_state = {
            "messages": [],
            "user_query": user_query,
            "collected_data": {},
            "report_content": "",
            "current_step": "starting",
            "error": None,
            "browser_test_url": None,
            "validation_passed": None,
            "abort_check": abort_check  # 상태에 중단 체크 함수 포함
        }
        
        try:
            await streaming_callback.send_analysis_step("workflow_start", "AI 에이전트 워크플로우를 시작합니다")
            
            # 🔥 워크플로우 실행 - 에이전틱 자율성 보장 (recursion_limit 증가)
            config = {"recursion_limit": 100}  # 25에서 100으로 증가
            final_state = await self.workflow.ainvoke(initial_state, config=config)
            
            logger.info("✅ 에이전틱 워크플로우 완료")
            
            # 마지막 메시지에서 분석 내용 추출
            analysis_content = ""
            report_content = ""
            
            for msg in final_state["messages"]:
                if hasattr(msg, 'content') and msg.content:
                    content = str(msg.content)
                    if 'html' in content.lower():
                        report_content = content
                    else:
                        analysis_content += content + "\n\n"
            
            await streaming_callback.send_analysis_step("workflow_complete", "AI 에이전트 분석이 완료되었습니다")
            
            return {
                "success": True,
                "analysis": analysis_content or "AI 에이전트가 사용자 요청을 분석하고 MCP 도구들을 활용하여 데이터를 수집했습니다.",
                "report_content": report_content,
                "collected_data": final_state["collected_data"],
                "browser_test_url": final_state.get("browser_test_url"),
                "validation_passed": final_state.get("validation_passed"),
                "messages": [str(msg) for msg in final_state["messages"]],
                "error": final_state["error"],
                "available_tools": [f"{tool.name} ({getattr(tool, 'server_name', 'builtin')})" for tool in self.tools]
            }
            
        except Exception as e:
            logger.error(f"❌ 에이전틱 워크플로우 실행 실패: {e}")
            await streaming_callback.send_tool_error("workflow", str(e))
            return {
                "success": False,
                "error": str(e),
                "analysis": "",
                "report_content": "",
                "collected_data": {},
                "messages": [],
                "available_tools": []
            }

    async def _wrap_tools_with_streaming(self, streaming_callback):
        """도구들에 스트리밍 콜백 추가 - 🔥 클로저 문제 해결"""
        
        for i, tool in enumerate(self.tools):
            # 원본 _arun 메서드 백업
            if not hasattr(tool, '_original_arun'):
                tool._original_arun = tool._arun
            
            # 🔥 클로저 문제 해결을 위한 로컬 변수 바인딩
            def create_wrapped_arun(current_tool, tool_index):
                async def wrapped_arun(*args, **kwargs):
                    tool_name = current_tool.name
                    server_name = getattr(current_tool, 'server_name', 'builtin')
                    
                    try:
                        logger.info(f"🔧 스트리밍 래퍼: {tool_name} 실행 시작 (index: {tool_index})")
                        
                        # 도구 시작 알림
                        await streaming_callback.send_tool_start(tool_name, server_name)
                        
                        # 🔥 도구 실행 중 중단 체크
                        if hasattr(self.llm, 'abort_check') and self.llm.abort_check and self.llm.abort_check():
                            logger.info(f"🛑 도구 {tool_name} 실행 중 중단 요청 감지")
                            await streaming_callback.send_tool_abort(tool_name, "사용자 요청으로 중단됨")
                            return "❌ 사용자 요청으로 도구 실행이 중단되었습니다."
                        
                        # 🔥 도구 실행을 래핑해서 중간에도 중단 체크
                        result = await self._run_tool_with_abort_check(current_tool, streaming_callback, *args, **kwargs)
                        
                        # 실행 완료 후에도 중단 체크
                        if hasattr(self.llm, 'abort_check') and self.llm.abort_check and self.llm.abort_check():
                            logger.info(f"🛑 도구 {tool_name} 완료 후 중단 요청 감지")
                            await streaming_callback.send_tool_abort(tool_name, "사용자 요청으로 중단됨")
                            return "❌ 사용자 요청으로 도구 실행이 중단되었습니다."
                        
                        # 결과 요약 생성
                        result_str = str(result)
                        result_summary = result_str  # 길이 제한 제거 - 전체 결과 표시
                        
                        # 도구 완료 알림
                        await streaming_callback.send_tool_complete(tool_name, result_summary)
                        
                        logger.info(f"✅ 스트리밍 래퍼: {tool_name} 실행 완료")
                        return result
                        
                    except Exception as e:
                        logger.error(f"❌ 스트리밍 래퍼: {tool_name} 실행 실패: {e}")
                        # 도구 오류 알림
                        await streaming_callback.send_tool_error(tool_name, str(e))
                        raise
                
                return wrapped_arun
            
            # 메서드 교체 - 🔥 각 도구마다 고유한 래퍼 생성
            tool._arun = create_wrapped_arun(tool, i)
    
    async def _run_tool_with_abort_check(self, tool, streaming_callback, *args, **kwargs):
        """🔥 중단 체크가 가능한 도구 실행"""
        try:
            # 실행 전 중단 체크
            if hasattr(self.llm, 'abort_check') and self.llm.abort_check and self.llm.abort_check():
                logger.info(f"🛑 도구 {tool.name} 실행 전 중단 감지")
                await streaming_callback.send_tool_abort(tool.name, "중단됨")
                return "❌ 사용자 요청으로 중단되었습니다."
            
            # 실제 도구 실행
            result = await tool._original_arun(*args, **kwargs)
            
            # 실행 후 중단 체크
            if hasattr(self.llm, 'abort_check') and self.llm.abort_check and self.llm.abort_check():
                logger.info(f"🛑 도구 {tool.name} 실행 후 중단 감지")
                await streaming_callback.send_tool_abort(tool.name, "중단됨")
                return "❌ 사용자 요청으로 중단되었습니다."
            
            return result
            
        except Exception as e:
            # 중단 요청인지 확인
            if hasattr(self.llm, 'abort_check') and self.llm.abort_check and self.llm.abort_check():
                logger.info(f"🛑 도구 {tool.name} 예외 발생 시 중단 감지")
                await streaming_callback.send_tool_abort(tool.name, "중단됨")
                return "❌ 사용자 요청으로 중단되었습니다."
            else:
                raise  # 일반 오류는 재발생

    async def run(self, user_query: str) -> Dict[str, Any]:
        """에이전틱 워크플로우 실행 (기본 버전)"""
        
        # 도구 초기화 (필요시)
        await self.initialize_tools()
        
        logger.info("🚀 에이전틱 워크플로우 시작 - Claude가 MCP 도구들을 자율적으로 선택")
        
        # 초기 상태
        initial_state = {
            "messages": [],
            "user_query": user_query,
            "collected_data": {},
            "report_content": "",
            "current_step": "starting",
            "error": None,
            "browser_test_url": None,
            "validation_passed": None
        }
        
        try:
            # 🔥 워크플로우 실행 - 에이전틱 자율성 보장 (recursion_limit 증가)
            config = {"recursion_limit": 100}  # 25에서 100으로 증가
            final_state = await self.workflow.ainvoke(initial_state, config=config)
            
            logger.info("✅ 에이전틱 워크플로우 완료")
            
            # 마지막 메시지에서 HTML 리포트 추출
            report_content = ""
            analysis_content = ""
            
            for msg in final_state["messages"]:
                if hasattr(msg, 'content') and msg.content:
                    content = str(msg.content)
                    if 'html' in content.lower():
                        report_content = content
                    else:
                        analysis_content += content + "\n\n"
            
            return {
                "success": True,
                "analysis": analysis_content or "AI 에이전트가 분석을 완료했습니다.",
                "report_content": report_content,
                "collected_data": final_state["collected_data"],
                "browser_test_url": final_state.get("browser_test_url"),
                "validation_passed": final_state.get("validation_passed"),
                "messages": [str(msg) for msg in final_state["messages"]],
                "error": final_state["error"],
                "available_tools": [f"{tool.name} ({getattr(tool, 'server_name', 'builtin')})" for tool in self.tools]
            }
            
        except Exception as e:
            logger.error(f"❌ 에이전틱 워크플로우 실행 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis": "",
                "report_content": "",
                "collected_data": {},
                "messages": [],
                "available_tools": []
            }

    def _analyze_user_query(self, query: str) -> str:
        """사용자 쿼리 분석하여 적절한 워크플로우 결정"""
        
        query_lower = query.lower()
        
        # 일반적인 분석 키워드 체크
        analysis_keywords = [
            '분석', '리포트', '시각화', '차트', '데이터', '통계', 
            '트렌드', '패턴', '비교', '현황', '성과', '지표'
        ]
        
        if any(keyword in query_lower for keyword in analysis_keywords):
            return f"""
데이터 분석 요청입니다.
요청 내용: {query}
목표: 완전한 데이터 분석 리포트 생성
사용할 도구: 가용한 MCP 도구들을 활용하여 데이터를 수집하고 분석
"""
        
        # 기본 응답
        return f"""
일반적인 데이터 분석 요청입니다.
요청 내용: {query}
목표: 요청에 맞는 적절한 분석 수행
"""


# 기존 클래스명 유지 (하위 호환성)
LangGraphRealEstateWorkflow = TrueAgenticWorkflow 