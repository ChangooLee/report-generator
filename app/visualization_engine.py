"""
Data-Driven Visualization Recommendation Engine
데이터 특성 기반 자동 시각화 추천 및 생성 엔진
"""

import json
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime
import re


class DataType(Enum):
    """데이터 타입 분류"""
    NUMERIC_CONTINUOUS = "numeric_continuous"
    NUMERIC_DISCRETE = "numeric_discrete"
    CATEGORICAL_NOMINAL = "categorical_nominal"
    CATEGORICAL_ORDINAL = "categorical_ordinal"
    TEMPORAL = "temporal"
    GEOGRAPHICAL = "geographical"
    TEXT = "text"
    BOOLEAN = "boolean"


class ChartRecommendation(Enum):
    """차트 타입 추천"""
    BAR_CHART = "bar"
    LINE_CHART = "line"
    PIE_CHART = "pie"
    SCATTER_PLOT = "scatter"
    AREA_CHART = "area"
    HEATMAP = "heatmap"
    HISTOGRAM = "histogram"
    BOX_PLOT = "box"
    GAUGE_CHART = "gauge"
    TREEMAP = "treemap"
    RADAR_CHART = "radar"
    TABLE = "table"
    SANKEY = "sankey"
    BUBBLE_CHART = "bubble"


@dataclass
class FieldAnalysis:
    """필드 분석 결과"""
    field_name: str
    data_type: DataType
    unique_values: int
    null_percentage: float
    sample_values: List[Any]
    statistics: Dict[str, Any]
    patterns: List[str]


@dataclass
class VisualizationRule:
    """시각화 규칙"""
    conditions: Dict[str, Any]
    chart_type: ChartRecommendation
    priority: int
    reasoning: str
    config_template: Dict[str, Any]


