"""
LangGraph Agentic Workflow
LangGraph 기반 에이전틱 워크플로우 - Claude가 MCP 도구들을 자동 발견하고 선택
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from dataclasses import dataclass
from datetime import datetime
import operator
import httpx # Added for OpenRouter API calls

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
        """메시지 생성 (표준 function calling 지원)"""
        
        # LangChain 메시지를 OpenRouter 형식으로 변환
        openrouter_messages = self._convert_messages(messages)
        
        # Claude에게 전달할 도구 스키마 생성
        tools_schema = self._create_tools_schema() if self.tools else None
        
        # OpenRouter 요청 페이로드 구성
        payload = {
            "model": "anthropic/claude-sonnet-4",
            "messages": openrouter_messages,
            "temperature": 0.3,
            "max_tokens": 4000,
            "stream": True
        }
        
        # 도구가 있으면 function calling 활성화
        if tools_schema:
            payload["tools"] = tools_schema
            payload["tool_choice"] = "auto"
        
        # 스트리밍 콜백이 있으면 LLM 시작 알림
        if self.streaming_callback:
            try:
                asyncio.run(self.streaming_callback.send_llm_start("Claude (OpenRouter)"))
                logger.info("🧠 Claude function calling 응답 생성 시작")
            except Exception as e:
                logger.error(f"스트리밍 시작 알림 실패: {e}")
        
        # OpenRouter API 호출 및 응답 수집
        try:
            response_content = ""
            tool_calls = []
            
            # 스트리밍으로 응답 수집
            async def collect_streaming_response():
                nonlocal response_content, tool_calls
                
                try:
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        async with client.stream(
                            "POST", 
                            "https://openrouter.ai/api/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {os.getenv('VLLM_API_KEY')}",
                                "Content-Type": "application/json",
                                "HTTP-Referer": "http://localhost:7001",
                                "X-Title": "Report Generator"
                            },
                            json=payload
                        ) as response:
                            response.raise_for_status()
                            
                            async for line in response.aiter_lines():
                                if line.strip():
                                    if line.startswith("data: "):
                                        data_str = line[6:]
                                        
                                        if data_str.strip() == "[DONE]":
                                            break
                                        
                                        try:
                                            data = json.loads(data_str)
                                            if "choices" in data and len(data["choices"]) > 0:
                                                choice = data["choices"][0]
                                                delta = choice.get("delta", {})
                                                
                                                # 텍스트 콘텐츠 처리
                                                if "content" in delta and delta["content"]:
                                                    content_chunk = delta["content"]
                                                    response_content += content_chunk
                                                    
                                                    # 스트리밍 콜백으로 실시간 전송
                                                    if self.streaming_callback:
                                                        try:
                                                            await self.streaming_callback.send_llm_chunk(content_chunk)
                                                        except Exception as e:
                                                            logger.error(f"스트리밍 청크 전송 실패: {e}")
                                                
                                                # 도구 호출 처리
                                                if "tool_calls" in delta and delta["tool_calls"]:
                                                    for tool_call_delta in delta["tool_calls"]:
                                                        if "function" in tool_call_delta:
                                                            function_info = tool_call_delta["function"]
                                                            tool_calls.append({
                                                                "name": function_info.get("name", ""),
                                                                "args": json.loads(function_info.get("arguments", "{}")),
                                                                "id": tool_call_delta.get("id", f"call_{len(tool_calls)}")
                                                            })
                                                            logger.info(f"🔧 Claude가 {function_info.get('name')} 도구 호출 요청")
                                        
                                        except json.JSONDecodeError:
                                            continue
                                            
                except Exception as e:
                    logger.error(f"OpenRouter API 호출 실패: {e}")
                    return f"API 호출 중 오류: {str(e)}", []
                
                return response_content, tool_calls
            
            # 동기 컨텍스트에서 비동기 함수 실행
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, collect_streaming_response())
                    response_content, tool_calls = future.result(timeout=120)
            except RuntimeError:
                response_content, tool_calls = asyncio.run(collect_streaming_response())
            
            logger.info(f"✅ Claude 응답 완료: {len(response_content)} 문자, {len(tool_calls)}개 도구 호출")
                
        except Exception as e:
            logger.error(f"Claude function calling 실패: {e}")
            response_content = f"Claude 응답 생성 중 오류: {str(e)}"
            tool_calls = []
        
        # AIMessage 생성
        ai_message = AIMessage(content=response_content)
        if tool_calls:
            ai_message.tool_calls = tool_calls
        
        return ChatResult(generations=[ChatGeneration(message=ai_message)])
    
    def _convert_messages(self, messages) -> List[Dict]:
        """LangChain 메시지를 OpenRouter 형식으로 변환"""
        openrouter_messages = []
        
        for msg in messages:
            if hasattr(msg, 'content') and msg.content:
                if isinstance(msg, HumanMessage):
                    openrouter_messages.append({
                        "role": "user", 
                        "content": str(msg.content)
                    })
                elif isinstance(msg, AIMessage):
                    openrouter_messages.append({
                        "role": "assistant", 
                        "content": str(msg.content)
                    })
                elif isinstance(msg, ToolMessage):
                    openrouter_messages.append({
                        "role": "tool", 
                        "content": str(msg.content),
                        "tool_call_id": getattr(msg, 'tool_call_id', 'unknown')
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
                        "html_content": {
                            "type": "string",
                            "description": "테스트할 HTML 리포트 내용"
                        }
                    },
                    "required": ["html_content"]
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
        """비동기 도구 실행"""
        try:
            logger.info("🌐 브라우저 HTML 테스트 시작")
            
            # html_content 매개변수 추출
            html_content = kwargs.get('html_content')
            if not html_content:
                return "❌ html_content 매개변수가 제공되지 않았습니다. 먼저 HTML 리포트를 생성해주세요."
            
            # HTML 파일 생성 및 브라우저 테스트
            test_result = await self.browser_agent.test_html_in_browser(html_content)
            
            if hasattr(test_result, 'success') and test_result.success:
                url = getattr(test_result, 'url', 'N/A')
                return f"브라우저 테스트 성공! URL: {url}"
            else:
                error = getattr(test_result, 'error', 'Unknown error')
                return f"브라우저 테스트 실패: {error}"
                
        except Exception as e:
            logger.error(f"❌ 브라우저 테스트 실패: {e}")
            return f"브라우저 테스트 중 오류 발생: {str(e)}"


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
        self.tools = await self.tool_discovery.discover_all_tools()
        
        # LLM에 도구 바인딩
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # 워크플로우 그래프 생성
        self.workflow = self._create_workflow()
        
        logger.info(f"✅ {len(self.tools)}개 도구와 함께 에이전틱 워크플로우 초기화 완료")
    
    def _create_workflow(self) -> StateGraph:
        """에이전틱 워크플로우 그래프 생성"""
        
        # 워크플로우 그래프 초기화
        workflow = StateGraph(WorkflowState)
        
        # 노드 추가
        workflow.add_node("agent", self.call_model)
        workflow.add_node("tools", ToolNode(self.tools))
        
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
        
        return workflow.compile()
    
    async def call_model(self, state: WorkflowState) -> Dict[str, Any]:
        """Claude 모델 호출 - 체계적 분석 및 도구 선택"""
        
        messages = state["messages"]
        user_query = state["user_query"]
        collected_data = state["collected_data"]
        current_step = state["current_step"]
        
        # 첫 번째 호출인 경우 체계적인 분석 프롬프트 생성
        if not messages:
            system_prompt = f"""당신은 부동산 데이터 분석 전문가입니다.

