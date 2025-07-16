"""
Strategic Report Generator - Claude Desktop Style
클로드 데스크탑 스타일의 전략적 리포트 생성 시스템
"""

import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

from app.universal_workflow import UniversalAgenticWorkflow
from app.visualization_engine import VisualizationEngine
from app.template_generator import TemplateGenerator, TemplateConfig, VisualizationType
from app.data_adapters import DataSourceManager


class ReportStyle(Enum):
    """리포트 스타일"""
    EXECUTIVE = "executive"          # 경영진용 - 간결하고 핵심적
    ANALYTICAL = "analytical"       # 분석가용 - 상세하고 기술적
    PRESENTATION = "presentation"   # 발표용 - 시각적이고 임팩트 있음
    DASHBOARD = "dashboard"         # 대시보드 - 실시간 모니터링용
    NARRATIVE = "narrative"         # 스토리텔링 - 논리적 흐름 중심


class InsightLevel(Enum):
    """인사이트 수준"""
    BASIC = "basic"           # 기본 통계
    INTERMEDIATE = "intermediate"  # 패턴 분석
    ADVANCED = "advanced"     # 예측 및 권장사항


@dataclass
class ReportSection:
    """리포트 섹션"""
    id: str
    title: str
    content_type: str  # "text", "visualization", "metrics", "insights"
    priority: int
    content: Dict[str, Any]
    layout_hint: str = "full-width"  # "full-width", "half-width", "card"


@dataclass
class StrategicReportConfig:
    """전략적 리포트 설정"""
    title: str
    style: ReportStyle
    insight_level: InsightLevel
    color_theme: str = "professional"
    include_recommendations: bool = True
    include_methodology: bool = False
    max_sections: int = 8
    target_audience: str = "general"


