#!/usr/bin/env python3
"""
디버깅용: 우리 시스템의 도구 스키마 확인
"""

import asyncio
import json
import httpx
from app.langgraph_workflow import TrueAgenticWorkflow

async def debug_tool_schema():
    """우리 시스템의 도구 스키마를 확인하고 OpenRouter에 직접 테스트"""
    
    # 워크플로우 초기화
    workflow = TrueAgenticWorkflow()
    await workflow.initialize_tools()
    
    print(f"🔧 발견된 도구 수: {len(workflow.tools)}")
    
    # 첫 3개 도구만 테스트
    test_tools = workflow.tools[:3]
    
    # 도구 스키마 생성
    tools_schema = workflow.llm._create_tools_schema()
    
    print(f"🔧 생성된 스키마 수: {len(tools_schema)}")
    print("🔧 첫 번째 도구 스키마:")
    print(json.dumps(tools_schema[0], indent=2, ensure_ascii=False))
    
    # OpenRouter API에 직접 테스트
    api_key = "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"
    
    payload = {
        "model": "anthropic/claude-sonnet-4",
        "messages": [
            {
                "role": "user",
                "content": "강남구의 지역 코드를 검색해주세요."
            }
        ],
        "tools": tools_schema[:3],  # 첫 3개만 테스트
        "tool_choice": "auto",
        "max_tokens": 500
    }
    
    print("🚀 OpenRouter API 직접 테스트 시작...")
    
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
        print("✅ OpenRouter 응답:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(debug_tool_schema()) 