## 사용자 요청
{user_query}

## 사용 가능한 도구들
다음 도구들을 체계적으로 활용하여 분석을 수행하세요:

### 1단계: 지역 정보 수집
- get_region_codes: 지역명으로 법정동 코드 검색

### 2단계: 데이터 수집
- get_apt_trade_data: 아파트 매매 데이터
- get_apt_rent_data: 아파트 전월세 데이터  
- get_officetel_trade_data: 오피스텔 매매 데이터
- get_officetel_rent_data: 오피스텔 전월세 데이터
- get_commercial_property_trade_data: 상업용 부동산 데이터

### 3단계: 데이터 분석
- analyze_apartment_trade: 아파트 매매 분석
- analyze_apartment_rent: 아파트 전월세 분석
- analyze_officetel_trade: 오피스텔 매매 분석
- analyze_officetel_rent: 오피스텔 전월세 분석

### 4단계: 리포트 생성 및 테스트
- test_html_report: HTML 리포트 브라우저 테스트

## 분석 프로세스
1. 사용자 요청 분석 (지역, 기간, 부동산 유형 파악)
2. 필요한 지역 코드 획득
3. 관련 데이터 수집 (여러 개월/유형 가능)
4. 수집된 데이터 분석
5. HTML 리포트 생성
6. 브라우저 테스트

각 단계에서 결과를 확인하고 다음 단계를 진행하세요.
현재 단계에서 필요한 도구를 정확히 선택하여 호출하세요.

**중요**: 같은 도구를 반복 호출하지 말고, 단계별로 진행하세요."""

            messages = [HumanMessage(content=system_prompt)]
        
        # 진행 상황에 따른 컨텍스트 메시지 추가
        elif len(messages) > 1:
            # 이전 결과 분석 및 다음 단계 가이드
            last_message = messages[-1]
            
            context_prompt = f"""
## 현재 진행 상황
수집된 데이터: {list(collected_data.keys()) if collected_data else '없음'}
현재 단계: {current_step}

## 다음 단계 결정
이전 결과를 바탕으로 다음에 필요한 작업을 결정하세요:

1. 더 많은 데이터가 필요한가?
2. 수집된 데이터를 분석해야 하는가?
3. HTML 리포트를 생성해야 하는가?
4. 브라우저 테스트를 해야 하는가?

