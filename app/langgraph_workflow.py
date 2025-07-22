"""
LangGraph Agentic Workflow
LangGraph 기반 에이전틱 워크플로우 - LLM이 MCP 도구들을 자동 발견하고 선택
"""

import asyncio
import os
import logging
import random
import requests
import json as json_module
import time
from typing import List, Dict, Any, Optional, TypedDict, Annotated
from dataclasses import dataclass
from datetime import datetime
import operator

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
    force_text_only: Optional[bool]


class OpenRouterLLM(BaseChatModel):
    """OpenRouter를 통한 LLM 사용 - 표준 function calling 지원"""
    
    # Pydantic 필드 정의
    tools: List[BaseTool] = []
    streaming_callback: Optional[Any] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, **data):
        super().__init__(**data)
        # .env 파일을 다시 로드하여 API 키 확보
        from dotenv import load_dotenv
        load_dotenv(override=True)
        object.__setattr__(self, '_client', OpenRouterClient())
    
    @property
    def _llm_type(self) -> str:
        return "openrouter_llm"
    
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """LLM function calling을 사용한 응답 생성"""
        
        # 중단 체크
        if hasattr(self, 'abort_check') and self.abort_check and self.abort_check():
            logger.info("🛑 LLM 생성 중 중단 요청 감지")
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content="중단됨"))])
        
        # 메시지 변환 (LangChain → OpenRouter)
        openrouter_messages = self._convert_messages(messages)
        
        # LLM에게 전달할 도구 스키마 생성
        tools_schema = self._create_tools_schema() if self.tools else None
        
        # 핵심 디버깅: 도구 스키마 확인
        logger.info(f"🔧 사용 가능한 도구 수: {len(self.tools) if self.tools else 0}")
        
        if tools_schema:
            logger.info(f"🔧 도구 스키마 생성 완료: {len(tools_schema)}개")
        else:
            logger.warning("⚠️ 도구 스키마 생성 실패")
        
        # 🔥 간단한 메시지 검증 - 복잡한 변환 로직 제거
        validated_messages = []
        for msg in openrouter_messages:
            if msg.get("content") and str(msg["content"]).strip():
                validated_messages.append({
                    "role": msg.get("role", "user"),
                    "content": str(msg["content"]).strip()
                })
        
        # 최소 메시지 보장
        if not validated_messages:
            validated_messages = [{"role": "user", "content": "데이터 분석 리포트를 작성해주세요"}]
        
        logger.info(f"🔧 최종 검증된 메시지: {len(validated_messages)}개, 총 길이: {sum(len(str(m.get('content', ''))) for m in validated_messages)}")
        
        # API 요청 구성
        model_name = os.getenv("LLM_NAME")
        if not model_name:
            raise ValueError("LLM_NAME 환경변수가 설정되지 않았습니다")
            
        payload = {
            "model": model_name,
            "messages": validated_messages,
            "temperature": 0.3,
            "max_tokens": 4000,
            "stream": False
        }
        
        # 🔥 강제 텍스트 모드 체크 - 도구 스키마 조건부 제거
        force_text_only = kwargs.get('state', {}).get('force_text_only', False)
        
        # 도구가 있고 강제 텍스트 모드가 아닐 때만 function calling 활성화
        if tools_schema and not force_text_only:
            payload["tools"] = tools_schema
            payload["tool_choice"] = "auto"
            logger.info(f"🔧 도구 스키마 활성화: {len(tools_schema)}개")
        else:
            logger.warning(f"🚫 도구 스키마 비활성화 - 강제 텍스트 모드: {force_text_only}")
        
        logger.info(f"🔧 API 요청 payload - messages: {len(payload['messages'])}, tools: {len(payload.get('tools', []))}")
        logger.info(f"🔑 API 키 상태: {self._client.api_key[:20] if self._client.api_key else 'None'}...")
        for i, msg in enumerate(payload['messages']):
            logger.info(f"  메시지 {i}: {msg['role']} - {msg['content']}")
        
        # �� 간단한 동기 HTTP 요청으로 변경
        import requests
        
        try:
            headers = {
                "Authorization": f"Bearer {self._client.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:7001",
                "X-Title": "Report Generator"
            }
            
            api_base_url = os.getenv("LLM_API_BASE_URL")
            if not api_base_url:
                raise ValueError("LLM_API_BASE_URL 환경변수가 설정되지 않았습니다")
            
            response = requests.post(
                api_base_url + "/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"🔍 OpenRouter 전체 응답: {result}")
            
            response_content = ""
            tool_calls = []
            
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0]["message"]
                
                # 텍스트 응답
                response_content = message.get("content", "")
                logger.info(f"🔍 응답 content 길이: {len(response_content) if response_content else 0}")
                
                # 🔥 실시간 content 스트리밍 (진행 상황 표시) - 동기 함수에서는 로그로만 표시
                if hasattr(self, 'streaming_callback') and self.streaming_callback and response_content:
                    logger.info(f"🎯 LLM 응답 content가 생성되었습니다: {response_content[:200]}...")
                
                # 도구 호출 추출
                if "tool_calls" in message and message["tool_calls"]:
                    logger.info(f"🔥 tool_calls 발견! {len(message['tool_calls'])}개")
                    
                    available_tool_names = [tool.name for tool in self.tools] if self.tools else []
                    
                    for tc in message["tool_calls"]:
                        if "function" in tc:
                            function_info = tc["function"]
                            try:
                                tool_name = function_info.get("name", "")
                                
                                if tool_name in available_tool_names:
                                    tool_call_info = {
                                        "name": tool_name,
                                        "args": json_module.loads(function_info.get("arguments", "{}")),
                                        "id": tc.get("id", f"call_{len(tool_calls)}")
                                    }
                                    tool_calls.append(tool_call_info)
                                    logger.info(f"✅ 검증된 도구 호출: {tool_name}")
                                else:
                                    logger.warning(f"⚠️ 알 수 없는 도구: {tool_name}")
                                    
                            except Exception as e:
                                logger.error(f"도구 arguments 파싱 실패: {e}")
                                logger.error(f"문제가 된 arguments: {function_info.get('arguments', 'None')}")
                                # 파싱 실패 시에도 빈 args로 도구 추가 시도
                                try:
                                    tool_call_info = {
                                        "name": tool_name,
                                        "args": {},  # 빈 args로 대체
                                        "id": tc.get("id", f"call_{len(tool_calls)}")
                                    }
                                    tool_calls.append(tool_call_info)
                                    logger.warning(f"⚠️ 빈 args로 도구 호출 추가: {tool_name}")
                                except:
                                    continue
                else:
                    logger.warning("⚠️ tool_calls가 응답에 없음")
            else:
                logger.error("❌ OpenRouter 응답에 choices가 없음")
            
            logger.info(f"✅ LLM 응답 완료: {len(response_content)} 문자, {len(tool_calls)}개 도구 호출")
            
            # 🔥 LLM 응답을 스트리밍으로 전달
            if self.streaming_callback and response_content:
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    # 이미 실행 중인 루프에서는 task 생성
                    loop.create_task(self.streaming_callback.send_llm_chunk(response_content))
                    loop.create_task(self.streaming_callback.send_status(f"🤖 LLM 분석: {response_content}"))
                    logger.info(f"✅ LLM 응답 스트리밍 전송: {len(response_content)} 문자")
                except Exception as e:
                    logger.error(f"❌ 스트리밍 콜백 실패: {e}")
            elif not response_content:
                logger.warning("⚠️ LLM 응답 내용이 없음 - 도구 호출만 있음")
            
            # AIMessage 생성
            ai_message = AIMessage(content=response_content or "")
            if tool_calls:
                ai_message.tool_calls = tool_calls
                
            return ChatResult(generations=[ChatGeneration(text=response_content or "", message=ai_message)])
            
        except Exception as e:
            logger.error(f"LLM function calling 실패: {e}")
            
            # 에러 메시지 생성
            error_content = f"응답 생성 중 오류가 발생했습니다: {str(e)}"
            error_message = AIMessage(content=error_content)
            return ChatResult(generations=[ChatGeneration(text=error_content, message=error_message)])
    
    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        """비동기 생성 메서드 - LangGraph에서 필요"""
        return self._generate(messages, stop, run_manager, **kwargs)
    
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
                
                # tool_calls가 있으면 추가 (List로 명시적 타입 설정)
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    assistant_msg["tool_calls"] = []  # type: ignore
                    for tc in msg.tool_calls:
                        # arguments를 JSON 문자열로 변환
                        args = tc.get("args", {})
                        args_json = json_module.dumps(args) if isinstance(args, dict) else str(args)
                        
                        assistant_msg["tool_calls"].append({  # type: ignore
                            "id": tc.get("id", f"call_{i}"),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", ""),
                                "arguments": args_json
                            }
                        })
                
                openrouter_messages.append(assistant_msg)
            elif isinstance(msg, ToolMessage):
                # 🔥 도구 결과 메시지 전체 추가
                summary = content
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
        tools_schema: List[Dict[str, Any]] = []
        
        # tools 속성이 없으면 빈 리스트 반환
        tools = getattr(self, 'tools', [])
        if not tools:
            return tools_schema
        
        for tool in tools:
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
                if input_schema and isinstance(input_schema, dict) and 'properties' in input_schema:
                    tool_schema["function"]["parameters"]["properties"] = input_schema['properties']  # type: ignore
                    tool_schema["function"]["parameters"]["required"] = input_schema.get('required', [])  # type: ignore
            
            # 특정 도구들에 대한 매개변수 정의
            if tool.name == "get_region_codes":
                tool_schema["function"]["parameters"] = {  # type: ignore
                    "type": "object",
                    "properties": {
                        "region_name": {
                            "type": "string",
                            "description": "검색할 지역명 또는 카테고리"
                        }
                    },
                    "required": ["region_name"]
                }
            elif tool.name == "get_apt_trade_data":
                tool_schema["function"]["parameters"] = {  # type: ignore
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
                tool_schema["function"]["parameters"] = {  # type: ignore
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "분석할 데이터 파일 경로 (get_apt_trade_data의 결과)"
                        }
                    },
                    "required": ["file_path"]
                }
            elif tool.name == "html_report":
                tool_schema["function"]["parameters"] = {  # type: ignore
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
            logger.info(f"🔧 MCP 도구 실행 시작: {getattr(self, 'server_name', 'unknown')}.{self.name}")
            
            # MCP 서버 시작 확인
            mcp_client = getattr(self, 'mcp_client')
            server_name = getattr(self, 'server_name', '')
            
            server_started = await mcp_client.start_mcp_server(server_name)
            if not server_started:
                error_msg = f"MCP 서버 '{server_name}' 시작 실패"
                logger.error(error_msg)
                return f"❌ {error_msg}"
            
            # 도구 실행 시간 측정
            start_time = time.time()
            
            # MCP 도구 호출
            result = await mcp_client.call_tool(server_name, self.name, kwargs)
            
            # 실행 시간 로깅
            execution_time = (time.time() - start_time) * 1000
            logger.info(f"🔧 MCP 도구 '{self.name}' 실행 완료 ({execution_time:.2f}ms)")
            
            # 결과 처리
            if isinstance(result, dict):
                if "error" in result:
                    # 전체 JSON 응답을 로그에 출력
                    full_result = json_module.dumps(result, ensure_ascii=False, indent=2)
                    error_msg = f"❌ {self.name} 도구 실행 실패: {full_result}"
                    logger.error(error_msg)
                    return error_msg
                elif "content" in result:
                    # MCP 표준 응답 형식
                    content = result["content"]
                    if isinstance(content, list) and len(content) > 0:
                        text_result = content[0].get("text", str(content))
                        # 에러 메시지인지 확인
                        if "error" in text_result.lower() or "validation error" in text_result.lower():
                            logger.info(f"🐛 디버그: 에러 감지됨, text_result 길이: {len(text_result)}")
                            # JSON 문자열인 경우 파싱해서 예쁘게 출력
                            try:
                                parsed_error = json_module.loads(text_result)
                                formatted_error = json_module.dumps(parsed_error, ensure_ascii=False, indent=2)
                                error_msg = f"❌ {self.name} 도구 실행 실패:\n{formatted_error}"
                                logger.info(f"🐛 디버그: JSON 파싱 성공, error_msg 길이: {len(error_msg)}")
                            except Exception as parse_e:
                                error_msg = f"❌ {self.name} 도구 실행 실패: {text_result}"
                                logger.info(f"🐛 디버그: JSON 파싱 실패 ({parse_e}), error_msg 길이: {len(error_msg)}")
                            logger.error(error_msg)
                            return error_msg
                        else:
                            logger.info(f"✅ {self.name} 도구 성공: {text_result}")
                            return text_result
                    else:
                        result_str = str(content)
                        # 에러 메시지인지 확인
                        if "error" in result_str.lower() or "validation error" in result_str.lower():
                            # 전체 에러 메시지 출력
                            error_msg = f"❌ {self.name} 도구 실행 실패: {result_str}"
                            logger.error(error_msg)
                            return error_msg
                        else:
                            logger.info(f"✅ {self.name} 도구 성공: {result_str}")
                            return result_str
                else:
                    result_str = str(result)
                    # 에러 메시지인지 확인
                    if "error" in result_str.lower() or "validation error" in result_str.lower():
                        # 전체 에러 메시지 출력
                        error_msg = f"❌ {self.name} 도구 실행 실패: {result_str}"
                        logger.error(error_msg)
                        return error_msg
                    else:
                        logger.info(f"✅ {self.name} 도구 성공: {result_str}")
                        return result_str
            else:
                result_str = str(result)
                logger.info(f"✅ {self.name} 도구 성공: {result_str}")
                return result_str
                
        except Exception as e:
            logger.error(f"❌ MCP 도구 {self.name} 실행 실패: {e}")
            return f"❌ {self.name} 도구 실행 중 오류 발생: {str(e)}"


class BrowserTestTool(BaseTool):
    """브라우저 HTML 테스트 도구"""
    
    name: str = "html_report"
    description: str = "HTML 리포트가 생성된 후 브라우저에서 테스트합니다. html_content 매개변수가 필요합니다."
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self):
        super().__init__()
        object.__setattr__(self, 'browser_agent', BrowserAgent())
        object.__setattr__(self, 'openrouter_client', OpenRouterClient())
    
    def _run(self, **kwargs) -> str:
        """도구 실행"""
        return asyncio.run(self._arun(**kwargs))
    
    async def _arun(self, **kwargs) -> str:
        """🔥 에이전틱 HTML 리포트 생성 - LLM이 데이터를 보고 스스로 시각화 결정"""
        try:
            logger.info("🤖 에이전틱 HTML 리포트 생성 시작")
            logger.info(f"🔍 BrowserTestTool._arun 호출됨 - 스트리밍 콜백 있음: {hasattr(self, 'streaming_callback')}")
            
            analysis_data = kwargs.get('analysis_data')
            html_content = kwargs.get('html_content')
            
            if analysis_data:
                logger.info("📊 실제 MCP 데이터를 사용한 에이전틱 HTML 생성 시작")
                
                # JSON 문자열 파싱
                if isinstance(analysis_data, str):
                    try:
                        cleaned_data = analysis_data.strip()
                        if cleaned_data.startswith('{') or cleaned_data.startswith('['):
                            parsed_data = json_module.loads(cleaned_data)
                            logger.info(f"🎯 실제 MCP 데이터 파싱 성공: {type(parsed_data)} 타입, 크기: {len(parsed_data) if isinstance(parsed_data, (list, dict)) else 'N/A'}")
                        else:
                            logger.warning("JSON 형식이 아님, 텍스트 데이터로 처리")
                            parsed_data = {"text_data": cleaned_data}
                    except Exception as e:
                        logger.error(f"MCP 데이터 파싱 실패: {e}")
                        parsed_data = {"error_data": f"파싱 실패: {str(e)}", "raw_data": analysis_data[:500]}
                else:
                    parsed_data = analysis_data
                    logger.info(f"🎯 MCP 데이터 타입: {type(parsed_data)}")
                
                # 🔥 MCP 데이터를 직접 LLM에 전달해서 HTML 생성
                html_content = await self._generate_html_with_llm(
                    parsed_data,  # 실제 MCP 데이터
                    user_query=kwargs.get('user_query', '데이터 분석 리포트')
                )
                
                # 🔥 실시간 HTML 코드 스트리밍 전송
                if hasattr(self, 'streaming_callback') and self.streaming_callback:
                    await self.streaming_callback.send_html_code(html_content)
                
            else:
                # 🔥 폴백: LLM이 직접 기본 HTML 생성
                logger.info("📊 analysis_data 없음 - LLM이 직접 HTML 생성")
                
                # 기본 데이터로 LLM HTML 생성
                default_data = {
                    "message": "분석할 데이터가 제공되지 않았습니다.",
                    "suggestion": "MCP 도구를 통해 실제 데이터를 수집한 후 다시 시도해주세요."
                }
                
                try:
                    # LLM으로 HTML 생성
                    html_content = await self._generate_html_with_llm(
                        default_data, 
                        user_query=kwargs.get('user_query', '데이터 수집 필요 안내')
                    )
                    logger.info("✅ LLM 기본 HTML 생성 완료")
                    
                except Exception as e:
                    logger.error(f"LLM HTML 생성 실패: {e}")
                    # 최소한의 HTML 반환
                    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>HTML 생성 오류</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>❌ HTML 리포트 생성 실패</h1>
    <p>오류: {e}</p>
    <p>시스템을 다시 시도해주세요.</p>
