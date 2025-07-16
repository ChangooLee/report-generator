#!/usr/bin/env python3
"""
Universal Report System Test
새로운 범용 리포트 시스템 테스트
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.orchestrator import UniversalOrchestrator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_universal.log')
    ]
)

logger = logging.getLogger(__name__)


async def test_strategic_report():
    """전략적 리포트 테스트"""
    
    print("🎯 전략적 리포트 시스템 테스트 시작")
    
    orchestrator = UniversalOrchestrator()
    
    # 테스트 시나리오들
    test_scenarios = [
        {
            "name": "Executive Summary Report",
            "query": "비즈니스 성과 데이터 분석 및 경영진 요약 리포트를 생성해주세요",
            "style": "executive",
            "insight_level": "advanced"
        },
        {
            "name": "Data Analysis Report", 
            "query": "고객 만족도와 매출 간의 상관관계를 분석해주세요",
            "style": "analytical",
            "insight_level": "intermediate"
        },
        {
            "name": "Presentation Report",
            "query": "지역별 성장률 트렌드를 시각화한 발표 자료를 만들어주세요",
            "style": "presentation", 
            "insight_level": "basic"
        },
        {
            "name": "Dashboard Report",
            "query": "실시간 KPI 대시보드를 생성해주세요",
            "style": "dashboard",
            "insight_level": "intermediate"
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(test_scenarios):
        print(f"\n📊 테스트 {i+1}: {scenario['name']}")
        print(f"   스타일: {scenario['style']}")
        print(f"   인사이트 수준: {scenario['insight_level']}")
        
        session_id = f"test_{scenario['style']}_{int(datetime.now().timestamp())}"
        
        try:
            result = await orchestrator.generate_report(
                user_query=scenario["query"],
                session_id=session_id,
                data_sources=None,  # 샘플 데이터 사용
                report_style=scenario["style"],
                insight_level=scenario["insight_level"],
                use_legacy=False
            )
            
            if result.get("success"):
                print(f"   ✅ 성공: {result.get('report_path', result.get('report_url'))}")
                print(f"   📈 처리 시간: {result.get('processing_time', 0):.2f}초")
                if "sections_count" in result:
                    print(f"   📑 섹션 수: {result['sections_count']}")
                if "insights_count" in result:
                    print(f"   💡 인사이트 수: {result['insights_count']}")
            else:
                print(f"   ❌ 실패: {result.get('error', 'Unknown error')}")
            
            results.append({
                "scenario": scenario["name"],
                "success": result.get("success", False),
                "processing_time": result.get("processing_time", 0),
                "report_type": result.get("report_type", "unknown"),
                "error": result.get("error") if not result.get("success") else None
            })
            
        except Exception as e:
            print(f"   💥 예외 발생: {e}")
            results.append({
                "scenario": scenario["name"],
                "success": False,
                "error": str(e)
            })
    
    return results


async def test_data_adapters():
    """데이터 어댑터 테스트"""
    
    print("\n🔄 데이터 어댑터 테스트")
    
    from app.data_adapters import DataSourceManager
    
    manager = DataSourceManager()
    
    # JSON 데이터 테스트
    test_json = {
        "data": [
            {"name": "Product A", "sales": 1000, "category": "Electronics"},
            {"name": "Product B", "sales": 1500, "category": "Home"},
            {"name": "Product C", "sales": 800, "category": "Electronics"}
        ],
        "metadata": {
            "source": "sales_db",
            "updated": "2024-01-15"
        }
    }
    
    try:
        processed = manager.process_data(test_json)
        print(f"   ✅ JSON 처리 성공:")
        print(f"      레코드 수: {processed.metadata.total_records}")
        print(f"      컬럼 수: {len(processed.metadata.columns)}")
        print(f"      품질 점수: {processed.metadata.quality_score:.2f}")
        print(f"      소스 타입: {processed.metadata.source_type.value}")
        
    except Exception as e:
        print(f"   ❌ JSON 처리 실패: {e}")
    
    # CSV 데이터 테스트
    test_csv = """name,sales,category
