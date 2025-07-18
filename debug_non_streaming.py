#!/usr/bin/env python3
"""
디버깅용: 비스트리밍 모드로 테스트
"""

import asyncio
import json
import httpx

async def debug_non_streaming():
    """비스트리밍 모드로 OpenRouter API 테스트"""
    
    api_key = "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"
    
    # 비스트리밍 모드
    payload = {
        "model": "anthropic/claude-sonnet-4",
        "messages": [
            {
                "role": "user",
                "content": "강남구의 지역 코드를 검색해주세요."
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_region_codes",
                    "description": "지역명으로 법정동 코드를 검색합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "region_name": {
                                "type": "string",
                                "description": "검색할 지역명 (예: 강남구, 강동구)"
                            }
                        },
                        "required": ["region_name"]
                    }
                }
            }
        ],
        "tool_choice": "auto",
        "max_tokens": 500,
        "stream": False  # 🔥 비스트리밍 모드
    }
    
    print("🚀 비스트리밍 모드 테스트...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:7001"
            },
            json=payload
        )
        
        result = response.json()
        print("✅ 비스트리밍 응답:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # tool_calls 확인
        if "choices" in result and len(result["choices"]) > 0:
            message = result["choices"][0]["message"]
            if "tool_calls" in message and message["tool_calls"]:
                print(f"🔧 tool_calls 발견: {len(message['tool_calls'])}개")
                for i, tc in enumerate(message["tool_calls"]):
                    print(f"  {i+1}. {tc['function']['name']}: {tc['function']['arguments']}")
            else:
                print("⚠️ tool_calls 없음")

if __name__ == "__main__":
    asyncio.run(debug_non_streaming()) 