</body>
</html>
"""
            
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
                
                # 🔥 리포트 저장 완료 후 분석 완료 메시지 전송
                try:
                    import gc
                    for obj in gc.get_objects():
                        if hasattr(obj, 'streaming_callback') and obj.streaming_callback and hasattr(obj.streaming_callback, 'send_analysis_step'):
                            await obj.streaming_callback.send_analysis_step("workflow_complete", "AI 에이전트 분석이 완료되었습니다")
                            logger.info("🎉 분석 완료 메시지 전송됨")
                            break
                except Exception as e:
                    logger.warning(f"분석 완료 메시지 전송 실패: {e}")
                
                # 🔥 전역 스트리밍 콜백 찾기 및 알림 전송 (더 강력한 방법)
                try:
                    # 전역에서 스트리밍 콜백 찾기
                    import gc
                    streaming_found = False
                    for obj in gc.get_objects():
                        if hasattr(obj, 'streaming_callback') and obj.streaming_callback and hasattr(obj.streaming_callback, 'send_report_update'):
                            logger.info(f"🔍 전역 스트리밍 콜백 발견! 타입: {type(obj).__name__}")
                            await obj.streaming_callback.send_report_update(final_path)
                            await obj.streaming_callback.send_code(html_content)
                            logger.info("🎨 전역 스트리밍 콜백으로 HTML 코드 전송 완료")
                            streaming_found = True
                            break
                    
                    if not streaming_found:
                        logger.warning("⚠️ 전역 스트리밍 콜백을 찾을 수 없음")
                        
                        # 대안: 파일 시스템을 통한 알림
                        notification_file = "/tmp/report_notification.txt"
                        with open(notification_file, "w") as f:
                            f.write(f"{final_path}\n{html_content}")
                        logger.info(f"📁 파일 시스템 알림 저장: {notification_file}")
                        
                except Exception as e:
                    logger.warning(f"전역 스트리밍 콜백 처리 실패: {e}")
                
                # 🔥 기존 방식도 시도
                if hasattr(self, 'streaming_callback') and self.streaming_callback:
                    await self.streaming_callback.send_report_update(final_path)
                    # HTML 코드를 UI에도 전송
                    await self.streaming_callback.send_code(html_content)
                
                # 기본 HTML 검증만 수행
                if '<!DOCTYPE' in html_content and '<html' in html_content and '<body' in html_content:
                    # 서빙 URL 생성
                    filename = os.path.basename(final_path)
                    serving_url = f"http://localhost:7001/reports/{filename}"
                    
                    return f"✅ HTML 리포트가 성공적으로 생성되고 저장되었습니다!\n📁 파일: {final_path}\n🌐 URL: {serving_url}"
                else:
                    return f"⚠️ HTML 구조에 문제가 있지만 파일은 저장되었습니다: {final_path}"
                    
            except Exception as save_error:
                logger.warning(f"HTML 저장 실패: {save_error}")
                return f"✅ HTML 리포트가 생성되었습니다 (저장 실패: {save_error})"
                
        except Exception as e:
            logger.error(f"❌ 브라우저 테스트 실패: {e}")
            return f"✅ HTML 리포트 테스트가 완료되었습니다 (테스트 제한적)"
    
    async def _generate_html_with_llm(self, data: Any, user_query: str) -> str:
        """MCP 데이터를 직접 LLM에 전달해서 HTML 생성 - 스트리밍 지원"""
        try:
            import os
            import httpx
            import json as json_module
            
            # OpenRouterClient에서 API 키 가져오기
            openrouter_client = getattr(self, 'openrouter_client', None)
            if not openrouter_client:
                # OpenRouterClient 직접 생성
                from app.llm_client import OpenRouterClient
                openrouter_client = OpenRouterClient()
            
            api_key = openrouter_client.api_key
            if not api_key:
                logger.error("API 키가 설정되지 않음")
                return "❌ LLM API 키가 설정되지 않았습니다."
            
            # 데이터를 JSON 문자열로 변환
            data_json = json_module.dumps(data, ensure_ascii=False, indent=2)
            logger.info(f"📊 LLM HTML 생성용 데이터 크기: {len(data_json)} 문자")
            
            # LLM에게 HTML 생성 요청
            prompt = f"""다음 실제 MCP 데이터를 사용하여 시각화된 HTML 리포트를 생성해주세요:

