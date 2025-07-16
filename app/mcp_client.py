import asyncio
import json
import logging
import os
import subprocess
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MCPClient:
    """MCP 서버와 stdio 통신을 통해 데이터를 수집하는 클라이언트"""
    
    def __init__(self):
        self.active_servers = {}
        self.mcp_configs = {
            "kr-realestate": {
                "path": "/Users/lchangoo/Workspace/mcp-kr-realestate",
                "command": ["/Users/lchangoo/Workspace/mcp-kr-realestate/.venv310/bin/mcp-kr-realestate"],
                "description": "한국 부동산 정보 MCP 서버"
            }
        }
    
    async def start_mcp_server(self, server_name: str) -> bool:
        """MCP 서버를 시작합니다."""
        
        if server_name in self.active_servers:
            logger.info(f"MCP 서버 '{server_name}'이 이미 실행 중입니다.")
            return True
        
        config = self.mcp_configs.get(server_name)
        if not config:
            logger.error(f"알 수 없는 MCP 서버: {server_name}")
            return False
        
        try:
            # 서버 디렉토리 확인
            server_path = config["path"]
            if not os.path.exists(server_path):
                logger.error(f"MCP 서버 경로가 존재하지 않습니다: {server_path}")
                return False
            
            # 프로세스 시작
            process = await asyncio.create_subprocess_exec(
                *config["command"],
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=server_path
            )
            
            # 초기화 메시지 전송
            init_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "report-generator",
                        "version": "1.0.0"
                    }
                }
            }
            
            # 초기화 요청 전송
            init_response = await self._send_request(process, init_request)
            
            if not init_response or "error" in init_response:
                logger.error(f"MCP 서버 초기화 실패: {init_response}")
                process.terminate()
                return False
            
            # initialized notification 전송 (MCP 표준 필수)
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            
            # notification은 응답이 없으므로 직접 전송
            try:
                if process.stdin is None:
                    logger.error("프로세스 stdin이 None입니다")
                    process.terminate()
                    return False
                    
                message = json.dumps(initialized_notification) + "\n"
                process.stdin.write(message.encode())
                await process.stdin.drain()
                logger.info("MCP initialized notification 전송 완료")
            except Exception as e:
                logger.error(f"initialized notification 전송 실패: {e}")
                process.terminate()
                return False
            
            # 서버 등록
            self.active_servers[server_name] = {
                "process": process,
                "config": config,
                "capabilities": init_response.get("result", {}).get("capabilities", {}),
                "started_at": datetime.now()
            }
            
            logger.info(f"MCP 서버 '{server_name}' 시작 완료")
            return True
            
        except Exception as e:
            logger.error(f"MCP 서버 시작 실패: {e}")
            return False
    
    async def stop_mcp_server(self, server_name: str):
        """MCP 서버를 중지합니다."""
        
        if server_name not in self.active_servers:
            return
        
        try:
            server_info = self.active_servers[server_name]
            process = server_info["process"]
            
            # 정상 종료 시도
            process.terminate()
            
            # 5초 대기 후 강제 종료
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
            
            del self.active_servers[server_name]
            logger.info(f"MCP 서버 '{server_name}' 중지 완료")
            
        except Exception as e:
            logger.error(f"MCP 서버 중지 실패: {e}")
    
    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """MCP 서버에서 사용 가능한 도구 목록을 조회합니다."""
        
        if server_name not in self.active_servers:
            await self.start_mcp_server(server_name)
        
        if server_name not in self.active_servers:
            return []
        
        try:
            server_info = self.active_servers[server_name]
            process = server_info["process"]
            
            request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/list"
            }
            
            response = await self._send_request(process, request)
            
            if response and "result" in response:
                tools = response["result"].get("tools", [])
                logger.info(f"MCP 서버 '{server_name}'에서 {len(tools)}개 도구 발견")
                return tools
            
            return []
            
        except Exception as e:
            logger.error(f"도구 목록 조회 실패: {e}")
            return []
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """MCP 서버의 도구를 호출합니다."""
        
        if server_name not in self.active_servers:
            await self.start_mcp_server(server_name)
        
        if server_name not in self.active_servers:
            return {"error": f"MCP 서버 '{server_name}'을 시작할 수 없습니다."}
        
        try:
            server_info = self.active_servers[server_name]
            process = server_info["process"]
            
            request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            response = await self._send_request(process, request)
            
            if response and "result" in response:
                return response["result"]
            elif response and "error" in response:
                return {"error": response["error"]}
            else:
                return {"error": "응답을 받지 못했습니다."}
            
        except Exception as e:
            logger.error(f"도구 호출 실패: {e}")
            return {"error": str(e)}
    
    async def get_realestate_data(self, region: Optional[str] = None, property_type: Optional[str] = None) -> Dict[str, Any]:
        """부동산 데이터를 조회합니다."""
        
        try:
            # 부동산 서버 시작
            server_started = await self.start_mcp_server("kr-realestate")
            if not server_started:
                return {"error": "부동산 MCP 서버를 시작할 수 없습니다."}
            
            # 도구 목록 조회
            tools = await self.list_tools("kr-realestate")
            
            # 적절한 도구 찾기
            search_tool = None
            for tool in tools:
                if "search" in tool.get("name", "").lower() or "부동산" in tool.get("description", ""):
                    search_tool = tool["name"]
                    break
            
            if not search_tool:
                # 기본 도구 이름들 시도
                common_tool_names = ["search_properties", "get_properties", "search", "list"]
                for tool_name in common_tool_names:
                    if any(t["name"] == tool_name for t in tools):
                        search_tool = tool_name
                        break
            
            if not search_tool:
                return {
                    "error": "부동산 검색 도구를 찾을 수 없습니다.",
                    "available_tools": [t.get("name") for t in tools]
                }
            
            # 도구 호출
            arguments = {}
            if region:
                arguments["region"] = region
            if property_type:
                arguments["type"] = property_type
            
            result = await self.call_tool("kr-realestate", search_tool, arguments)
            
            return result
            
        except Exception as e:
            logger.error(f"부동산 데이터 조회 실패: {e}")
            return {"error": str(e)}
    
    async def _send_request(self, process: asyncio.subprocess.Process, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """MCP 서버에 요청을 전송하고 응답을 받습니다."""
        
        try:
            # stdin/stdout 확인
            if process.stdin is None or process.stdout is None:
                logger.error("프로세스의 stdin 또는 stdout이 None입니다")
                return None
            
            # 요청 직렬화 및 전송
            request_data = json.dumps(request) + "\n"
            process.stdin.write(request_data.encode())
            await process.stdin.drain()
            
            # 응답 대기 (타임아웃 30초)
            response_line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=30.0
            )
            
            if not response_line:
                return None
            
            # 응답 파싱
            response_text = response_line.decode().strip()
            if not response_text:
                return None
            
            response = json.loads(response_text)
            return response
            
        except asyncio.TimeoutError:
            logger.error("MCP 서버 응답 시간 초과")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"MCP 응답 파싱 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"MCP 요청 전송 실패: {e}")
            return None
    
    async def discover_mcp_server(self, server_path: str) -> Dict[str, Any]:
        """MCP 서버의 기능을 탐색합니다."""
        
        temp_server_name = f"temp_{uuid.uuid4().hex[:8]}"
        
        try:
            # 임시 서버 설정
            if server_path.endswith('.js'):
                command = ["node", server_path]
            elif server_path.endswith('.py'):
                command = ["python", server_path]
            else:
                # 디렉토리인 경우 package.json 확인
                package_json_path = os.path.join(server_path, "package.json")
                if os.path.exists(package_json_path):
                    command = ["node", "dist/index.js"]
                else:
                    command = ["python", "main.py"]
            
            self.mcp_configs[temp_server_name] = {
                "path": os.path.dirname(server_path) if os.path.isfile(server_path) else server_path,
                "command": command,
                "description": f"임시 MCP 서버: {server_path}"
            }
            
            # 서버 시작 및 탐색
            server_started = await self.start_mcp_server(temp_server_name)
            if not server_started:
                return {"error": "서버를 시작할 수 없습니다."}
            
            # 서버 정보 수집
            server_info = self.active_servers[temp_server_name]
            tools = await self.list_tools(temp_server_name)
            
            discovery_result = {
                "path": server_path,
                "capabilities": server_info["capabilities"],
                "tools": tools,
                "command": command,
                "started_at": server_info["started_at"].isoformat()
            }
            
            return discovery_result
            
        except Exception as e:
            logger.error(f"MCP 서버 탐색 실패: {e}")
            return {"error": str(e)}
        finally:
            # 임시 서버 정리
            if temp_server_name in self.active_servers:
                await self.stop_mcp_server(temp_server_name)
            if temp_server_name in self.mcp_configs:
                del self.mcp_configs[temp_server_name]
    
    async def shutdown_all(self):
        """모든 MCP 서버를 종료합니다."""
        
        tasks = []
        for server_name in list(self.active_servers.keys()):
            tasks.append(self.stop_mcp_server(server_name))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("모든 MCP 서버가 종료되었습니다.")
    
    def get_server_status(self) -> Dict[str, Any]:
        """실행 중인 MCP 서버의 상태를 반환합니다."""
        
        status = {}
        for server_name, server_info in self.active_servers.items():
            process = server_info["process"]
            status[server_name] = {
                "running": process.returncode is None,
                "config": server_info["config"],
                "capabilities": server_info["capabilities"],
                "started_at": server_info["started_at"].isoformat(),
                "pid": process.pid if process.returncode is None else None
            }
        
        return status 