Product A,1000,Electronics
Product B,1500,Home
Product C,800,Electronics"""
    
    try:
        processed_csv = manager.process_data(test_csv)
        print(f"   ✅ CSV 처리 성공:")
        print(f"      레코드 수: {processed_csv.metadata.total_records}")
        print(f"      컬럼 수: {len(processed_csv.metadata.columns)}")
        
    except Exception as e:
        print(f"   ❌ CSV 처리 실패: {e}")


async def test_visualization_engine():
    """시각화 엔진 테스트"""
    
    print("\n📊 시각화 엔진 테스트")
    
    from app.visualization_engine import VisualizationEngine
    
    viz_engine = VisualizationEngine()
    
    # 샘플 데이터
    sample_data = [
        {"region": "North", "sales": 1000, "satisfaction": 4.2, "date": "2024-01-15"},
        {"region": "South", "sales": 1200, "satisfaction": 3.8, "date": "2024-01-16"},
        {"region": "East", "sales": 800, "satisfaction": 4.5, "date": "2024-01-17"},
        {"region": "West", "sales": 1100, "satisfaction": 4.0, "date": "2024-01-18"}
    ]
    
    try:
        # 데이터 분석
        field_analyses = viz_engine.analyze_data_structure(sample_data)
        print(f"   ✅ 필드 분석 완료: {len(field_analyses)}개 필드")
        
        for field_name, analysis in field_analyses.items():
            print(f"      {field_name}: {analysis.data_type.value} ({analysis.unique_values}개 고유값)")
        
        # 시각화 추천
        recommendations = viz_engine.recommend_visualizations(field_analyses, "지역별 매출 분석")
        print(f"   📈 시각화 추천: {len(recommendations)}개")
        
        for rec in recommendations[:3]:  # 상위 3개만 출력
            print(f"      - {rec['chart_type']}: {rec['reasoning']}")
        
    except Exception as e:
        print(f"   ❌ 시각화 엔진 테스트 실패: {e}")


async def test_template_generator():
    """템플릿 생성기 테스트"""
    
    print("\n🎨 템플릿 생성기 테스트")
    
    from app.template_generator import TemplateGenerator, TemplateConfig, VisualizationType
    
    generator = TemplateGenerator()
    
    # 다양한 차트 타입 테스트
    chart_types = [
        VisualizationType.BAR_CHART,
        VisualizationType.LINE_CHART,
        VisualizationType.PIE_CHART,
        VisualizationType.DATA_TABLE,
        VisualizationType.KPI_CARDS
    ]
    
    for chart_type in chart_types:
        try:
            config = TemplateConfig(
                chart_type=chart_type,
                title=f"Test {chart_type.value.title()}",
                data_fields=["region", "sales"],
                color_scheme="modern"
            )
            
            template = generator.generate_chart_template(config)
            
            print(f"   ✅ {chart_type.value} 템플릿 생성 성공")
            print(f"      HTML 길이: {len(template['html'])}")
            print(f"      JS 길이: {len(template['javascript'])}")
            
        except Exception as e:
            print(f"   ❌ {chart_type.value} 템플릿 생성 실패: {e}")


async def test_system_integration():
    """시스템 통합 테스트"""
    
    print("\n🔗 시스템 통합 테스트")
    
    orchestrator = UniversalOrchestrator()
    
    # 시스템 상태 확인
    status = orchestrator.get_system_status()
    print(f"   📊 시스템 버전: {status['version']}")
    print(f"   🎨 지원 스타일: {', '.join(status['supported_styles'])}")
    print(f"   💡 인사이트 수준: {', '.join(status['supported_insight_levels'])}")
    
    # 각 컴포넌트 상태
    for component, state in status.items():
        if component not in ['supported_styles', 'supported_insight_levels', 'version']:
            print(f"   📦 {component}: {state}")


async def main():
    """메인 테스트 실행"""
    
    print("🚀 범용 리포트 시스템 종합 테스트 시작")
    print("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # 1. 시스템 통합 테스트
        await test_system_integration()
        
        # 2. 데이터 어댑터 테스트
        await test_data_adapters()
        
        # 3. 시각화 엔진 테스트
        await test_visualization_engine()
        
        # 4. 템플릿 생성기 테스트
        await test_template_generator()
        
        # 5. 전략적 리포트 테스트
        results = await test_strategic_report()
        
        # 결과 요약
        print("\n" + "=" * 60)
        print("📋 테스트 결과 요약")
        
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r["success"])
        
        print(f"   총 테스트: {total_tests}")
        print(f"   성공: {successful_tests}")
        print(f"   실패: {total_tests - successful_tests}")
        print(f"   성공률: {successful_tests/total_tests*100:.1f}%")
        
        # 실패한 테스트 상세
        failed_tests = [r for r in results if not r["success"]]
        if failed_tests:
            print("\n❌ 실패한 테스트:")
            for test in failed_tests:
                print(f"   - {test['scenario']}: {test.get('error', 'Unknown error')}")
        
        # 성능 정보
        successful_results = [r for r in results if r["success"]]
        if successful_results:
            avg_time = sum(r.get("processing_time", 0) for r in successful_results) / len(successful_results)
            print(f"\n⏱️  평균 처리 시간: {avg_time:.2f}초")
        
        total_time = (datetime.now() - start_time).total_seconds()
        print(f"   전체 테스트 시간: {total_time:.2f}초")
        
        # 결과를 파일로 저장
        test_report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": successful_tests/total_tests*100,
            "total_time": total_time,
            "results": results
        }
        
        with open("test_results.json", "w", encoding="utf-8") as f:
            json.dump(test_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 상세 결과가 test_results.json에 저장되었습니다.")
        
    except Exception as e:
        print(f"\n💥 테스트 실행 중 치명적 오류: {e}")
        logger.exception("테스트 실행 오류")


if __name__ == "__main__":
    # 이벤트 루프 실행
    asyncio.run(main()) 