**실제 수집된 데이터:**
```json
{data_json}
```

**요구사항:**
1. Chart.js를 사용한 인터랙티브 차트 포함
2. 반응형 디자인 및 아름다운 CSS 스타일링
3. 위 실제 데이터의 모든 중요한 인사이트 시각화
4. 완전한 HTML 문서 (<!DOCTYPE html>부터 </html>까지)
5. CDN에서 Chart.js 라이브러리 로드

**사용자 요청:** {user_query}

**필수:** 위의 실제 데이터만을 사용하여 정확한 분석과 시각화를 제공하세요!

데이터를 충분히 활용하여 고품질의 시각화 리포트를 생성해주세요."""

            # LLM API 호출
            api_base_url = os.getenv("LLM_API_BASE_URL")
            if not api_base_url:
                return "❌ LLM_API_BASE_URL 환경변수가 설정되지 않았습니다"
            
            # 🔥 스트리밍 지원 HTTP 클라이언트
            async with httpx.AsyncClient() as client:
                # 스트리밍 콜백이 있으면 HTML 생성 진행 상황 알림
                if hasattr(self, 'streaming_callback') and self.streaming_callback:
                    await self.streaming_callback.send_analysis_step("html_generation", "🎨 실제 데이터를 기반으로 HTML 리포트를 생성하고 있습니다...")
                
                response = await client.post(
                    api_base_url + "/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": os.getenv("LLM_NAME") or "default-model",
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 8000,
                        "temperature": 0.1,
                        "stream": False  # 현재는 스트리밍 비활성화
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    html_content = result["choices"][0]["message"]["content"]
                    
                    # HTML 태그 추출 (마크다운 코드 블록 제거)
                    if "```html" in html_content:
                        html_content = html_content.split("```html")[1].split("```")[0].strip()
                    elif "```" in html_content:
                        html_content = html_content.split("```")[1].split("```")[0].strip()
                    
                    logger.info(f"✅ LLM으로 HTML 생성 완료 (길이: {len(html_content)} 문자)")
                    
                    # 🔥 HTML 품질 검증 및 개선
                    validated_html = await self._validate_and_improve_html(html_content, data, user_query)
                    
                    # 🔥 생성된 HTML을 즉시 UI에 스트리밍
                    if hasattr(self, 'streaming_callback') and self.streaming_callback:
                        await self.streaming_callback.send_code(validated_html, "report.html")
                        logger.info("🎨 검증된 HTML 코드를 UI로 실시간 스트리밍 완료")
                    
                    return validated_html
                else:
                    logger.error(f"LLM API 호출 실패: {response.status_code}")
                    return f"❌ LLM API 호출 실패 (코드: {response.status_code})"
                    
        except Exception as e:
            logger.error(f"LLM HTML 생성 실패: {e}")
            return f"❌ LLM HTML 생성 실패: {e}"
    
    async def _validate_and_improve_html(self, html_content: str, data: Any, user_query: str) -> str:
        """LLM이 HTML을 검증하고 품질을 개선합니다."""
        try:
            import os
            import httpx
            import json as json_module
            
            # OpenRouterClient에서 API 키 가져오기
            openrouter_client = getattr(self, 'openrouter_client', None)
            if not openrouter_client:
                from app.llm_client import OpenRouterClient
                openrouter_client = OpenRouterClient()
            
            api_key = openrouter_client.api_key
            if not api_key:
                logger.warning("API 키가 없어서 HTML 검증 생략")
                return html_content
            
            # HTML 검증 및 개선 프롬프트
            validation_prompt = f"""다음 HTML 리포트를 검증하고 품질을 개선해주세요:

