#!/usr/bin/env python3
"""
Claude 기반 LangGraph 워크플로우 직접 테스트
"""

import asyncio
import os
import sys
import logging

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.langgraph_workflow import TrueAgenticWorkflow

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_workflow():
    """워크플로우 테스트"""
    
    print("🧪 Claude 기반 워크플로우 테스트 시작")
    
    # API 키 확인 (.env 파일 로드)
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        print("⚠️ CLAUDE_API_KEY 환경변수가 설정되지 않았습니다.")
        print(".env 파일에 CLAUDE_API_KEY를 설정하세요.")
        print()
        print("테스트용으로 Mock 응답을 시뮬레이션합니다...")
        return
    
    print(f"✅ Claude API 키 확인됨: {api_key[:20]}...")
    
    try:
        # 워크플로우 초기화
        workflow = TrueAgenticWorkflow()
        
        # 테스트 쿼리
        test_query = "강동구 아파트 매매분석"
        
        print(f"📊 사용자 쿼리: {test_query}")
        print("🚀 워크플로우 실행 중...")
        
        # 워크플로우 실행
        result = await workflow.run(test_query)
        
        # 결과 출력
        print("\n" + "="*50)
        print("📋 실행 결과:")
        print(f"✅ 성공: {result['success']}")
        
        if result['success']:
            print(f"📄 리포트 길이: {len(result.get('report_content', ''))}")
            print(f"📊 수집된 데이터: {len(result.get('collected_data', {}))}")
            print(f"🌐 브라우저 테스트 URL: {result.get('browser_test_url', 'N/A')}")
            print(f"✓ 검증 통과: {result.get('validation_passed', False)}")
            print(f"💬 메시지 수: {len(result.get('messages', []))}")
        else:
            print(f"❌ 에러: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_workflow()) 