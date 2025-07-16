"""
Universal Report Generator Orchestrator
범용 리포트 생성 오케스트레이터 - 클로드 데스크탑 스타일
"""

import asyncio
import json
import logging
import os
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.llm_client import OpenRouterClient
from app.mcp_client import MCPClient
from app.code_executor import CodeExecutor
from app.utils.security import SecurityValidator
from app.strategic_reporter import StrategicReporter, StrategicReportConfig, ReportStyle, InsightLevel
from app.data_adapters import DataSourceManager
from app.universal_workflow import UniversalAgenticWorkflow

# 기존 워크플로우 (백업용)
try:
    from app.workflow_v2 import AgenticWorkflow
    LEGACY_WORKFLOW_AVAILABLE = True
except ImportError:
    LEGACY_WORKFLOW_AVAILABLE = False

logger = logging.getLogger(__name__)


class UniversalOrchestrator:
    """범용 리포트 생성 오케스트레이터"""
    
    def __init__(self):
        self.llm_client = OpenRouterClient()
        self.mcp_client = MCPClient()
        self.code_executor = CodeExecutor()
        self.security_validator = SecurityValidator()
        
        # 새로운 범용 시스템
        self.strategic_reporter = StrategicReporter()
        self.data_manager = DataSourceManager()
        self.universal_workflow = UniversalAgenticWorkflow(self.llm_client)
        
        # 레거시 워크플로우 (fallback)
        if LEGACY_WORKFLOW_AVAILABLE:
            self.legacy_workflow = AgenticWorkflow(self.llm_client)
        else:
            self.legacy_workflow = None
        
        logger.info("🚀 Universal Orchestrator 초기화 완료")
    
    async def generate_report(
        self,
        user_query: str,
        session_id: str,
        data_sources: Optional[List[str]] = None,
        report_style: str = "executive",
        insight_level: str = "intermediate",
        use_legacy: bool = False
    ) -> Dict[str, Any]:
        """
        범용 리포트 생성
        
        Args:
            user_query: 사용자 질문
            session_id: 세션 ID
            data_sources: 데이터 소스 목록
            report_style: 리포트 스타일 (executive, analytical, presentation, dashboard, narrative)
            insight_level: 인사이트 수준 (basic, intermediate, advanced)
            use_legacy: 레거시 시스템 사용 여부
        """
        
        start_time = datetime.now()
        
        try:
            logger.info(f"📊 범용 리포트 생성 시작 - Session: {session_id}")
            logger.info(f"   스타일: {report_style}, 인사이트 수준: {insight_level}")
            
            # 1. 데이터 수집
            context_data = await self._collect_data(data_sources, user_query)
            
            # 2. 컨텍스트 파일 생성
            context_file = await self._create_context_file(context_data, session_id)
            
            # 3. 리포트 생성 방식 선택
            if use_legacy and self.legacy_workflow:
                logger.info("🔄 레거시 워크플로우 사용")
                result = await self._generate_legacy_report(
                    user_query, context_data, session_id
                )
            else:
                logger.info("✨ 새로운 전략적 리포트 시스템 사용")
                result = await self._generate_strategic_report(
                    user_query, context_data, session_id, report_style, insight_level
                )
            
            # 4. 처리 시간 계산
            processing_time = (datetime.now() - start_time).total_seconds()
            result["processing_time"] = processing_time
            
            # 5. 결과 정리
            if result.get("success"):
                logger.info(f"✅ 리포트 생성 완료: {result.get('report_path')}")
                logger.info(f"   처리 시간: {processing_time:.2f}초")
            else:
                logger.error(f"❌ 리포트 생성 실패: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 오케스트레이터 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "report_path": None,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    async def _collect_data(
        self, 
        data_sources: Optional[List[str]], 
        user_query: str
    ) -> Dict[str, Any]:
        """데이터 수집"""
        
        context_data = {}
        
        if not data_sources:
            # 기본 샘플 데이터 사용
            context_data["main_data"] = self._get_sample_data()
            context_data["source"] = "sample_data"
            logger.info("📦 샘플 데이터 사용")
        else:
            # 실제 데이터 소스에서 수집
            for source in data_sources:
                try:
                    if source.startswith("mcp_"):
                        # MCP 데이터 수집
                        mcp_data = await self._collect_mcp_data(source, user_query)
                        context_data.update(mcp_data)
                    else:
                        # 파일 데이터 수집
                        file_data = await self._collect_file_data(source)
                        context_data.update(file_data)
                        
                except Exception as e:
                    logger.warning(f"데이터 소스 {source} 수집 실패: {e}")
                    continue
        
        # 데이터 검증 및 전처리
        processed_data = self.data_manager.process_data(context_data)
        
        return {
            "main_data": processed_data.main_data,
            "metadata": {
                "total_records": processed_data.metadata.total_records,
                "columns": processed_data.metadata.columns,
                "data_types": processed_data.metadata.data_types,
                "quality_score": processed_data.metadata.quality_score,
                "source_type": processed_data.metadata.source_type.value
            },
            "summary": processed_data.summary,
            "processing_notes": processed_data.processing_notes
        }
    
    async def _collect_mcp_data(self, source: str, user_query: str) -> Dict[str, Any]:
        """MCP 데이터 수집"""
        
        try:
            if "realestate" in source:
                # 부동산 데이터 수집
                result = await self.mcp_client.get_realestate_data(
                    region="전국", 
                    property_type="아파트"
                )
                return {"mcp_realestate": result}
            else:
                # 기본 MCP 데이터
                result = await self.mcp_client.execute_tool(source, {"query": user_query})
                return {"mcp_data": result}
                
        except Exception as e:
            logger.warning(f"MCP 데이터 수집 실패: {e}")
            return {}
    
    async def _collect_file_data(self, source: str) -> Dict[str, Any]:
        """파일 데이터 수집"""
        
        try:
            data_path = f"./data/{source}"
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    if source.endswith('.json'):
                        return {"file_data": json.load(f)}
                    else:
                        return {"file_data": f.read()}
            else:
                logger.warning(f"파일을 찾을 수 없음: {data_path}")
                return {}
                
        except Exception as e:
            logger.warning(f"파일 데이터 수집 실패: {e}")
            return {}
    
    def _get_sample_data(self) -> List[Dict[str, Any]]:
        """샘플 데이터 생성"""
        
        import random
        from datetime import datetime, timedelta
        
        # 다양한 산업/비즈니스 도메인의 샘플 데이터
        sample_data = []
        
        categories = ["Technology", "Healthcare", "Finance", "Retail", "Manufacturing"]
        regions = ["North", "South", "East", "West", "Central"]
        
        base_date = datetime.now() - timedelta(days=365)
        
        for i in range(50):
            record = {
                "id": i + 1,
                "category": random.choice(categories),
                "region": random.choice(regions),
                "revenue": round(random.uniform(10000, 100000), 2),
                "units_sold": random.randint(10, 1000),
                "customer_satisfaction": round(random.uniform(3.0, 5.0), 1),
                "date": (base_date + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d"),
                "growth_rate": round(random.uniform(-10, 25), 1),
                "market_share": round(random.uniform(5, 30), 1),
                "employee_count": random.randint(10, 500)
            }
            sample_data.append(record)
        
        return sample_data
    
    async def _create_context_file(
        self, 
        context_data: Dict[str, Any], 
        session_id: str
    ) -> str:
        """컨텍스트 파일 생성"""
        
        context_file = f"/tmp/context_{session_id}.json"
        
        with open(context_file, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"📄 컨텍스트 파일 생성: {context_file}")
        return context_file
    
    async def _generate_strategic_report(
        self,
        user_query: str,
        context_data: Dict[str, Any],
        session_id: str,
        report_style: str,
        insight_level: str
    ) -> Dict[str, Any]:
        """새로운 전략적 리포트 생성"""
        
        try:
            # 리포트 설정 생성
            config = StrategicReportConfig(
                title=self._generate_report_title(user_query),
                style=ReportStyle(report_style),
                insight_level=InsightLevel(insight_level),
                color_theme="professional",
                include_recommendations=True,
                include_methodology=insight_level == "advanced"
            )
            
            # 전략적 리포트 생성
            result = await self.strategic_reporter.generate_strategic_report(
                user_query=user_query,
                data=context_data,
                config=config,
                session_id=session_id
            )
            
            # 결과 보강
            if result.get("success"):
                # 리포트 URL 생성
                report_url = f"/reports/strategic_report_{session_id}.html"
                result["report_url"] = report_url
                
                # 추가 메타데이터
                result["report_type"] = "strategic"
                result["config"] = {
                    "style": config.style.value,
                    "insight_level": config.insight_level.value,
                    "color_theme": config.color_theme
                }
            
            return result
            
        except Exception as e:
            logger.error(f"전략적 리포트 생성 실패: {e}")
            
            # Universal Workflow로 fallback
            logger.info("🔄 Universal Workflow로 fallback")
            return await self._generate_universal_workflow_report(
                user_query, context_data, session_id
            )
    
    async def _generate_universal_workflow_report(
        self,
        user_query: str,
        context_data: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """범용 워크플로우 리포트 생성"""
        
        try:
            result = await self.universal_workflow.execute_workflow(
                user_query=user_query,
                context_data=context_data,
                session_id=session_id
            )
            
            if result.get("success"):
                # 생성된 코드 실행
                execution_result = await self._execute_generated_code(
                    result.get("generated_code", ""), session_id
                )
                
                if execution_result.get("success"):
                    result["report_url"] = f"/reports/report_{session_id}.html"
                    result["report_type"] = "universal_workflow"
                
            return result
            
        except Exception as e:
            logger.error(f"Universal Workflow 실패: {e}")
            
            # 마지막 수단: 레거시 워크플로우
            if self.legacy_workflow:
                return await self._generate_legacy_report(user_query, context_data, session_id)
            else:
                return {
                    "success": False,
                    "error": "모든 리포트 생성 방법이 실패했습니다.",
                    "report_path": None
                }
    
    async def _generate_legacy_report(
        self,
        user_query: str,
        context_data: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """레거시 워크플로우 리포트 생성"""
        
        try:
            if not self.legacy_workflow:
                raise Exception("레거시 워크플로우를 사용할 수 없습니다.")
            
            result = await self.legacy_workflow.execute_workflow(
                user_query=user_query,
                context_data=context_data,
                session_id=session_id
            )
            
            if result.get("success"):
                # 생성된 코드 실행
                execution_result = await self._execute_generated_code(
                    result.get("generated_code", ""), session_id
                )
                
                if execution_result.get("success"):
                    result["report_url"] = f"/reports/report_{session_id}.html"
                    result["report_type"] = "legacy"
                
            return result
            
        except Exception as e:
            logger.error(f"레거시 워크플로우 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "report_path": None
            }
    
    async def _execute_generated_code(self, code: str, session_id: str) -> Dict[str, Any]:
        """생성된 코드 실행"""
        
        try:
            # 보안 검증
            security_result = self.security_validator.validate_code(code)
            if not security_result.get("is_safe", False):
                return {
                    "success": False,
                    "error": f"보안 검증 실패: {security_result.get('issues', [])}"
                }
            
            # 코드 실행
            context_file = f"/tmp/context_{session_id}.json"
            execution_result = await self.code_executor.execute_python_code(
                code, session_id, context_file
            )
            
            return execution_result
            
        except Exception as e:
            logger.error(f"코드 실행 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_report_title(self, user_query: str) -> str:
        """사용자 쿼리에서 리포트 제목 생성"""
        
        # 키워드 기반 제목 생성
        keywords = user_query.lower().split()
        
        if any(word in keywords for word in ["분석", "analysis", "데이터"]):
            return "데이터 분석 리포트"
        elif any(word in keywords for word in ["트렌드", "trend", "추세"]):
            return "트렌드 분석 리포트"
        elif any(word in keywords for word in ["성과", "performance", "실적"]):
            return "성과 분석 리포트"
        elif any(word in keywords for word in ["비교", "compare", "comparison"]):
            return "비교 분석 리포트"
        elif any(word in keywords for word in ["예측", "forecast", "predict"]):
            return "예측 분석 리포트"
        else:
            return "종합 분석 리포트"
    
    def get_available_styles(self) -> List[str]:
        """사용 가능한 리포트 스타일 목록"""
        return [style.value for style in ReportStyle]
    
    def get_available_insight_levels(self) -> List[str]:
        """사용 가능한 인사이트 수준 목록"""
        return [level.value for level in InsightLevel]
    
    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 확인"""
        
        return {
            "strategic_reporter": "available",
            "universal_workflow": "available",
            "legacy_workflow": "available" if self.legacy_workflow else "unavailable",
            "data_manager": "available",
            "supported_styles": self.get_available_styles(),
            "supported_insight_levels": self.get_available_insight_levels(),
            "version": "2.0.0"
        } 