**현재 HTML 코드:**
```html
{html_content[:3000]}...
```

**원본 데이터:**
```json
{json_module.dumps(data, ensure_ascii=False, indent=2)[:1000]}...
```

**사용자 요청:** {user_query}

**검증 및 개선 요구사항:**
1. **HTML 구조 검증**: DOCTYPE, meta tags, 올바른 태그 닫기
2. **Chart.js 차트 품질**: 실제 데이터 반영, 색상 일관성, 반응형
3. **CSS 스타일링**: 아름다운 디자인, 가독성, 반응형 레이아웃
4. **데이터 정확성**: 실제 수집된 데이터와 일치하는지 확인
5. **사용자 경험**: 인터랙티브 요소, 명확한 정보 전달
6. **브라우저 호환성**: 모든 브라우저에서 정상 작동

**반환 형식:**
- 개선된 완전한 HTML 코드만 반환
- 설명이나 주석은 제외
- 반드시 <!DOCTYPE html>부터 </html>까지 포함

개선된 HTML 코드:"""

            # LLM API 호출
            api_base_url = os.getenv("LLM_API_BASE_URL", "https://openrouter.ai/api/v1")
            model_name = os.getenv("LLM_MODEL_NAME", "deepseek/deepseek-chat")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:7001",
                "X-Title": "Report Generator"
            }

            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": validation_prompt}],
                "temperature": 0.3,
                "max_tokens": 8000
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{api_base_url}/chat/completions", json=payload, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    improved_html = result["choices"][0]["message"]["content"]
                    
                    # HTML 태그 추출
                    if "```html" in improved_html:
                        improved_html = improved_html.split("```html")[1].split("```")[0].strip()
                    elif "```" in improved_html:
                        improved_html = improved_html.split("```")[1].split("```")[0].strip()
                    
                    # 기본 HTML 구조 확인
                    if '<!DOCTYPE' in improved_html and '<html' in improved_html and '</html>' in improved_html:
                        logger.info("✅ HTML 검증 및 개선 완료")
                        return improved_html
                    else:
                        logger.warning("⚠️ 개선된 HTML이 완전하지 않음 - 원본 반환")
                        return html_content
                else:
                    logger.warning(f"HTML 검증 API 호출 실패: {response.status_code}")
                    return html_content
                    
        except Exception as e:
            logger.warning(f"HTML 검증 중 오류 (원본 반환): {e}")
            return html_content
    

    

class MCPToolDiscovery:
    """MCP 서버들을 자동으로 발견하고 도구를 등록하는 클래스"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
    
    async def discover_all_tools(self) -> List[BaseTool]:
        """모든 MCP 서버의 도구들을 발견하여 LangChain 도구로 변환"""
        
        all_tools: List[BaseTool] = []  # 명시적 타입 어노테이션
        
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
                    all_tools.append(dynamic_tool)  # type: ignore
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
    """에이전틱 워크플로우 - LLM이 MCP 도구들을 자동 발견하고 선택"""
    
    def __init__(self):
        # OpenRouter 기반 LLM 초기화
        api_key = os.getenv("LLM_API_KEY") or os.getenv("LLM_API_KEY")
        
        if not api_key:
            logger.warning("⚠️ LLM_API_KEY가 설정되지 않았습니다.")
        
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
        
        priority_names = ['get_region_codes', 'get_apt_trade_data', 'analyze_apartment_trade', 'html_report']
        
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
    
    def _create_workflow(self) -> Any:
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
        
        tool_messages: List[ToolMessage] = []
        
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
                    logger.info(f"🔍 execute_tools에서 {tool_name} 실행 - 스트리밍 래퍼 적용됨: {hasattr(target_tool, '_original_arun')}")
                    result = await target_tool._arun(**tool_args)
                    logger.info(f"✅ 도구 실행 완료: {tool_name}")
                    
                    # 🔥 html_report 완료 시 직접 알림 처리
                    if tool_name == "html_report" and hasattr(self.llm, 'streaming_callback') and self.llm.streaming_callback:
                        try:
                            logger.info(f"🔍 execute_tools에서 html_report 완료 감지!")
                            
                            # 가장 최근 생성된 리포트 파일 찾기
                            import os
                            import glob
                            reports_dir = os.getenv('REPORTS_PATH', './reports')
                            report_files = glob.glob(os.path.join(reports_dir, "report_*.html"))
                            
                            if report_files:
                                # 생성 시간 기준 최신 파일
                                latest_report = max(report_files, key=os.path.getctime)
                                logger.info(f"🎉 execute_tools에서 최신 리포트 감지: {latest_report}")
                                await self.llm.streaming_callback.send_report_update(latest_report)
                                
                                # HTML 파일에서 내용 읽어서 코드 뷰에 전송
                                with open(latest_report, 'r', encoding='utf-8') as f:
                                    html_content = f.read()
                                await self.llm.streaming_callback.send_code(html_content)
                                logger.info("🎨 execute_tools에서 HTML 코드를 UI로 전송 완료")
                            else:
                                logger.warning("🔍 execute_tools에서 리포트 파일을 찾을 수 없음")
                        except Exception as e:
                            logger.warning(f"execute_tools에서 리포트 알림 실패: {e}")
                
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
        """LLM 모델 호출 - 체계적 분석 및 도구 선택"""
        
        messages = state["messages"]
        user_query = state["user_query"]
        collected_data = state["collected_data"]
        current_step = state["current_step"]
        
        # 🤖 완전히 에이전틱한 워크플로우 - LLM이 스스로 전략 결정
        if len(messages) == 0:
            # 사용자 쿼리에서 JSON 데이터 감지
            json_data = None
            clean_query = user_query
            
            # JSON 패턴 감지 및 추출 - 개선된 정규표현식
            import re
            import json as json_module
            
            logger.info(f"🔍 JSON 감지 시도 - 전체 쿼리 길이: {len(user_query)}")
            
            # 개선된 JSON 패턴 - 중첩 가능한 구조 지원
            json_pattern = r'\{(?:[^{}]|{[^{}]*})*\}'
            json_matches = re.findall(json_pattern, user_query, re.DOTALL)
            
            if json_matches:
                try:
                    # 가장 큰 JSON 데이터 선택
                    largest_json = max(json_matches, key=len)
                    logger.info(f"🔍 선택된 JSON 크기: {len(largest_json)} 문자")
                    
                    json_data = json_module.loads(largest_json)
                    # 쿼리에서 JSON 부분 제거
                    clean_query = re.sub(json_pattern, '', user_query, flags=re.DOTALL).strip()
                    logger.info(f"🎯 JSON 데이터 파싱 성공! - 타입: {type(json_data)}")
                except Exception as e:
                    logger.warning(f"⚠️ JSON 파싱 실패: {e}")
                    json_data = None
            
            # JSON 데이터가 있으면 바로 HTML 생성으로 이동
            if json_data:
                logger.info("🚀 JSON 데이터 감지됨 - 직접 HTML 생성 모드")
                initial_prompt = f"""사용자가 다음 데이터와 함께 요청했습니다:

**요청:** {clean_query if clean_query else "데이터 시각화"}

**제공된 데이터:**
```json
{json_module.dumps(json_data, ensure_ascii=False, indent=2)}
```

사용자가 이미 분석할 데이터를 제공했으므로, MCP 도구를 호출하지 말고 직접 이 데이터를 분석하여 html_report 도구로 시각화 리포트를 생성해주세요.

지금 바로 html_report 도구를 호출하여 위 데이터를 analysis_data 매개변수로 전달하세요."""
            else:
                logger.info("🚀 진짜 에이전틱 모드 - 전략 기반 LLM 자율 분석")
                
                # 🔥 현재 날짜 추가
                from datetime import datetime
                current_date = datetime.now().strftime("%Y년 %m월")
                current_year_month = datetime.now().strftime("%Y%m")
                
                # 🔥 사용 가능한 모든 도구 정보를 LLM에 제공 (에이전틱 전략 수립용)
                tools_info = []
                for tool in self.tools:
                    tool_desc = {
                        "name": tool.name,
                        "description": tool.description,
                        "server": getattr(tool, 'server_name', 'builtin')
                    }
                    tools_info.append(tool_desc)
                
                tools_summary = "\n".join([
                    f"- **{tool['name']}** ({tool['server']}): {tool['description']}"
                    for tool in tools_info
                ])
                
                initial_prompt = f"""**현재 날짜: {current_date} (시스템 날짜: {current_year_month})**

**🚫 절대 금지사항:**
- 실제 도구 결과 없이 추측하거나 가정하지 마세요
- 파일 경로만 받고 내용을 확인하지 않으면 안됩니다
- 하드코딩된 날짜나 데이터를 사용하지 마세요

**사용자 요청:** {user_query}

**🎯 에이전틱 분석 전략:**

**1단계: 전략 수립**
먼저 명확한 분석 전략을 설명하세요:
- 어떤 데이터가 필요한지
- 어떤 순서로 도구를 사용할지
- 어떤 결과를 목표로 하는지

**2단계: 실제 데이터 수집**
- get_region_codes로 지역 코드 확인
- get_apt_trade_data로 실제 거래 데이터 수집 (최신 가능한 년월)
- analyze_apartment_trade로 **실제 데이터 분석**

**3단계: 실제 분석 결과만 사용**
- 파일 경로만 받으면 반드시 analyze_ 도구 사용
- 실제 분석 결과만을 기반으로 리포트 작성

**사용 가능한 도구들:**
{tools_summary}

**지금 시작하세요:**
1. 먼저 분석 전략을 명확히 설명하세요
2. 첫 번째 도구를 호출하여 시작하세요"""

            messages = [HumanMessage(content=initial_prompt)]
            logger.info(f"🔍 초기 프롬프트 길이: {len(initial_prompt)}")
            logger.info(f"🔍 초기 프롬프트 일부: {initial_prompt[:200]}...")
        
        # 🔥 에이전틱 워크플로우 제어 - LLM이 상황에 따라 자율적으로 다음 단계 결정
        else:
            last_message = messages[-1]
            
            # 도구 실행 결과가 있으면 LLM이 스스로 다음 단계 결정
            if isinstance(last_message, ToolMessage):
                content = last_message.content
                
                # 🔥 도구 실행 횟수 체크해서 충분한 데이터가 모였으면 HTML 생성
                tool_message_count = sum(1 for msg in messages if isinstance(msg, ToolMessage))
                analyze_completed = any('analyze_' in str(msg.content) for msg in messages if isinstance(msg, ToolMessage))
                
                logger.info(f"🔍 현재 도구 실행 횟수: {tool_message_count}개, 분석 완료: {analyze_completed}")
                
                if analyze_completed and tool_message_count >= 3:  # 분석 완료 + 3개 이상 도구 실행 시 HTML 생성
                    logger.warning(f"🔥 분석 완료 + 도구 실행 {tool_message_count}개 - HTML 리포트 생성 모드!")
                    
                    # 🔥 모든 ToolMessage에서 분석 데이터 수집
                    collected_analysis_data = []
                    for msg in messages:
                        if isinstance(msg, ToolMessage) and msg.content:
                            try:
                                # JSON 형태인지 확인 (문자열만 처리)
                                if isinstance(msg.content, str) and msg.content.strip().startswith('{') and msg.content.strip().endswith('}'):
                                    import json
                                    data = json.loads(msg.content)
                                    collected_analysis_data.append({
                                        "tool_name": getattr(msg, 'name', 'unknown'),
                                        "data": data
                                    })
                                else:
                                    collected_analysis_data.append({
                                        "tool_name": getattr(msg, 'name', 'unknown'), 
                                        "data": str(msg.content)
                                    })
                            except:
                                collected_analysis_data.append({
                                    "tool_name": getattr(msg, 'name', 'unknown'),
                                    "data": str(msg.content)
                                })
                    
                    # 🔥 실제 분석 데이터를 JSON 문자열로 변환
                    analysis_json = json.dumps(collected_analysis_data, ensure_ascii=False, indent=2)
                    
                    context_prompt = f"""이전 단계 결과:
{content}

**HTML 리포트 생성 단계**

지금까지의 **실제 분석 결과**를 바탕으로 html_report 도구를 호출하여 시각화된 리포트를 생성해주세요.

**사용자 요청:** {user_query}

**수집된 실제 분석 데이터:**
```json
{analysis_json}
```

**필수:**
- 반드시 html_report 도구를 호출하세요
- analysis_data 매개변수에 다음 JSON 문자열을 정확히 전달하세요:

```
{analysis_json}
```

**호출 예시:**
```json
{{
  "analysis_data": "{analysis_json.replace(chr(10), '\\n').replace('"', '\\"')}"
}}
```

지금 바로 html_report 도구를 호출하세요!"""
                elif tool_message_count >= 5:  # 5개 이상이면 텍스트 분석으로 종료
                    logger.warning(f"🔥 도구 실행 횟수 {tool_message_count}개 - 강제 텍스트 분석 모드!")
                    context_prompt = f"""이전 단계 결과:
{content}

**최종 분석 단계**

사용자의 요청 "{user_query}"에 대해 지금까지 수집한 **실제 데이터**를 바탕으로 상세한 분석 리포트를 작성해주세요.

**필수 포함 내용:**
1. 📊 실제 데이터 수집 결과 요약
2. 📈 실제 거래 동향 분석
3. 💰 실제 가격 분석 및 시장 상황
4. 🏠 실제 지역별 특성 분석
5. 💡 투자 시사점 및 전망

**필수:** 실제 수집된 데이터만을 기반으로 분석하세요!"""
                
                else:
                    # 🔥 파일 경로만 받은 경우 강제로 분석 도구 사용 요구
                    if '/raw_data/' in content and '.json' in content:
                        context_prompt = f"""이전 단계 결과:
{content}

**🚨 중요: 파일 경로만 받았습니다! 반드시 analyze_ 도구로 실제 데이터를 분석하세요**

**필수 다음 단계:**
- analyze_apartment_trade 도구를 사용하여 위 파일의 실제 내용을 분석하세요
- file_path 매개변수에 위 경로를 전달하세요
- 실제 분석 결과가 나올 때까지 추측하지 마세요

**절대 금지:** 파일 경로만으로 추측 분석하지 마세요!"""
                    else:
                        context_prompt = f"""이전 단계 결과:
{content}

위 결과를 바탕으로 사용자의 원래 요청 "{user_query}"을 완수하기 위한 다음 단계를 결정해주세요.

**옵션:**
1. 추가 데이터가 필요하면 적절한 도구를 호출
2. 파일 경로를 받았으면 analyze_ 도구로 실제 분석
3. 분석 결과가 있으면 html_report 도구로 시각화
4. 충분한 정보가 있으면 직접 답변 제공

**필수:** 실제 데이터 분석 결과만을 사용하세요!"""
                
                messages.append(HumanMessage(content=context_prompt))
        
        # 🔥 자율적 오류 처리 가이드라인 추가
        if messages and len(messages) > 2:  # 이미 대화가 진행 중인 경우
            # 최근 메시지에서 오류 감지
            recent_content = str(messages[-1].content) if messages else ""
            has_recent_error = any(keyword in recent_content.lower() for keyword in ["실패", "오류", "❌", "error", "failed"])
            
            if has_recent_error:
                autonomy_guide = HumanMessage(content="""🔥 **자율적 문제 해결 모드**

이전 단계에서 오류가 발생했습니다. 다음 중 하나를 **자율적으로 선택**하여 즉시 실행하세요:

1. **재시도**: 같은 도구를 다른 파라미터로 재시도
2. **대안 도구**: 다른 도구로 같은 목적 달성
3. **우회**: 다른 지역/기간 데이터로 분석
4. **생략**: 해당 단계를 건너뛰고 다음 단계 진행

**반드시 즉시 도구를 호출하세요!** 설명만 하지 말고 바로 행동하세요.""")
                messages.insert(-1, autonomy_guide)  # 마지막 전에 삽입

        # 🔥 LLM 추론 및 도구 선택
        try:
            logger.info(f"🧠 LLM 호출 - 메시지 수: {len(messages)}")
            
            # 🔥 LLM 사고 시작 알림
            if hasattr(self, 'streaming_callback') and self.streaming_callback:
                await self.streaming_callback.send_llm_start(os.getenv("LLM_NAME", "LLM"))
                await self.streaming_callback.send_analysis_step("llm_thinking", "🧠 AI가 상황을 분석하고 다음 단계를 결정하고 있습니다...")
            
            # 🔥 LangGraph 호환성을 위해 _generate를 직접 호출하고 AIMessage 추출 (state 전달)
            chat_result = self.llm_with_tools._generate(messages, state=state)
            if chat_result.generations and len(chat_result.generations) > 0:
                response = chat_result.generations[0].message
            else:
                logger.error("❌ LLM 응답에서 message를 찾을 수 없음")
                response = AIMessage(content="응답 생성에 실패했습니다.")
            
            logger.info(f"🔍 LLM 응답 유형: {type(response)}")
            logger.info(f"🔍 응답 내용: {getattr(response, 'content', 'No content')}")
            if hasattr(response, 'tool_calls'):
                logger.info(f"🔍 도구 호출: {len(response.tool_calls) if response.tool_calls else 0}개")
            
            # 🔥 도구 호출 디버깅 강화 및 진행 상황 표시
            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_names = [str(tc.get('name', 'unknown')) if isinstance(tc, dict) else str(tc) for tc in response.tool_calls]
                logger.info(f"✅ LLM이 {len(response.tool_calls)}개 도구 호출: {tool_names}")
                
                # 🔥 도구 선택 결과를 UI에 표시
                if hasattr(self, 'streaming_callback') and self.streaming_callback:
                    tool_list = ", ".join(tool_names)
                    await self.streaming_callback.send_analysis_step("tool_selection", f"🔧 AI가 다음 도구들을 선택했습니다: {tool_list}")
            else:
                logger.warning(f"⚠️ LLM이 도구를 호출하지 않음! 응답: {str(response.content)}")
                
                # 🔥 텍스트 분석 완료 후 HTML 생성 자동 트리거 (강화된 로직)
                # 🔥 HTML 자동 생성 로직 제거 - 무한루프 방지
                logger.info("🔥 텍스트 응답 완료 - HTML 자동 생성 비활성화")
                
                # 🔥 응답 생성 알림
                if hasattr(self, 'streaming_callback') and self.streaming_callback:
                    await self.streaming_callback.send_analysis_step("response_generation", "✍️ AI가 최종 응답을 생성하고 있습니다...")
                
                # 도구 호출 강제 디버깅
                logger.warning(f"⚠️ response.tool_calls 속성: {hasattr(response, 'tool_calls')}")
                if hasattr(response, 'tool_calls'):
                    logger.warning(f"⚠️ tool_calls 값: {response.tool_calls}")
            
            return {"messages": [response]}
            
        except Exception as e:
            logger.error(f"LLM 호출 실패: {e}")
            error_message = AIMessage(content=f"LLM 호출 중 오류가 발생했습니다: {str(e)}")
            return {"messages": [error_message]}
    
    def should_continue(self, state: WorkflowState) -> str:
        """🔥 에이전틱 워크플로우 제어 - 완전한 자율성 보장"""
        
        messages = state["messages"]
        collected_data = state["collected_data"]
        
        if not messages:
            return "continue"
        
        last_message = messages[-1]
        
        # 응답 내용 분석
        content = getattr(last_message, 'content', '')
        
        # 🔥 핵심: 도구 호출이 있으면 항상 계속 진행
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            logger.info(f"🔄 도구 호출 감지: {len(last_message.tool_calls)}개 - 계속 진행")
            return "continue"
            
        # 🔥 자율적 판단: 오류가 있으면 계속 진행, 완성된 응답만 종료
        if content and len(content) > 50:  # 50자 이상의 텍스트 응답이 있으면
            # 🎯 오류나 실패 키워드가 있으면 계속 진행 (재시도 허용)
            error_keywords = ["실패", "오류", "에러", "error", "failed", "❌", "⚠️", "문제"]
            has_error = any(keyword in content.lower() for keyword in error_keywords)
            
            if has_error:
                logger.info(f"🔄 오류 감지됨 - LLM이 자율적으로 재시도 가능: {content[:100]}...")
                return "continue"
            else:
                logger.info(f"✅ 완성된 응답 감지 ({len(content)}자) - 종료")
                return "end"
        
        # 🔥 안정성 우선: 메시지 수 제한 강화
        if len(messages) >= 20:  # 50개에서 20개로 안정성 강화
            logger.warning("⚠️ 최대 메시지 수 도달 (20개) - 종료")
            return "end"
        
        # 🔥 HTML 리포트 완성 감지 - 더 포괄적인 조건 (NoneType 방지)
        content_lower = content.lower() if content else ""
        if content_lower and ('html' in content_lower and (len(content) > 200 or 
            any(keyword in content_lower for keyword in ['<!doctype', '<html', '<head', '<body', 'html>', '</html']))):
            logger.info("✅ HTML 리포트 생성 완료 - 종료")
            return "end"
        
        # 🔥 도구 실행 결과만 확인 - 하드코딩 제거
        # ToolMessage인 경우 항상 계속 진행
        if isinstance(last_message, ToolMessage):
            logger.info("🔧 도구 실행 결과 감지 - 계속 진행")
            return "continue"
        
        # 🔥 에러 발생 시 복구 시도 (NoneType 방지)
        if content_lower and ('error' in content_lower or 'failed' in content_lower or '오류' in content_lower):
            logger.warning("⚠️ 에러 감지 - 복구 시도를 위해 계속 진행")
            return "continue"
        
        # 🔥 기본적으로 계속 진행 - 에이전틱 자율성 최대 보장
        logger.info("🔄 에이전틱 워크플로우 계속 진행")
        return "continue"
    
    async def run_with_streaming(self, user_query: str, streaming_callback, abort_check=None) -> Dict[str, Any]:
        """에이전틱 워크플로우 실행 - 스트리밍 콜백 지원"""
        
        # 도구 초기화 (필요시)
        await self.initialize_tools()
        
        logger.info("🚀 에이전틱 워크플로우 시작 - LLM이 MCP 도구들을 자율적으로 선택")
        
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
            
            # 🔥 AI 에이전트 분석 완료 메시지는 이후에 전송
            
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
                        logger.info(f"🔍 스트리밍 래퍼 실행됨 - {tool_name}")
                        
                        # 도구 시작 알림
                        try:
                            await streaming_callback.send_tool_start(tool_name, server_name)
                            logger.info(f"🔍 스트리밍 도구 시작 알림 완료 - {tool_name}")
                        except Exception as e:
                            logger.warning(f"스트리밍 도구 시작 알림 실패 ({tool_name}): {e}")
                        
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
                        
                        # 결과 요약 생성 및 오류 감지
                        result_str = str(result)
                        result_summary = result_str  # 길이 제한 제거 - 전체 결과 표시
                        
                        # 🎯 도구 실행 결과에서 오류 감지
                        error_indicators = ["실패", "오류", "에러", "error", "failed", "❌", "exception", "timeout"]
                        has_error = any(indicator in result_str.lower() for indicator in error_indicators)
                        
                        if has_error:
                            # 오류 상태로 알림
                            await streaming_callback.send_tool_complete(tool_name, f"❌ {result_summary}")
                            await streaming_callback.send_analysis_step("tool_error", f"⚠️ {tool_name} 실행에 문제가 발생했습니다. LLM이 자율적으로 재시도하거나 대안을 선택합니다...")
                            logger.warning(f"🔄 도구 실행 오류 감지: {tool_name} - {result_str[:200]}...")
                        else:
                            # 정상 완료 알림
                            await streaming_callback.send_tool_complete(tool_name, result_summary)
                            await streaming_callback.send_analysis_step("tool_completed", f"✅ {tool_name} 도구 실행이 완료되었습니다. 다음 단계를 진행합니다...")
                            logger.info(f"✅ 도구 정상 완료: {tool_name}")
                        
                        # 🔥 HTML 리포트 생성 완료 감지 - html_report 실행 시 무조건 처리
                        if tool_name == "html_report":
                            logger.info(f"🔍 html_report 완료됨 - 리포트 갱신 시작")
                            logger.info(f"🔍 html_report 감지됨!")
                            
                            # 가장 최근 생성된 리포트 파일 찾기
                            import os
                            import glob
                            reports_dir = os.getenv('REPORTS_PATH', './reports')
                            report_files = glob.glob(os.path.join(reports_dir, "report_*.html"))
                            
                            if report_files:
                                # 가장 최근 파일 선택 (파일명의 타임스탬프 기준)
                                latest_report = max(report_files, key=os.path.getctime)
                                logger.info(f"🎉 execute_tools에서 최신 리포트 감지: {latest_report}")
                                
                                # HTML 파일에서 내용 읽어서 코드 뷰에 전송
                                try:
                                    with open(latest_report, 'r', encoding='utf-8') as f:
                                        html_content = f.read()
                                    await streaming_callback.send_code(html_content, filename="report.html")
                                    logger.info("🎨 execute_tools에서 HTML 코드를 UI로 전송 완료")
                                except Exception as read_error:
                                    logger.warning(f"HTML 파일 읽기 실패: {read_error}")
                            else:
                                logger.warning("🔍 리포트 파일을 찾을 수 없음")
                        
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
        
        logger.info("🚀 에이전틱 워크플로우 시작 - LLM이 MCP 도구들을 자율적으로 선택")
        
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
            # 🔥 워크플로우 실행 - 안정성 우선 (recursion_limit 축소)
            config = {"recursion_limit": 25}  # 100에서 25로 안정성 우선
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