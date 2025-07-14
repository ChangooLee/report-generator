import httpx
import json
import os
import logging
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)

class ModelType(Enum):
    QWEN_CODER = "qwen-coder"
    CLAUDE_SONNET = "claude-sonnet"

class OpenRouterClient:
    def __init__(self):
        self.base_url = os.getenv('VLLM_API_BASE_URL', 'https://openrouter.ai/api/v1')
        self.api_key = os.getenv('VLLM_API_KEY')
        self.qwen_model = os.getenv('VLLM_MODEL_NAME', 'Qwen/Qwen2.5-Coder-32B-Instruct')
        self.claude_model = os.getenv('CLAUDE_MODEL_NAME', 'anthropic/claude-3.5-sonnet')
        
        if not self.api_key:
            raise ValueError("VLLM_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:7000",
            "X-Title": "Report Generator"
        }
        
    async def generate_code(
        self, 
        prompt: str, 
        model_type: ModelType = ModelType.QWEN_CODER,
        max_tokens: int = 4000,
        temperature: float = 0.1
    ) -> str:
        """LLM을 사용하여 코드를 생성합니다."""
        
        model_name = self.qwen_model if model_type == ModelType.QWEN_CODER else self.claude_model
        
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": self._get_system_prompt(model_type)
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.error(f"OpenRouter API 응답 형식 오류: {result}")
                    return ""
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API HTTP 오류 ({e.response.status_code}): {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"OpenRouter API 요청 실패: {e}")
            raise
    
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
            model_type=ModelType.CLAUDE_SONNET,
            max_tokens=4000,
            temperature=0.1
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
            model_type=ModelType.CLAUDE_SONNET,
            max_tokens=4000,
            temperature=0.2
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