class VisualizationEngine:
    """데이터 기반 시각화 자동 추천 엔진"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rules = self._initialize_visualization_rules()
        
    def analyze_data_structure(self, data: Dict[str, Any]) -> Dict[str, FieldAnalysis]:
        """데이터 구조 및 필드별 특성 분석"""
        
        field_analyses: Dict[str, FieldAnalysis] = {}
        
        # 메인 데이터 추출
        main_data = self._extract_main_data(data)
        if not main_data:
            return field_analyses
        
        # DataFrame 변환
        try:
            df = pd.DataFrame(main_data)
        except Exception as e:
            self.logger.warning(f"DataFrame 변환 실패: {e}")
            return field_analyses
        
        # 각 필드 분석
        for column in df.columns:
            try:
                analysis = self._analyze_field(df, column)
                field_analyses[column] = analysis
            except Exception as e:
                self.logger.warning(f"필드 {column} 분석 실패: {e}")
                continue
        
        return field_analyses
    
    def recommend_visualizations(
        self, 
        field_analyses: Dict[str, FieldAnalysis],
        user_intent: str = ""
    ) -> List[Dict[str, Any]]:
        """데이터 특성과 사용자 의도에 기반한 시각화 추천"""
        
        recommendations = []
        
        # 1. 단일 필드 시각화
        for field_name, analysis in field_analyses.items():
            single_field_recs = self._recommend_single_field(analysis, user_intent)
            recommendations.extend(single_field_recs)
        
        # 2. 다중 필드 관계 시각화
        multi_field_recs = self._recommend_multi_field(field_analyses, user_intent)
        recommendations.extend(multi_field_recs)
        
        # 3. 우선순위별 정렬
        recommendations.sort(key=lambda x: x.get('priority', 10))
        
        # 4. 중복 제거 및 상위 선택
        unique_recommendations = self._deduplicate_recommendations(recommendations)
        
        return unique_recommendations[:8]  # 상위 8개 추천
    
    def generate_chart_config(
        self, 
        chart_type: str, 
        data_fields: List[str],
        field_analyses: Dict[str, FieldAnalysis],
        title: str = ""
    ) -> Dict[str, Any]:
        """차트 타입과 데이터 필드에 맞는 Chart.js 설정 생성"""
        
        config = {
            "type": chart_type,
            "data": {},
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": title or f"{chart_type.title()} Chart"
                    },
                    "legend": {
                        "display": True,
                        "position": "top"
                    }
                }
            }
        }
        
        # 차트 타입별 특화 설정
        if chart_type == "bar":
            config = self._configure_bar_chart(config, data_fields, field_analyses)
        elif chart_type == "line":
            config = self._configure_line_chart(config, data_fields, field_analyses)
        elif chart_type == "pie":
            config = self._configure_pie_chart(config, data_fields, field_analyses)
        elif chart_type == "scatter":
            config = self._configure_scatter_chart(config, data_fields, field_analyses)
        elif chart_type == "histogram":
            config = self._configure_histogram(config, data_fields, field_analyses)
        elif chart_type == "heatmap":
            config = self._configure_heatmap(config, data_fields, field_analyses)
        
        return config
    
    def _extract_main_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """메인 데이터 배열 추출"""
        
        # 일반적인 키 패턴들
        common_keys = ['data', 'main_data', 'records', 'items', 'results', 'rows']
        
        # 직접 배열인 경우
        if isinstance(data, list):
            return data
        
        # 키별로 배열 탐색
        for key in common_keys:
            if key in data and isinstance(data[key], list):
                return data[key]
        
        # 가장 큰 배열 찾기
        largest_array: List[Dict[str, Any]] = []
        for key, value in data.items():
            if isinstance(value, list) and len(value) > len(largest_array):
                # 배열 요소가 딕셔너리인지 확인
                if value and isinstance(value[0], dict):
                    largest_array = value
        
        return largest_array
    
    def _analyze_field(self, df: pd.DataFrame, column: str) -> FieldAnalysis:
        """개별 필드 상세 분석"""
        
        series = df[column]
        
        # 기본 통계
        unique_values = series.nunique()
        null_percentage = series.isnull().sum() / len(series) * 100
        sample_values = series.dropna().head(5).tolist()
        
        # 데이터 타입 추론
        data_type = self._infer_data_type(series)
        
        # 통계 계산
        statistics = self._calculate_statistics(series, data_type)
        
        # 패턴 탐지
        patterns = self._detect_patterns(series, data_type)
        
        return FieldAnalysis(
            field_name=column,
            data_type=data_type,
            unique_values=unique_values,
            null_percentage=null_percentage,
            sample_values=sample_values,
            statistics=statistics,
            patterns=patterns
        )
    
    def _infer_data_type(self, series: pd.Series) -> DataType:
        """데이터 타입 추론"""
        
        # 결측치 제거
        clean_series = series.dropna()
        if len(clean_series) == 0:
            return DataType.TEXT
        
        # 숫자형 확인
        if pd.api.types.is_numeric_dtype(series):
            # 정수형이고 unique 값이 적으면 discrete
            if pd.api.types.is_integer_dtype(series) and series.nunique() < 20:
                return DataType.NUMERIC_DISCRETE
            else:
                return DataType.NUMERIC_CONTINUOUS
        
        # 날짜/시간 확인
        if self._is_temporal(clean_series):
            return DataType.TEMPORAL
        
        # 불린형 확인
        if self._is_boolean(clean_series):
            return DataType.BOOLEAN
        
        # 지리적 데이터 확인
        if self._is_geographical(clean_series):
            return DataType.GEOGRAPHICAL
        
        # 카테고리형 확인
        unique_ratio = series.nunique() / len(series)
        if unique_ratio < 0.1:  # 10% 미만이면 카테고리
            return DataType.CATEGORICAL_NOMINAL
        elif unique_ratio < 0.5 and self._is_ordinal(clean_series):
            return DataType.CATEGORICAL_ORDINAL
        
        return DataType.TEXT
    
    def _is_temporal(self, series: pd.Series) -> bool:
        """시간 데이터 여부 확인"""
        try:
            # 날짜 패턴 확인
            sample = str(series.iloc[0])
            date_patterns = [
                r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
                r'\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
                r'\d{4}-\d{2}',        # YYYY-MM
            ]
            
            for pattern in date_patterns:
                if re.match(pattern, sample):
                    return True
            
            # pandas 날짜 변환 시도
            pd.to_datetime(series.head(3), errors='raise')
            return True
        except:
            return False
    
    def _is_boolean(self, series: pd.Series) -> bool:
        """불린 데이터 여부 확인"""
        unique_values = set(series.astype(str).str.lower())
        boolean_sets = [
            {'true', 'false'},
            {'yes', 'no'},
            {'y', 'n'},
            {'1', '0'},
            {'on', 'off'}
        ]
        
        return any(unique_values.issubset(bool_set) for bool_set in boolean_sets)
    
    def _is_geographical(self, series: pd.Series) -> bool:
        """지리적 데이터 여부 확인"""
        sample_values = series.astype(str).str.lower().head(10)
        
        # 지역명 패턴
        geo_patterns = [
            r'.*시$', r'.*구$', r'.*도$',  # 한국 지역
            r'.*city$', r'.*state$',       # 영어 지역
            r'\d+\.\d+,\d+\.\d+',         # 좌표
        ]
        
        geo_keywords = [
            '서울', '부산', '대구', '인천', '광주', '대전', '울산',
            'seoul', 'busan', 'daegu', 'incheon', 'gwangju'
        ]
        
        for value in sample_values:
            for pattern in geo_patterns:
                if re.search(pattern, value):
                    return True
            for keyword in geo_keywords:
                if keyword in value:
                    return True
        
        return False
    
    def _is_ordinal(self, series: pd.Series) -> bool:
        """순서형 카테고리 여부 확인"""
        ordinal_patterns = [
            ['low', 'medium', 'high'],
            ['small', 'medium', 'large'],
            ['poor', 'fair', 'good', 'excellent'],
            ['1', '2', '3', '4', '5'],
            ['first', 'second', 'third'],
        ]
        
        unique_values = set(series.astype(str).str.lower())
        
        for pattern in ordinal_patterns:
            if unique_values.issubset(set(pattern)):
                return True
        
        return False
    
    def _calculate_statistics(self, series: pd.Series, data_type: DataType) -> Dict[str, Union[str, int, float, Dict[str, Any]]]:
        """데이터 타입별 통계 계산"""
        
        stats: Dict[str, Union[str, int, float, Dict[str, Any]]] = {}
        
        if data_type in [DataType.NUMERIC_CONTINUOUS, DataType.NUMERIC_DISCRETE]:
            numeric_series = pd.to_numeric(series, errors='coerce')
            stats.update({
                'mean': float(numeric_series.mean()) if not numeric_series.isna().all() else 0,
                'median': float(numeric_series.median()) if not numeric_series.isna().all() else 0,
                'std': float(numeric_series.std()) if not numeric_series.isna().all() else 0,
                'min': float(numeric_series.min()) if not numeric_series.isna().all() else 0,
                'max': float(numeric_series.max()) if not numeric_series.isna().all() else 0,
                'range': float(numeric_series.max() - numeric_series.min()) if not numeric_series.isna().all() else 0
            })
        
        elif data_type in [DataType.CATEGORICAL_NOMINAL, DataType.CATEGORICAL_ORDINAL]:
            value_counts = series.value_counts()
            stats.update({
                'mode': str(value_counts.index[0]) if len(value_counts) > 0 else "",
                'mode_frequency': int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                'category_count': len(value_counts),
                'top_categories': value_counts.head(5).to_dict()
            })
        
        # 공통 통계
        stats.update({
            'count': int(series.count()),
            'unique_count': int(series.nunique()),
            'null_count': int(series.isnull().sum())
        })
        
        return stats
    
    def _detect_patterns(self, series: pd.Series, data_type: DataType) -> List[str]:
        """데이터 패턴 탐지"""
        
        patterns = []
        
        if data_type == DataType.NUMERIC_CONTINUOUS:
            # 분포 패턴
            numeric_series = pd.to_numeric(series, errors='coerce').dropna()
            if len(numeric_series) > 0:
                skewness = numeric_series.skew()
                if skewness > 1:
                    patterns.append("right_skewed")
                elif skewness < -1:
                    patterns.append("left_skewed")
                else:
                    patterns.append("normal_distribution")
                
                # 이상치 탐지
                Q1 = numeric_series.quantile(0.25)
                Q3 = numeric_series.quantile(0.75)
                IQR = Q3 - Q1
                outliers = numeric_series[(numeric_series < Q1 - 1.5*IQR) | (numeric_series > Q3 + 1.5*IQR)]
                if len(outliers) > len(numeric_series) * 0.05:
                    patterns.append("has_outliers")
        
        elif data_type in [DataType.CATEGORICAL_NOMINAL, DataType.CATEGORICAL_ORDINAL]:
            # 카테고리 분포
            value_counts = series.value_counts()
            if len(value_counts) > 0:
                dominant_ratio = value_counts.iloc[0] / len(series)
                if dominant_ratio > 0.7:
                    patterns.append("dominant_category")
                elif dominant_ratio < 0.2:
                    patterns.append("uniform_distribution")
        
        # 시계열 패턴 (temporal 데이터)
        if data_type == DataType.TEMPORAL:
            patterns.append("time_series")
        
        return patterns
    
    def _recommend_single_field(
        self, 
        analysis: FieldAnalysis, 
        user_intent: str
    ) -> List[Dict[str, Any]]:
        """단일 필드 시각화 추천"""
        
        recommendations = []
        
        # 데이터 타입별 기본 추천
        if analysis.data_type == DataType.NUMERIC_CONTINUOUS:
            recommendations.extend([
                {
                    "chart_type": "histogram",
                    "data_fields": [analysis.field_name],
                    "priority": 2,
                    "reasoning": f"{analysis.field_name}의 분포를 보여주는 히스토그램",
                    "config": {"title": f"{analysis.field_name} 분포"}
                },
                {
                    "chart_type": "box",
                    "data_fields": [analysis.field_name],
                    "priority": 3,
                    "reasoning": f"{analysis.field_name}의 이상치와 사분위수를 보여주는 박스플롯",
                    "config": {"title": f"{analysis.field_name} 통계 요약"}
                }
            ])
        
        elif analysis.data_type in [DataType.CATEGORICAL_NOMINAL, DataType.CATEGORICAL_ORDINAL]:
            recommendations.extend([
                {
                    "chart_type": "bar",
                    "data_fields": [analysis.field_name],
                    "priority": 1,
                    "reasoning": f"{analysis.field_name} 카테고리별 빈도를 보여주는 막대차트",
                    "config": {"title": f"{analysis.field_name} 분포"}
                }
            ])
            
            # 카테고리가 적으면 파이차트도 추천
            if analysis.unique_values <= 8:
                recommendations.append({
                    "chart_type": "pie",
                    "data_fields": [analysis.field_name],
                    "priority": 2,
                    "reasoning": f"{analysis.field_name} 비율을 보여주는 파이차트",
                    "config": {"title": f"{analysis.field_name} 구성비"}
                })
        
        elif analysis.data_type == DataType.TEMPORAL:
            recommendations.append({
                "chart_type": "line_chart",
                "data_fields": [analysis.field_name],
                "priority": 1,
                "reasoning": f"{analysis.field_name} 시간에 따른 변화를 보여주는 선형차트",
                "config": {"title": f"{analysis.field_name} 시계열"}
            })
        
        return recommendations
    
    def _recommend_multi_field(
        self, 
        field_analyses: Dict[str, FieldAnalysis],
        user_intent: str
    ) -> List[Dict[str, Any]]:
        """다중 필드 관계 시각화 추천"""
        
        recommendations = []
        fields = list(field_analyses.keys())
        
        # 수치형 필드들
        numeric_fields = [
            name for name, analysis in field_analyses.items()
            if analysis.data_type in [DataType.NUMERIC_CONTINUOUS, DataType.NUMERIC_DISCRETE]
        ]
        
        # 카테고리형 필드들
        categorical_fields = [
            name for name, analysis in field_analyses.items()
            if analysis.data_type in [DataType.CATEGORICAL_NOMINAL, DataType.CATEGORICAL_ORDINAL]
        ]
        
        # 시간 필드들
        temporal_fields = [
            name for name, analysis in field_analyses.items()
            if analysis.data_type == DataType.TEMPORAL
        ]
        
        # 1. 수치형 vs 수치형: 산점도
        if len(numeric_fields) >= 2:
            for i, field1 in enumerate(numeric_fields[:3]):
                for field2 in numeric_fields[i+1:i+3]:
                    recommendations.append({
                        "chart_type": "scatter",
                        "data_fields": [field1, field2],
                        "priority": 3,
                        "reasoning": f"{field1}과 {field2} 간의 상관관계를 보여주는 산점도",
                        "config": {"title": f"{field1} vs {field2}"}
                    })
        
        # 2. 카테고리 vs 수치형: 그룹별 막대차트
        if categorical_fields and numeric_fields:
            for cat_field in categorical_fields[:2]:
                for num_field in numeric_fields[:2]:
                    recommendations.append({
                        "chart_type": "bar",
                        "data_fields": [cat_field, num_field],
                        "priority": 2,
                        "reasoning": f"{cat_field}별 {num_field} 평균을 보여주는 그룹 막대차트",
                        "config": {"title": f"{cat_field}별 {num_field} 분석"}
                    })
        
        # 3. 시간 vs 수치형: 시계열 차트
        if temporal_fields and numeric_fields:
            for time_field in temporal_fields[:1]:
                for num_field in numeric_fields[:2]:
                    recommendations.append({
                        "chart_type": "line_chart",
                        "data_fields": [time_field, num_field],
                        "priority": 1,
                        "reasoning": f"{time_field}에 따른 {num_field} 변화를 보여주는 시계열 차트",
                        "config": {"title": f"{num_field} 추세 분석"}
                    })
        
        # 4. 3개 이상 수치형 필드: 히트맵
        if len(numeric_fields) >= 3:
            recommendations.append({
                "chart_type": "heatmap",
                "data_fields": numeric_fields[:5],
                "priority": 4,
                "reasoning": "수치형 변수들 간의 상관관계를 보여주는 히트맵",
                "config": {"title": "변수 간 상관관계"}
            })
        
        return recommendations
    
    def _deduplicate_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 추천 제거"""
        
        seen = set()
        unique_recs = []
        
        for rec in recommendations:
            # 차트 타입과 필드 조합으로 중복 확인
            key = (rec["chart_type"], tuple(sorted(rec["data_fields"])))
            if key not in seen:
                seen.add(key)
                unique_recs.append(rec)
        
        return unique_recs
    
    def _configure_bar_chart(
        self, 
        config: Dict[str, Any], 
        data_fields: List[str],
        field_analyses: Dict[str, FieldAnalysis]
    ) -> Dict[str, Any]:
        """막대차트 특화 설정"""
        
        config["data"] = {
            "labels": [],  # 동적으로 채워짐
            "datasets": [{
                "label": data_fields[1] if len(data_fields) > 1 else "Value",
                "backgroundColor": [
                    "#667eea", "#764ba2", "#f093fb", "#f5576c", 
                    "#4facfe", "#00f2fe", "#43e97b", "#38f9d7"
                ],
                "borderColor": "#ffffff",
                "borderWidth": 2,
                "data": []  # 동적으로 채워짐
            }]
        }
        
        config["options"]["scales"] = {
            "y": {
                "beginAtZero": True,
                "grid": {"color": "rgba(0,0,0,0.1)"}
            },
            "x": {
                "grid": {"display": False}
            }
        }
        
        return config
    
    def _configure_line_chart(
        self, 
        config: Dict[str, Any], 
        data_fields: List[str],
        field_analyses: Dict[str, FieldAnalysis]
    ) -> Dict[str, Any]:
        """선형차트 특화 설정"""
        
        config["data"] = {
            "labels": [],
            "datasets": [{
                "label": data_fields[1] if len(data_fields) > 1 else "Value",
                "borderColor": "#667eea",
                "backgroundColor": "rgba(102, 126, 234, 0.1)",
                "fill": True,
                "tension": 0.4,
                "pointBackgroundColor": "#667eea",
                "pointBorderColor": "#ffffff",
                "pointBorderWidth": 2,
                "data": []
            }]
        }
        
        config["options"]["scales"] = {
            "y": {
                "beginAtZero": False,
                "grid": {"color": "rgba(0,0,0,0.1)"}
            },
            "x": {
                "grid": {"display": False}
            }
        }
        
        config["options"]["interaction"] = {
            "intersect": False,
            "mode": "index"
        }
        
        return config
    
    def _configure_pie_chart(
        self, 
        config: Dict[str, Any], 
        data_fields: List[str],
        field_analyses: Dict[str, FieldAnalysis]
    ) -> Dict[str, Any]:
        """파이차트 특화 설정"""
        
        config["data"] = {
            "labels": [],
            "datasets": [{
                "backgroundColor": [
                    "#667eea", "#764ba2", "#f093fb", "#f5576c", 
                    "#4facfe", "#00f2fe", "#43e97b", "#38f9d7",
                    "#ff9a9e", "#fecfef", "#ffecd2", "#fcb69f"
                ],
                "borderColor": "#ffffff",
                "borderWidth": 3,
                "data": []
            }]
        }
        
        config["options"]["plugins"]["legend"]["position"] = "right"
        
        return config
    
    def _configure_scatter_chart(
        self, 
        config: Dict[str, Any], 
        data_fields: List[str],
        field_analyses: Dict[str, FieldAnalysis]
    ) -> Dict[str, Any]:
        """산점도 특화 설정"""
        
        config["data"] = {
            "datasets": [{
                "label": f"{data_fields[0]} vs {data_fields[1]}" if len(data_fields) > 1 else "Data Points",
                "backgroundColor": "rgba(102, 126, 234, 0.6)",
                "borderColor": "#667eea",
                "pointRadius": 6,
                "pointHoverRadius": 8,
                "data": []  # {x: value, y: value} 형태
            }]
        }
        
        config["options"]["scales"] = {
            "x": {
                "type": "linear",
                "position": "bottom",
                "title": {
                    "display": True,
                    "text": data_fields[0] if len(data_fields) > 0 else "X-axis"
                }
            },
            "y": {
                "title": {
                    "display": True,
                    "text": data_fields[1] if len(data_fields) > 1 else "Y-axis"
                }
            }
        }
        
        return config
    
    def _configure_histogram(
        self, 
        config: Dict[str, Any], 
        data_fields: List[str],
        field_analyses: Dict[str, FieldAnalysis]
    ) -> Dict[str, Any]:
        """히스토그램 특화 설정"""
        
        config["data"] = {
            "labels": [],  # 구간 라벨
            "datasets": [{
                "label": "Frequency",
                "backgroundColor": "rgba(102, 126, 234, 0.7)",
                "borderColor": "#667eea",
                "borderWidth": 1,
                "data": []
            }]
        }
        
        config["options"]["scales"] = {
            "y": {
                "beginAtZero": True,
                "title": {
                    "display": True,
                    "text": "빈도"
                }
            },
            "x": {
                "title": {
                    "display": True,
                    "text": data_fields[0] if len(data_fields) > 0 else "값"
                }
            }
        }
        
        return config
    
    def _configure_heatmap(
        self, 
        config: Dict[str, Any], 
        data_fields: List[str],
        field_analyses: Dict[str, FieldAnalysis]
    ) -> Dict[str, Any]:
        """히트맵 특화 설정 (Chart.js 매트릭스 차트 사용)"""
        
        config["type"] = "scatter"  # Chart.js에서는 scatter로 히트맵 구현
        config["data"] = {
            "datasets": [{
                "label": "Correlation",
                "backgroundColor": "rgba(102, 126, 234, 0.8)",
                "data": []  # {x: field1, y: field2, v: correlation} 형태
            }]
        }
        
        return config
    
    def _initialize_visualization_rules(self) -> List[VisualizationRule]:
        """시각화 규칙 초기화"""
        
        return [
            # 기본 규칙들은 위의 recommend 메서드에서 구현됨
            # 추가 커스텀 규칙이 필요한 경우 여기에 정의
        ] 