**적절한 도구를 선택하여 다음 단계를 진행하세요.**
"""
            messages.append(HumanMessage(content=context_prompt))
        
        # Claude 호출
        try:
            response = await self.llm_with_tools.ainvoke(messages)
            
            # 응답 로깅
            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_names = [str(tc.get('name', 'unknown')) if isinstance(tc, dict) else str(tc) for tc in response.tool_calls]
                logger.info(f"🔧 Claude가 {len(response.tool_calls)}개 도구 호출: {tool_names}")
            else:
                logger.info(f"💬 Claude 응답: {str(response.content)[:100]}...")
            
            return {"messages": [response]}
            
        except Exception as e:
            logger.error(f"Claude 호출 실패: {e}")
            error_message = AIMessage(content=f"Claude 호출 중 오류가 발생했습니다: {str(e)}")
            return {"messages": [error_message]}
    
    def should_continue(self, state: WorkflowState) -> str:
        """지능적 워크플로우 제어 - 다음 단계 결정"""
        
        messages = state["messages"]
        collected_data = state["collected_data"]
        
        if not messages:
            return "continue"
        
        last_message = messages[-1]
        
        # 도구 호출이 있으면 계속 진행
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            logger.info("🔄 도구 호출 감지 - 계속 진행")
            return "continue"
        
        # 메시지 수 제한 (무한 루프 방지)
        if len(messages) >= 25:
            logger.warning("⚠️ 최대 메시지 수 도달 - 종료")
            return "end"
        
        # 응답 내용 분석
        content = getattr(last_message, 'content', '').lower()
        
        # HTML 리포트가 완성되고 테스트까지 완료된 경우
        if all(keyword in content for keyword in ['html', '완료', '테스트']):
            logger.info("✅ HTML 리포트 생성 및 테스트 완료 - 종료")
            return "end"
        
        # 오류가 발생한 경우 - 몇 번 더 시도 후 종료
        if 'error' in content or 'oops' in content or '오류' in content:
            error_count = sum(1 for msg in messages if 'error' in str(getattr(msg, 'content', '')).lower())
            if error_count >= 3:
                logger.warning("⚠️ 연속 오류 발생 - 종료")
                return "end"
        
        # 충분한 데이터가 수집되고 분석이 완료된 경우
        if collected_data and len(collected_data) >= 3:
            if 'analysis' in content or '분석' in content:
                logger.info("📊 데이터 수집 및 분석 진행 중 - 계속")
                return "continue"
        
        # 아직 작업이 더 필요한 경우
        logger.info("🔄 더 많은 작업 필요 - 계속 진행")
        return "continue"
    
    async def run_with_streaming(self, user_query: str, streaming_callback) -> Dict[str, Any]:
        """스트리밍 콜백과 함께 에이전틱 워크플로우 실행"""
        
        # 도구 초기화 (필요시)
        await streaming_callback.send_status("🔧 MCP 도구들을 자동 발견하고 있습니다...")
        await self.initialize_tools()
        
        await streaming_callback.send_status(f"✅ {len(self.tools)}개 도구 발견 완료")
        
        logger.info("🚀 에이전틱 워크플로우 시작 - Claude가 MCP 도구들을 자율적으로 선택")
        
        # 도구들 래핑하여 스트리밍 콜백 추가
        await self._wrap_tools_with_streaming(streaming_callback)
        
        # LLM에 스트리밍 콜백 추가 (Pydantic 모델용)
        object.__setattr__(self.llm, 'streaming_callback', streaming_callback)
        
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
            await streaming_callback.send_analysis_step("workflow_start", "AI 에이전트 워크플로우를 시작합니다")
            
            # 워크플로우 실행 - Claude가 자율적으로 결정
            final_state = await self.workflow.ainvoke(initial_state)
            
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
        """도구들에 스트리밍 콜백 추가"""
        
        for tool in self.tools:
            # 원본 _arun 메서드 백업
            if not hasattr(tool, '_original_arun'):
                tool._original_arun = tool._arun
            
            # 스트리밍 콜백이 포함된 새로운 _arun 메서드 생성
            async def wrapped_arun(*args, **kwargs):
                tool_name = tool.name
                server_name = getattr(tool, 'server_name', 'builtin')
                
                try:
                    # 도구 시작 알림
                    await streaming_callback.send_tool_start(tool_name, server_name)
                    
                    # 원본 도구 실행
                    result = await tool._original_arun(*args, **kwargs)
                    
                    # 결과 요약 생성
                    result_str = str(result)
                    result_summary = result_str[:200] + "..." if len(result_str) > 200 else result_str
                    
                    # 도구 완료 알림
                    await streaming_callback.send_tool_complete(tool_name, result_summary)
                    
                    return result
                    
                except Exception as e:
                    # 도구 오류 알림
                    await streaming_callback.send_tool_error(tool_name, str(e))
                    raise
            
            # 메서드 교체
            tool._arun = wrapped_arun

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
            # 워크플로우 실행 - Claude가 자율적으로 결정
            final_state = await self.workflow.ainvoke(initial_state)
            
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


# 기존 클래스명 유지 (하위 호환성)
LangGraphRealEstateWorkflow = TrueAgenticWorkflow 