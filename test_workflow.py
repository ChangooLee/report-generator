#!/usr/bin/env python3
"""
새로운 에이전틱 워크플로우 테스트 스크립트
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.llm_client import OpenRouterClient
from app.workflow_v2 import AgenticWorkflow

async def test_workflow():
    """새로운 워크플로우를 테스트합니다."""
    
    print("🧪 에이전틱 워크플로우 테스트 시작")
    print("=" * 50)
    
    try:
        # LLM 클라이언트 초기화
        llm_client = OpenRouterClient()
        print("✅ LLM 클라이언트 초기화 완료")
        
        # 워크플로우 초기화
        workflow = AgenticWorkflow(llm_client)
        print("✅ 에이전틱 워크플로우 초기화 완료")
        
        # 테스트 데이터 준비
        test_context_data = {
            "main_data": [
                {"region": "서울", "premium": 1200000, "policies": 45, "date": "2024-01"},
                {"region": "부산", "premium": 800000, "policies": 32, "date": "2024-01"},
                {"region": "대구", "premium": 600000, "policies": 28, "date": "2024-01"},
                {"region": "서울", "premium": 1350000, "policies": 48, "date": "2024-02"},
                {"region": "부산", "premium": 850000, "policies": 35, "date": "2024-02"}
            ],
            "summary": {
                "total_premium": 4800000,
                "total_policies": 188,
                "regions": 3
            }
        }
        
        user_query = "삼성생명 지역별 보험료 현황을 분석하고 시각화된 리포트를 생성해주세요"
        session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"📝 테스트 쿼리: {user_query}")
        print(f"🔑 세션 ID: {session_id}")
        print(f"📊 테스트 데이터: {len(test_context_data['main_data'])}개 레코드")
        
        # 워크플로우 실행
        print("\n🚀 워크플로우 실행 중...")
        start_time = datetime.now()
        
        result = await workflow.execute_workflow(
            user_query=user_query,
            context_data=test_context_data,
            session_id=session_id
        )
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"\n⏱️  처리 시간: {processing_time:.2f}초")
        
        # 결과 분석
        if result["success"]:
            print("✅ 워크플로우 실행 성공!")
            print(f"📋 계획: {result.get('plan', {}).get('title', 'N/A')}")
            print(f"🔧 토큰 사용: {result.get('token_usage', 'N/A')}")
            print(f"📝 생성된 코드 길이: {len(result.get('python_code', ''))} 문자")
            
            # 생성된 코드 미리보기
            code = result.get('python_code', '')
            if code:
                print("\n📄 생성된 코드 미리보기 (처음 500자):")
                print("-" * 50)
                print(code[:500] + "..." if len(code) > 500 else code)
                print("-" * 50)
                
                # 코드 저장
                code_file = f"generated_code_{session_id}.py"
                with open(code_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                print(f"💾 생성된 코드 저장됨: {code_file}")
            
            # 계획 분석
            plan = result.get('plan', {})
            if plan:
                print(f"\n📊 계획 분석:")
                print(f"  - 제목: {plan.get('title', 'N/A')}")
                print(f"  - 섹션 수: {len(plan.get('sections', []))}")
                print(f"  - 차트 수: {len(plan.get('charts', []))}")
                print(f"  - 지표 수: {len(plan.get('metrics', []))}")
        else:
            print("❌ 워크플로우 실행 실패!")
            print(f"🔥 오류: {result.get('error', 'Unknown error')}")
        
        print("\n" + "=" * 50)
        print("🧪 테스트 완료")
        
        return result
        
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_token_optimization():
    """토큰 최적화 효과를 테스트합니다."""
    
    print("\n🔬 토큰 최적화 효과 테스트")
    print("=" * 50)
    
    try:
        # 간단한 프롬프트로 토큰 사용량 비교
        llm_client = OpenRouterClient()
        workflow = AgenticWorkflow(llm_client)
        
        # 1단계: 계획 수립만 테스트
        user_query = "간단한 데이터 분석 리포트를 만들어주세요"
        
        print("📝 1단계: 리포트 계획 수립 테스트")
        start_time = datetime.now()
        
        plan = await workflow._plan_report(user_query)
        
        end_time = datetime.now()
        planning_time = (end_time - start_time).total_seconds()
        
        print(f"⏱️  계획 수립 시간: {planning_time:.2f}초")
        print(f"📋 생성된 계획: {json.dumps(plan, ensure_ascii=False, indent=2)}")
        
        # 2단계: 데이터 분석 전략 테스트
        print("\n📊 2단계: 데이터 분석 전략 수립 테스트")
        test_data = {"main_data": [{"value": 100, "category": "A"}]}
        
        start_time = datetime.now()
        strategy = await workflow._analyze_data_strategy(plan, test_data)
        end_time = datetime.now()
        strategy_time = (end_time - start_time).total_seconds()
        
        print(f"⏱️  전략 수립 시간: {strategy_time:.2f}초")
        print(f"🎯 생성된 전략: {json.dumps(strategy, ensure_ascii=False, indent=2)}")
        
        total_optimization_time = planning_time + strategy_time
        print(f"\n⚡ 총 최적화 단계 시간: {total_optimization_time:.2f}초")
        
        return {
            "planning_time": planning_time,
            "strategy_time": strategy_time,
            "total_time": total_optimization_time,
            "plan": plan,
            "strategy": strategy
        }
        
    except Exception as e:
        print(f"❌ 토큰 최적화 테스트 실패: {e}")
        return None

def main():
    """메인 테스트 실행"""
    
    print("🧪 삼성생명 에이전틱 워크플로우 테스트")
    print("=" * 60)
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 비동기 테스트 실행
    try:
        # 기본 워크플로우 테스트
        workflow_result = asyncio.run(test_workflow())
        
        # 토큰 최적화 테스트
        optimization_result = asyncio.run(test_token_optimization())
        
        # 결과 요약
        print("\n📊 테스트 결과 요약")
        print("=" * 60)
        
        if workflow_result and workflow_result.get("success"):
            print("✅ 전체 워크플로우: 성공")
            print(f"   - 처리 시간: {workflow_result.get('processing_time', 'N/A'):.2f}초")
            print(f"   - 토큰 사용: {workflow_result.get('token_usage', 'N/A')}")
        else:
            print("❌ 전체 워크플로우: 실패")
        
        if optimization_result:
            print("✅ 토큰 최적화: 성공")
            print(f"   - 계획 수립: {optimization_result['planning_time']:.2f}초")
            print(f"   - 전략 수립: {optimization_result['strategy_time']:.2f}초")
            print(f"   - 총 시간: {optimization_result['total_time']:.2f}초")
        else:
            print("❌ 토큰 최적화: 실패")
        
        print(f"\n⏰ 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        print("\n⏹️  사용자에 의해 테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 