class StrategicReporter:
    """클로드 데스크탑 스타일 전략적 리포트 생성기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_manager = DataSourceManager()
        self.viz_engine = VisualizationEngine()
        self.template_generator = TemplateGenerator()
        
        # 스타일별 템플릿
        self.style_templates = {
            ReportStyle.EXECUTIVE: self._get_executive_template(),
            ReportStyle.ANALYTICAL: self._get_analytical_template(),
            ReportStyle.PRESENTATION: self._get_presentation_template(),
            ReportStyle.DASHBOARD: self._get_dashboard_template(),
            ReportStyle.NARRATIVE: self._get_narrative_template()
        }
    
    async def generate_strategic_report(
        self,
        user_query: str,
        data: Any,
        config: StrategicReportConfig,
        session_id: str
    ) -> Dict[str, Any]:
        """전략적 리포트 생성"""
        
        self.logger.info(f"🎯 전략적 리포트 생성 시작: {config.style.value} 스타일")
        
        try:
            # 1. 데이터 전처리
            processed_data = self.data_manager.process_data(data)
            
            # 2. 데이터 분석
            field_analyses = self.viz_engine.analyze_data_structure(processed_data.main_data)
            
            # 3. 시각화 추천
            viz_recommendations = self.viz_engine.recommend_visualizations(
                field_analyses, user_query
            )
            
            # 4. 인사이트 생성
            insights = await self._generate_strategic_insights(
                processed_data, field_analyses, config.insight_level, user_query
            )
            
            # 5. 리포트 구조 설계
            report_structure = self._design_report_structure(
                config, insights, viz_recommendations
            )
            
            # 6. 섹션별 콘텐츠 생성
            sections = await self._generate_sections(
                report_structure, processed_data, field_analyses, viz_recommendations
            )
            
            # 7. 최종 HTML 생성
            html_content = self._assemble_final_report(
                config, sections, session_id
            )
            
            # 8. 리포트 저장
            report_path = f"./reports/strategic_report_{session_id}.html"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return {
                "success": True,
                "report_path": report_path,
                "sections_count": len(sections),
                "insights_count": len(insights),
                "style": config.style.value,
                "metadata": {
                    "total_records": processed_data.metadata.total_records,
                    "data_quality": processed_data.metadata.quality_score,
                    "processing_time": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ 전략적 리포트 생성 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "report_path": None
            }
    
    async def _generate_strategic_insights(
        self,
        processed_data,
        field_analyses: Dict[str, Any],
        insight_level: InsightLevel,
        user_query: str
    ) -> List[Dict[str, Any]]:
        """전략적 인사이트 생성"""
        
        insights = []
        
        # 기본 통계 인사이트
        if insight_level in [InsightLevel.BASIC, InsightLevel.INTERMEDIATE, InsightLevel.ADVANCED]:
            basic_insights = self._generate_basic_insights(processed_data, field_analyses)
            insights.extend(basic_insights)
        
        # 패턴 분석 인사이트
        if insight_level in [InsightLevel.INTERMEDIATE, InsightLevel.ADVANCED]:
            pattern_insights = self._generate_pattern_insights(field_analyses, user_query)
            insights.extend(pattern_insights)
        
        # 고급 인사이트 (예측 및 권장사항)
        if insight_level == InsightLevel.ADVANCED:
            advanced_insights = await self._generate_advanced_insights(
                processed_data, field_analyses, user_query
            )
            insights.extend(advanced_insights)
        
        return insights
    
    def _generate_basic_insights(self, processed_data, field_analyses: Dict[str, Any]) -> List[Dict[str, Any]]:
        """기본 통계 인사이트"""
        
        insights = []
        
        # 데이터 개요 인사이트
        insights.append({
            "type": "data_overview",
            "title": "데이터 개요",
            "content": f"총 {processed_data.metadata.total_records:,}개의 레코드와 {len(processed_data.metadata.columns)}개의 필드를 분석했습니다.",
            "importance": 0.7,
            "visual_hint": "info"
        })
        
        # 데이터 품질 인사이트
        quality_score = processed_data.metadata.quality_score
        quality_text = "우수" if quality_score > 0.8 else "양호" if quality_score > 0.6 else "개선 필요"
        
        insights.append({
            "type": "data_quality",
            "title": "데이터 품질",
            "content": f"데이터 품질은 {quality_text} 수준({quality_score:.1%})으로 평가됩니다.",
            "importance": 0.8,
            "visual_hint": "success" if quality_score > 0.8 else "warning",
            "metric": quality_score
        })
        
        # 필드별 핵심 인사이트
        for field_name, analysis in field_analyses.items():
            if hasattr(analysis, 'statistics') and analysis.statistics:
                if analysis.data_type.value in ['numeric_continuous', 'numeric_discrete']:
                    mean_val = analysis.statistics.get('mean', 0)
                    insights.append({
                        "type": "field_summary",
                        "title": f"{field_name} 분석",
                        "content": f"{field_name}의 평균값은 {mean_val:.2f}이며, 총 {analysis.unique_values}개의 고유값을 가집니다.",
                        "importance": 0.6,
                        "field": field_name
                    })
        
        return insights
    
    def _generate_pattern_insights(self, field_analyses: Dict[str, Any], user_query: str) -> List[Dict[str, Any]]:
        """패턴 분석 인사이트"""
        
        insights = []
        
        # 상관관계 패턴
        numeric_fields = [
            name for name, analysis in field_analyses.items()
            if hasattr(analysis, 'data_type') and analysis.data_type.value in ['numeric_continuous', 'numeric_discrete']
        ]
        
        if len(numeric_fields) >= 2:
            insights.append({
                "type": "correlation_pattern",
                "title": "변수 간 관계",
                "content": f"{len(numeric_fields)}개의 수치형 변수 간 상관관계 분석이 가능합니다. 특히 {numeric_fields[0]}와 {numeric_fields[1]} 간의 관계를 주목해보세요.",
                "importance": 0.8,
                "visual_hint": "scatter_plot",
                "fields": numeric_fields[:2]
            })
        
        # 분포 패턴
        for field_name, analysis in field_analyses.items():
            if hasattr(analysis, 'patterns') and analysis.patterns:
                for pattern in analysis.patterns:
                    if pattern == "right_skewed":
                        insights.append({
                            "type": "distribution_pattern",
                            "title": f"{field_name} 분포 특성",
                            "content": f"{field_name}은 우편향 분포를 보여, 대부분의 값이 낮은 범위에 집중되어 있습니다.",
                            "importance": 0.7,
                            "field": field_name
                        })
                    elif pattern == "has_outliers":
                        insights.append({
                            "type": "outlier_pattern",
                            "title": f"{field_name} 이상치 탐지",
                            "content": f"{field_name}에서 이상치가 탐지되었습니다. 데이터 검토가 필요할 수 있습니다.",
                            "importance": 0.9,
                            "visual_hint": "warning",
                            "field": field_name
                        })
        
        return insights
    
    async def _generate_advanced_insights(
        self,
        processed_data,
        field_analyses: Dict[str, Any],
        user_query: str
    ) -> List[Dict[str, Any]]:
        """고급 인사이트 (예측 및 권장사항)"""
        
        insights = []
        
        # 비즈니스 임팩트 분석
        insights.append({
            "type": "business_impact",
            "title": "비즈니스 임팩트",
            "content": "분석된 데이터를 바탕으로 향후 의사결정에 활용할 수 있는 핵심 지표들을 식별했습니다.",
            "importance": 0.9,
            "visual_hint": "target"
        })
        
        # 권장사항
        recommendations = self._generate_recommendations(processed_data, field_analyses, user_query)
        if recommendations:
            insights.append({
                "type": "recommendations",
                "title": "권장사항",
                "content": "데이터 분석 결과를 바탕으로 한 실행 가능한 권장사항입니다.",
                "importance": 1.0,
                "visual_hint": "action",
                "recommendations": recommendations
            })
        
        return insights
    
    def _generate_recommendations(
        self,
        processed_data,
        field_analyses: Dict[str, Any],
        user_query: str
    ) -> List[str]:
        """실행 가능한 권장사항 생성"""
        
        recommendations = []
        
        # 데이터 품질 기반 권장사항
        if processed_data.metadata.quality_score < 0.8:
            recommendations.append("데이터 품질 개선을 위한 데이터 정제 과정을 검토하세요.")
        
        # 데이터 양 기반 권장사항
        if processed_data.metadata.total_records < 100:
            recommendations.append("더 많은 데이터 수집을 통해 분석 신뢰성을 높이세요.")
        
        # 필드별 권장사항
        numeric_fields = [
            name for name, analysis in field_analyses.items()
            if hasattr(analysis, 'data_type') and analysis.data_type.value in ['numeric_continuous', 'numeric_discrete']
        ]
        
        if len(numeric_fields) >= 2:
            recommendations.append(f"{numeric_fields[0]}와 {numeric_fields[1]} 간의 상관관계를 심층 분석해보세요.")
        
        # 시계열 데이터 권장사항
        temporal_fields = [
            name for name, analysis in field_analyses.items()
            if hasattr(analysis, 'data_type') and analysis.data_type.value == 'temporal'
        ]
        
        if temporal_fields:
            recommendations.append("시계열 데이터를 활용한 트렌드 분석과 예측 모델링을 고려하세요.")
        
        return recommendations
    
    def _design_report_structure(
        self,
        config: StrategicReportConfig,
        insights: List[Dict[str, Any]],
        viz_recommendations: List[Dict[str, Any]]
    ) -> List[ReportSection]:
        """리포트 구조 설계"""
        
        sections = []
        
        # 스타일에 따른 섹션 구성
        if config.style == ReportStyle.EXECUTIVE:
            sections = self._design_executive_structure(insights, viz_recommendations)
        elif config.style == ReportStyle.ANALYTICAL:
            sections = self._design_analytical_structure(insights, viz_recommendations)
        elif config.style == ReportStyle.PRESENTATION:
            sections = self._design_presentation_structure(insights, viz_recommendations)
        elif config.style == ReportStyle.DASHBOARD:
            sections = self._design_dashboard_structure(insights, viz_recommendations)
        elif config.style == ReportStyle.NARRATIVE:
            sections = self._design_narrative_structure(insights, viz_recommendations)
        
        # 최대 섹션 수 제한
        return sections[:config.max_sections]
    
    def _design_executive_structure(
        self,
        insights: List[Dict[str, Any]],
        viz_recommendations: List[Dict[str, Any]]
    ) -> List[ReportSection]:
        """경영진용 구조"""
        
        return [
            ReportSection(
                id="executive_summary",
                title="Executive Summary",
                content_type="text",
                priority=1,
                content={"insights": [i for i in insights if i.get("importance", 0) > 0.8]},
                layout_hint="full-width"
            ),
            ReportSection(
                id="key_metrics",
                title="Key Performance Indicators",
                content_type="metrics",
                priority=2,
                content={"visualizations": viz_recommendations[:3]},
                layout_hint="card"
            ),
            ReportSection(
                id="strategic_insights",
                title="Strategic Insights",
                content_type="insights",
                priority=3,
                content={"insights": insights},
                layout_hint="half-width"
            ),
            ReportSection(
                id="recommendations",
                title="Recommendations",
                content_type="text",
                priority=4,
                content={"recommendations": [i for i in insights if i.get("type") == "recommendations"]},
                layout_hint="full-width"
            )
        ]
    
    def _design_analytical_structure(
        self,
        insights: List[Dict[str, Any]],
        viz_recommendations: List[Dict[str, Any]]
    ) -> List[ReportSection]:
        """분석가용 구조"""
        
        return [
            ReportSection(
                id="data_overview",
                title="Data Overview",
                content_type="text",
                priority=1,
                content={"insights": [i for i in insights if i.get("type") == "data_overview"]},
                layout_hint="full-width"
            ),
            ReportSection(
                id="statistical_analysis",
                title="Statistical Analysis",
                content_type="visualization",
                priority=2,
                content={"visualizations": viz_recommendations},
                layout_hint="full-width"
            ),
            ReportSection(
                id="pattern_analysis",
                title="Pattern Analysis",
                content_type="insights",
                priority=3,
                content={"insights": [i for i in insights if "pattern" in i.get("type", "")]},
                layout_hint="half-width"
            ),
            ReportSection(
                id="detailed_findings",
                title="Detailed Findings",
                content_type="text",
                priority=4,
                content={"insights": insights},
                layout_hint="full-width"
            )
        ]
    
    def _design_presentation_structure(
        self,
        insights: List[Dict[str, Any]],
        viz_recommendations: List[Dict[str, Any]]
    ) -> List[ReportSection]:
        """발표용 구조"""
        
        return [
            ReportSection(
                id="title_slide",
                title="Key Findings",
                content_type="text",
                priority=1,
                content={"insights": insights[:3]},
                layout_hint="full-width"
            ),
            ReportSection(
                id="visual_highlights",
                title="Visual Highlights",
                content_type="visualization",
                priority=2,
                content={"visualizations": viz_recommendations[:4]},
                layout_hint="card"
            ),
            ReportSection(
                id="impact_analysis",
                title="Impact Analysis",
                content_type="insights",
                priority=3,
                content={"insights": [i for i in insights if i.get("importance", 0) > 0.7]},
                layout_hint="half-width"
            )
        ]
    
    def _design_dashboard_structure(
        self,
        insights: List[Dict[str, Any]],
        viz_recommendations: List[Dict[str, Any]]
    ) -> List[ReportSection]:
        """대시보드 구조"""
        
        return [
            ReportSection(
                id="kpi_dashboard",
                title="Key Metrics Dashboard",
                content_type="metrics",
                priority=1,
                content={"visualizations": viz_recommendations},
                layout_hint="card"
            ),
            ReportSection(
                id="real_time_insights",
                title="Real-time Insights",
                content_type="insights",
                priority=2,
                content={"insights": insights},
                layout_hint="half-width"
            )
        ]
    
    def _design_narrative_structure(
        self,
        insights: List[Dict[str, Any]],
        viz_recommendations: List[Dict[str, Any]]
    ) -> List[ReportSection]:
        """스토리텔링 구조"""
        
        return [
            ReportSection(
                id="story_introduction",
                title="The Data Story",
                content_type="text",
                priority=1,
                content={"insights": [i for i in insights if i.get("type") == "data_overview"]},
                layout_hint="full-width"
            ),
            ReportSection(
                id="discovery_journey",
                title="Discovery Journey",
                content_type="visualization",
                priority=2,
                content={"visualizations": viz_recommendations},
                layout_hint="full-width"
            ),
            ReportSection(
                id="key_revelations",
                title="Key Revelations",
                content_type="insights",
                priority=3,
                content={"insights": insights},
                layout_hint="half-width"
            ),
            ReportSection(
                id="conclusion",
                title="Conclusion & Next Steps",
                content_type="text",
                priority=4,
                content={"recommendations": [i for i in insights if i.get("type") == "recommendations"]},
                layout_hint="full-width"
            )
        ]
    
    async def _generate_sections(
        self,
        report_structure: List[ReportSection],
        processed_data,
        field_analyses: Dict[str, Any],
        viz_recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """섹션별 콘텐츠 생성"""
        
        generated_sections = []
        
        for section in report_structure:
            section_content = await self._generate_section_content(
                section, processed_data, field_analyses, viz_recommendations
            )
            generated_sections.append(section_content)
        
        return generated_sections
    
    async def _generate_section_content(
        self,
        section: ReportSection,
        processed_data,
        field_analyses: Dict[str, Any],
        viz_recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """개별 섹션 콘텐츠 생성"""
        
        if section.content_type == "visualization":
            return await self._generate_visualization_section(section, viz_recommendations, field_analyses)
        elif section.content_type == "metrics":
            return await self._generate_metrics_section(section, processed_data, field_analyses)
        elif section.content_type == "insights":
            return self._generate_insights_section(section)
        else:  # text
            return self._generate_text_section(section)
    
    async def _generate_visualization_section(
        self,
        section: ReportSection,
        viz_recommendations: List[Dict[str, Any]],
        field_analyses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """시각화 섹션 생성"""
        
        charts = []
        for viz in section.content.get("visualizations", []):
            config = TemplateConfig(
                chart_type=VisualizationType(viz["chart_type"]),
                title=viz["config"]["title"],
                data_fields=viz["data_fields"],
                color_scheme="professional"
            )
            
            template = self.template_generator.generate_chart_template(config)
            charts.append({
                "type": viz["chart_type"],
                "title": viz["config"]["title"],
                "template": template,
                "reasoning": viz["reasoning"]
            })
        
        return {
            "id": section.id,
            "title": section.title,
            "type": "visualization",
            "layout": section.layout_hint,
            "charts": charts
        }
    
    async def _generate_metrics_section(
        self,
        section: ReportSection,
        processed_data,
        field_analyses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """메트릭 섹션 생성"""
        
        metrics = []
        
        # 기본 메트릭
        metrics.append({
            "title": "Total Records",
            "value": f"{processed_data.metadata.total_records:,}",
            "subtitle": "Data Points",
            "trend": "neutral"
        })
        
        metrics.append({
            "title": "Data Quality",
            "value": f"{processed_data.metadata.quality_score:.1%}",
            "subtitle": "Quality Score",
            "trend": "up" if processed_data.metadata.quality_score > 0.8 else "down"
        })
        
        metrics.append({
            "title": "Fields Analyzed",
            "value": str(len(processed_data.metadata.columns)),
            "subtitle": "Dimensions",
            "trend": "neutral"
        })
        
        # 수치형 필드의 주요 메트릭
        for field_name, analysis in field_analyses.items():
            if hasattr(analysis, 'statistics') and analysis.statistics:
                if analysis.data_type.value in ['numeric_continuous', 'numeric_discrete']:
                    mean_val = analysis.statistics.get('mean', 0)
                    metrics.append({
                        "title": field_name.replace('_', ' ').title(),
                        "value": f"{mean_val:.2f}",
                        "subtitle": "Average",
                        "trend": "neutral"
                    })
        
        return {
            "id": section.id,
            "title": section.title,
            "type": "metrics",
            "layout": section.layout_hint,
            "metrics": metrics[:6]  # 최대 6개 메트릭
        }
    
    def _generate_insights_section(self, section: ReportSection) -> Dict[str, Any]:
        """인사이트 섹션 생성"""
        
        insights = section.content.get("insights", [])
        
        return {
            "id": section.id,
            "title": section.title,
            "type": "insights",
            "layout": section.layout_hint,
            "insights": insights
        }
    
    def _generate_text_section(self, section: ReportSection) -> Dict[str, Any]:
        """텍스트 섹션 생성"""
        
        content = section.content
        
        return {
            "id": section.id,
            "title": section.title,
            "type": "text",
            "layout": section.layout_hint,
            "content": content
        }
    
    def _assemble_final_report(
        self,
        config: StrategicReportConfig,
        sections: List[Dict[str, Any]],
        session_id: str
    ) -> str:
        """최종 HTML 리포트 조합"""
        
        # 스타일별 템플릿 선택
        base_template = self.style_templates[config.style]
        
        # 섹션 HTML 생성
        sections_html = ""
        chart_scripts = ""
        
        for section in sections:
            section_html, section_scripts = self._render_section(section, config)
            sections_html += section_html
            chart_scripts += section_scripts
        
        # 최종 HTML 조합
        final_html = base_template.format(
            title=config.title,
            sections_html=sections_html,
            chart_scripts=chart_scripts,
            session_id=session_id,
            generated_at=datetime.now().strftime('%Y년 %m월 %d일 %H:%M'),
            color_theme=config.color_theme
        )
        
        return final_html
    
    def _render_section(self, section: Dict[str, Any], config: StrategicReportConfig) -> tuple[str, str]:
        """섹션 HTML 렌더링"""
        
        section_type = section["type"]
        layout = section["layout"]
        
        if section_type == "visualization":
            return self._render_visualization_section(section, layout, config)
        elif section_type == "metrics":
            return self._render_metrics_section(section, layout, config)
        elif section_type == "insights":
            return self._render_insights_section(section, layout, config)
        else:  # text
            return self._render_text_section(section, layout, config)
    
    def _render_visualization_section(
        self, 
        section: Dict[str, Any], 
        layout: str, 
        config: StrategicReportConfig
    ) -> tuple[str, str]:
        """시각화 섹션 렌더링"""
        
        charts_html = ""
        scripts = ""
        
        for chart in section.get("charts", []):
            chart_id = f"{section['id']}_{chart['type']}_chart"
            
            charts_html += f"""
            <div class="chart-wrapper {layout}">
                <h4 class="chart-title">{chart['title']}</h4>
                <div class="chart-description">{chart['reasoning']}</div>
                {chart['template']['html'].replace('Chart', chart_id)}
            </div>
            """
            
            scripts += chart['template']['javascript'].replace('Chart', chart_id)
            scripts += chart['template']['data_processing']
        
        section_html = f"""
        <section class="report-section {layout}" id="{section['id']}">
            <h2 class="section-title">{section['title']}</h2>
            <div class="charts-grid">
                {charts_html}
            </div>
        </section>
        """
        
        return section_html, scripts
    
    def _render_metrics_section(
        self, 
        section: Dict[str, Any], 
        layout: str, 
        config: StrategicReportConfig
    ) -> tuple[str, str]:
        """메트릭 섹션 렌더링"""
        
        metrics_html = ""
        
        for metric in section.get("metrics", []):
            trend_class = f"trend-{metric['trend']}"
            
            metrics_html += f"""
            <div class="metric-card">
                <div class="metric-value">{metric['value']}</div>
                <div class="metric-title">{metric['title']}</div>
                <div class="metric-subtitle {trend_class}">{metric['subtitle']}</div>
            </div>
            """
        
        section_html = f"""
        <section class="report-section {layout}" id="{section['id']}">
            <h2 class="section-title">{section['title']}</h2>
            <div class="metrics-grid">
                {metrics_html}
            </div>
        </section>
        """
        
        return section_html, ""
    
    def _render_insights_section(
        self, 
        section: Dict[str, Any], 
        layout: str, 
        config: StrategicReportConfig
    ) -> tuple[str, str]:
        """인사이트 섹션 렌더링"""
        
        insights_html = ""
        
        for insight in section.get("insights", []):
            visual_hint = insight.get("visual_hint", "info")
            importance = insight.get("importance", 0.5)
            
            insights_html += f"""
            <div class="insight-card {visual_hint}">
                <div class="insight-header">
                    <h4 class="insight-title">{insight['title']}</h4>
                    <div class="importance-badge" data-importance="{importance}">
                        {'⭐' * int(importance * 5)}
                    </div>
                </div>
                <div class="insight-content">{insight['content']}</div>
            </div>
            """
        
        section_html = f"""
        <section class="report-section {layout}" id="{section['id']}">
            <h2 class="section-title">{section['title']}</h2>
            <div class="insights-grid">
                {insights_html}
            </div>
        </section>
        """
        
        return section_html, ""
    
    def _render_text_section(
        self, 
        section: Dict[str, Any], 
        layout: str, 
        config: StrategicReportConfig
    ) -> tuple[str, str]:
        """텍스트 섹션 렌더링"""
        
        content = section.get("content", {})
        text_html = ""
        
        # 인사이트가 있는 경우
        if "insights" in content:
            for insight in content["insights"]:
                text_html += f"<p><strong>{insight['title']}:</strong> {insight['content']}</p>"
        
        # 권장사항이 있는 경우
        if "recommendations" in content:
            text_html += "<h4>권장사항:</h4><ul>"
            for rec in content["recommendations"]:
                if isinstance(rec, dict) and "recommendations" in rec:
                    for item in rec["recommendations"]:
                        text_html += f"<li>{item}</li>"
            text_html += "</ul>"
        
        section_html = f"""
        <section class="report-section {layout}" id="{section['id']}">
            <h2 class="section-title">{section['title']}</h2>
            <div class="text-content">
                {text_html}
            </div>
        </section>
        """
        
        return section_html, ""
    
    def _get_executive_template(self) -> str:
        """경영진용 템플릿"""
        return """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="/static/js/chart.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            background: #f8fafc;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 60px 40px;
            text-align: center;
            border-radius: 20px;
            margin-bottom: 40px;
            box-shadow: 0 20px 40px rgba(102, 126, 234, 0.3);
        }}
        
        .header h1 {{
            font-size: 3rem;
            font-weight: 300;
            margin-bottom: 20px;
            letter-spacing: -0.02em;
        }}
        
        .header .subtitle {{
            font-size: 1.2rem;
            opacity: 0.9;
        }}
        
        .report-section {{
            background: white;
            border-radius: 15px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid #e2e8f0;
        }}
        
        .section-title {{
            font-size: 2rem;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 30px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 15px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 25px;
            margin: 30px 0;
        }}
        
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            transition: transform 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-5px);
        }}
        
        .metric-value {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        
        .metric-title {{
            font-size: 1rem;
            font-weight: 500;
            opacity: 0.9;
        }}
        
        .insights-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
        }}
        
        .insight-card {{
            background: #f7fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 25px;
            transition: all 0.3s ease;
        }}
        
        .insight-card:hover {{
            border-color: #667eea;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.1);
        }}
        
        .insight-title {{
            font-size: 1.3rem;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 15px;
        }}
        
        .insight-content {{
            color: #4a5568;
            line-height: 1.7;
        }}
        
        .footer {{
            text-align: center;
            padding: 40px;
            color: #718096;
            font-size: 0.9rem;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 20px 10px;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
            
            .metrics-grid,
            .insights-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div class="subtitle">Strategic Analysis Report • {generated_at}</div>
        </div>
        
        {sections_html}
        
        <div class="footer">
            <p>Generated by Universal Analytics Platform</p>
            <p>Report ID: {session_id} • {generated_at}</p>
        </div>
    </div>
    
    <script>
        {chart_scripts}
        
        // 애니메이션 효과
        const sections = document.querySelectorAll('.report-section');
        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }}
            }});
        }}, {{ threshold: 0.1 }});
        
        sections.forEach(section => {{
            section.style.opacity = '0';
            section.style.transform = 'translateY(30px)';
            section.style.transition = 'all 0.6s ease';
            observer.observe(section);
        }});
    </script>
</body>
</html>
"""
    
    def _get_analytical_template(self) -> str:
        """분석가용 템플릿 (간소화)"""
        return self._get_executive_template().replace(
            "Strategic Analysis Report",
            "Detailed Analytical Report"
        )
    
    def _get_presentation_template(self) -> str:
        """발표용 템플릿 (간소화)"""
        return self._get_executive_template().replace(
            "Strategic Analysis Report",
            "Presentation Report"
        )
    
    def _get_dashboard_template(self) -> str:
        """대시보드 템플릿 (간소화)"""
        return self._get_executive_template().replace(
            "Strategic Analysis Report",
            "Dashboard Report"
        )
    
    def _get_narrative_template(self) -> str:
        """스토리텔링 템플릿 (간소화)"""
        return self._get_executive_template().replace(
            "Strategic Analysis Report",
            "Data Story Report"
        ) 