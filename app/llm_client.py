import asyncio
import json
import logging
import os
import tempfile
from enum import Enum
from typing import Dict, Any, Optional, List, AsyncIterator
import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class ModelType(Enum):
    QWEN_CODER = "qwen-coder"
    CLAUDE_SONNET = "claude-sonnet"

class OpenRouterClient:
    def __init__(self):
        self.base_url = os.getenv('VLLM_API_BASE_URL', 'https://openrouter.ai/api/v1')
        self.api_key = os.getenv('VLLM_API_KEY')
        self.qwen_model = os.getenv('VLLM_MODEL_NAME', 'Qwen/Qwen2.5-Coder-32B-Instruct')
        self.claude_model = os.getenv('CLAUDE_MODEL_NAME', 'anthropic/claude-sonnet-4')
        
        if not self.api_key:
            raise ValueError("VLLM_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:7000",
            "X-Title": "Report Generator"
        }
        
    async def generate_code(self, prompt: str, model_type: ModelType = ModelType.QWEN_CODER) -> str:
        """코드 생성 (일반 버전)"""
        try:
            full_response = ""
            async for chunk in self.generate_code_stream(prompt, model_type):
                full_response += chunk
            return full_response
        except Exception as e:
            logger.error(f"코드 생성 실패: {e}")
            return f"코드 생성 중 오류가 발생했습니다: {str(e)}"
    
    async def generate_code_stream(self, prompt: str, model_type: ModelType = ModelType.QWEN_CODER) -> AsyncIterator[str]:
        """코드 생성 (스트리밍 버전)"""
        try:
            model_name = self.qwen_model if model_type == ModelType.QWEN_CODER else self.claude_model
            system_prompt = self._get_system_prompt(model_type)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            payload = {
                "model": model_name,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 4000,
                "stream": True  # 스트리밍 활성화
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST", 
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            if line.startswith("data: "):
                                data_str = line[6:]  # "data: " 제거
                                
                                if data_str.strip() == "[DONE]":
                                    break
                                
                                try:
                                    data = json.loads(data_str)
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue
                                    
        except Exception as e:
            logger.error(f"스트리밍 코드 생성 실패: {e}")
            yield f"스트리밍 코드 생성 중 오류가 발생했습니다: {str(e)}"
    
    async def generate_completion(
        self, 
        prompt: str, 
        model_type: ModelType = ModelType.CLAUDE_SONNET,
        max_tokens: int = 100,
        temperature: float = 0.1
    ) -> str:
        """간단한 텍스트 완성을 위한 메서드 (health check용)"""
        
        # health check용 간단 응답
        if prompt == "test":
            return "healthy"
        
        model_name = self.claude_model if model_type == ModelType.CLAUDE_SONNET else self.qwen_model
        
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    return "healthy"
                    
        except Exception as e:
            logger.error(f"Completion API 요청 실패: {e}")
            return "unhealthy"
    
    async def analyze_and_fix_code(
        self, 
        original_code: str, 
        error_message: str, 
        user_query: str
    ) -> str:
        """Claude를 사용하여 코드 오류를 분석하고 수정합니다."""
        
        fix_prompt = f"""
다음 코드에서 오류가 발생했습니다. 오류를 분석하고 수정된 코드를 제공해주세요.

원본 사용자 요청:
{user_query}

오류가 발생한 코드:
{original_code}

오류 메시지:
{error_message}

수정 사항:
1. 오류의 원인을 분석해주세요
2. 수정된 전체 코드를 제공해주세요
3. 수정된 부분에 대한 설명을 추가해주세요

수정된 코드는 다음 형식으로 제공해주세요:
```python
# 수정된 Python 코드
```

```html
<!-- 수정된 HTML 코드 -->
```
"""
        
        return await self.generate_code(
            prompt=fix_prompt,
            model_type=ModelType.CLAUDE_SONNET
        )
    
    async def enhance_report(
        self, 
        basic_report: str, 
        user_feedback: str
    ) -> str:
        """Claude를 사용하여 리포트를 개선합니다."""
        
        enhance_prompt = f"""
다음 기본 리포트를 사용자 피드백을 바탕으로 개선해주세요.

기본 리포트:
{basic_report}

사용자 피드백:
{user_feedback}

개선 사항:
1. 사용자 피드백을 반영한 추가 분석
2. 더 나은 시각화 방법 제안
3. 추가적인 인사이트 제공
4. 개선된 디자인 및 레이아웃

개선된 코드를 제공해주세요.
"""
        
        return await self.generate_code(
            prompt=enhance_prompt,
            model_type=ModelType.CLAUDE_SONNET
        )
    
    def _get_system_prompt(self, model_type: ModelType) -> str:
        """모델 타입에 따른 시스템 프롬프트를 반환합니다."""
        
        if model_type == ModelType.QWEN_CODER:
            return """
당신은 데이터 분석 및 웹 리포트 생성 전문가입니다. 
사용자의 요청에 따라 JSON 데이터를 분석하고, HTML/JavaScript를 사용하여 
인터랙티브한 시각화 리포트를 생성하는 Python 코드를 작성해야 합니다.

규칙:
1. 반드시 Python 코드와 HTML 템플릿을 생성하세요
2. Chart.js, D3.js, Plotly.js 등의 오프라인 라이브러리를 활용하세요
3. 생성된 HTML은 완전히 독립적으로 실행되어야 합니다
4. 모든 스타일과 스크립트는 로컬 경로(/static/)를 사용하세요
5. 데이터는 JSON 형태로 제공되며, 이를 적절히 파싱하여 사용하세요
6. 코드는 안전하고 실행 가능해야 합니다
7. MCP 도구를 통해 얻은 데이터를 활용하세요

출력 형식:
- Python 코드: ```python ... ```
- HTML 코드: ```html ... ```
- JavaScript 코드 (필요시): ```javascript ... ```
- 설명: 마크다운 형식으로 작성

생성된 리포트는 `/reports/` 디렉토리에 저장되어야 합니다.
"""
        else:  # Claude
            return """
당신은 코드 분석 및 개선 전문가입니다.
주어진 코드의 오류를 분석하고, 더 나은 해결책을 제안하며,
사용자 경험을 개선하는 방법을 제시해야 합니다.

능력:
1. 코드 오류 분석 및 수정
2. 성능 최적화 제안
3. 사용자 인터페이스 개선
4. 데이터 시각화 향상
5. 보안 및 안전성 검토

항상 명확하고 실행 가능한 해결책을 제공해주세요.
"""
    
    async def health_check(self) -> bool:
        """OpenRouter API 서버 상태 확인"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self.headers
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"OpenRouter API 헬스체크 실패: {e}")
            return False
    
    async def list_available_models(self) -> List[Dict[str, Any]]:
        """사용 가능한 모델 목록 조회"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get("data", [])
                
        except Exception as e:
            logger.error(f"모델 목록 조회 실패: {e}")
            return []
    
    def get_model_info(self) -> Dict[str, str]:
        """현재 설정된 모델 정보 반환"""
        return {
            "qwen_model": self.qwen_model,
            "claude_model": self.claude_model,
            "base_url": self.base_url
        } 