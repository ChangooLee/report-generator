"""
Universal Data Source Adapter System
다양한 데이터 소스를 통합 처리하는 어댑터 시스템
"""

import json
import csv
import io
from typing import Dict, Any, List, Optional, Union, Set
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
import logging
from datetime import datetime
import pandas as pd


class DataSourceType(Enum):
    """지원되는 데이터 소스 타입"""
    JSON = "json"
    MCP_RESPONSE = "mcp_response"
    CSV = "csv"
    API_RESPONSE = "api_response"
    PANDAS_DATAFRAME = "pandas_dataframe"
    EXCEL = "excel"
    DATABASE_RESULT = "database_result"
    STRUCTURED_DATA = "structured_data"


@dataclass
class DataMetadata:
    """데이터 메타데이터"""
    source_type: DataSourceType
    total_records: int
    columns: List[str]
    data_types: Dict[str, str]
    created_at: datetime
    source_info: Dict[str, Any]
    quality_score: float = 0.0


@dataclass
class ProcessedData:
    """처리된 데이터"""
    main_data: List[Dict[str, Any]]
    metadata: DataMetadata
    summary: Dict[str, Any]
    processing_notes: List[str]


class DataSourceAdapter(ABC):
    """데이터 소스 어댑터 추상 클래스"""
    
    @abstractmethod
    def can_handle(self, data: Any) -> bool:
        """해당 어댑터가 이 데이터를 처리할 수 있는지 확인"""
        pass
    
    @abstractmethod
    def extract_data(self, data: Any) -> ProcessedData:
        """데이터 추출 및 변환"""
        pass
    
    @abstractmethod
    def get_source_type(self) -> DataSourceType:
        """소스 타입 반환"""
        pass


class JSONAdapter(DataSourceAdapter):
    """JSON 데이터 어댑터"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def can_handle(self, data: Any) -> bool:
        """JSON 데이터 처리 가능 여부 확인"""
        if isinstance(data, dict):
            return True
        elif isinstance(data, str):
            try:
                json.loads(data)
                return True
            except (json.JSONDecodeError, ValueError):
                return False
        return False
    
    def extract_data(self, data: Any) -> ProcessedData:
        """JSON 데이터 추출"""
        
        # 문자열인 경우 파싱
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                raise ValueError(f"잘못된 JSON 형식: {e}")
        
        # 메인 데이터 추출
        main_data = self._extract_main_array(data)
        
        # 메타데이터 생성
        metadata = self._create_metadata(data, main_data)
        
        # 요약 정보 생성
        summary = self._create_summary(main_data)
        
        # 처리 노트
        processing_notes = [
            f"JSON 데이터 처리 완료",
            f"메인 데이터 경로: {self._find_main_data_path(data)}",
            f"추출된 레코드 수: {len(main_data)}"
        ]
        
        return ProcessedData(
            main_data=main_data,
            metadata=metadata,
            summary=summary,
            processing_notes=processing_notes
        )
    
    def get_source_type(self) -> DataSourceType:
        return DataSourceType.JSON
    
    def _extract_main_array(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """JSON에서 메인 데이터 배열 추출"""
        
        # 직접 배열인 경우
        if isinstance(data, list):
            return data
        
        # 일반적인 키 패턴들
        common_keys = [
            'data', 'items', 'records', 'results', 'rows', 'content',
            'main_data', 'payload', 'response', 'list', 'entries'
        ]
        
        # 키별로 배열 탐색
        for key in common_keys:
            if key in data and isinstance(data[key], list):
                if data[key] and isinstance(data[key][0], dict):
                    return data[key]
        
        # 가장 큰 배열 찾기
        largest_array: List[Dict[str, Any]] = []
        for key, value in data.items():
            if isinstance(value, list) and len(value) > len(largest_array):
                if value and isinstance(value[0], (dict, list)):
                    largest_array = value
        
        # 배열을 찾지 못한 경우 단일 객체를 배열로 변환
        if not largest_array and isinstance(data, dict):
            # 딕셔너리의 값들 중 객체들을 수집
            potential_records = []
            for key, value in data.items():
                if isinstance(value, dict):
                    potential_records.append({**value, '_source_key': key})
            
            if potential_records:
                return potential_records
            else:
                # 마지막 수단: 딕셔너리 자체를 단일 레코드로 처리
                return [data]
        
        return largest_array if isinstance(largest_array[0], dict) else []
    
    def _find_main_data_path(self, data: Dict[str, Any]) -> str:
        """메인 데이터 경로 찾기"""
        
        if isinstance(data, list):
            return "root"
        
        common_keys = [
            'data', 'items', 'records', 'results', 'rows', 'content',
            'main_data', 'payload', 'response', 'list', 'entries'
        ]
        
        for key in common_keys:
            if key in data and isinstance(data[key], list):
                return key
        
        # 가장 큰 배열의 키 찾기
        largest_key = None
        largest_size = 0
        
        for key, value in data.items():
            if isinstance(value, list) and len(value) > largest_size:
                largest_key = key
                largest_size = len(value)
        
        return largest_key or "unknown"
    
    def _create_metadata(self, raw_data: Dict[str, Any], main_data: List[Dict[str, Any]]) -> DataMetadata:
        """메타데이터 생성"""
        
        columns = []
        data_types = {}
        
        if main_data:
            # 모든 키 수집
            all_keys: Set[str] = set()
            for record in main_data[:100]:  # 샘플링
                if isinstance(record, dict):
                    all_keys.update(record.keys())
            
            columns = list(all_keys)
            
            # 데이터 타입 추론
            for column in columns:
                sample_values = [
                    record.get(column) for record in main_data[:50] 
                    if isinstance(record, dict) and column in record and record[column] is not None
                ]
                
                if sample_values:
                    data_types[column] = self._infer_column_type(sample_values)
                else:
                    data_types[column] = "unknown"
        
        # 데이터 품질 점수 계산
        quality_score = self._calculate_quality_score(main_data)
        
        return DataMetadata(
            source_type=self.get_source_type(),
            total_records=len(main_data),
            columns=columns,
            data_types=data_types,
            created_at=datetime.now(),
            source_info={
                "original_keys": list(raw_data.keys()) if isinstance(raw_data, dict) else [],
                "nested_levels": self._count_nested_levels(raw_data),
                "total_size_bytes": len(json.dumps(raw_data, default=str))
            },
            quality_score=quality_score
        )
    
    def _infer_column_type(self, sample_values: List[Any]) -> str:
        """컬럼 타입 추론"""
        
        if not sample_values:
            return "unknown"
        
        # 타입별 카운트
        type_counts: Dict[str, int] = {}
        for value in sample_values:
            if isinstance(value, bool):
                type_counts['boolean'] = type_counts.get('boolean', 0) + 1
            elif isinstance(value, int):
                type_counts['integer'] = type_counts.get('integer', 0) + 1
            elif isinstance(value, float):
                type_counts['float'] = type_counts.get('float', 0) + 1
            elif isinstance(value, str):
                # 날짜 패턴 확인
                if self._is_date_string(value):
                    type_counts['datetime'] = type_counts.get('datetime', 0) + 1
                elif self._is_numeric_string(value):
                    type_counts['numeric_string'] = type_counts.get('numeric_string', 0) + 1
                else:
                    type_counts['string'] = type_counts.get('string', 0) + 1
            elif isinstance(value, (list, dict)):
                type_counts['complex'] = type_counts.get('complex', 0) + 1
            else:
                type_counts['other'] = type_counts.get('other', 0) + 1
        
        # 가장 많은 타입 반환
        if type_counts:
            return max(type_counts, key=lambda k: type_counts[k])
        else:
            return "unknown"
    
    def _is_date_string(self, value: str) -> bool:
        """날짜 문자열 여부 확인"""
        import re
        
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',           # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',           # MM/DD/YYYY
            r'\d{4}/\d{2}/\d{2}',           # YYYY/MM/DD
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO format
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, value):
                return True
        return False
    
    def _is_numeric_string(self, value: str) -> bool:
        """숫자 문자열 여부 확인"""
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    def _count_nested_levels(self, data: Any, current_level: int = 0) -> int:
        """중첩 레벨 계산"""
        max_level = current_level
        
        if isinstance(data, dict):
            for value in data.values():
                level = self._count_nested_levels(value, current_level + 1)
                max_level = max(max_level, level)
        elif isinstance(data, list) and data:
            for item in data[:5]:  # 샘플링
                level = self._count_nested_levels(item, current_level + 1)
                max_level = max(max_level, level)
        
        return max_level
    
    def _calculate_quality_score(self, main_data: List[Dict[str, Any]]) -> float:
        """데이터 품질 점수 계산 (0-1)"""
        
        if not main_data:
            return 0.0
        
        total_score = 0.0
        factors = 0
        
        # 1. 완성도 (결측치 비율)
        if main_data:
            all_fields: Set[str] = set()
            for record in main_data:
                if isinstance(record, dict):
                    all_fields.update(record.keys())
            
            if all_fields:
                completeness_scores = []
                for field in all_fields:
                    non_null_count = sum(
                        1 for record in main_data 
                        if isinstance(record, dict) and field in record and record[field] is not None
                    )
                    completeness_scores.append(non_null_count / len(main_data))
                
                total_score += sum(completeness_scores) / len(completeness_scores)
                factors += 1
        
        # 2. 일관성 (타입 일관성)
        consistency_score = 0.8  # 기본값
        total_score += consistency_score
        factors += 1
        
        # 3. 구조적 무결성
        structural_score = 1.0 if all(isinstance(record, dict) for record in main_data) else 0.5
        total_score += structural_score
        factors += 1
        
        return total_score / factors if factors > 0 else 0.0
    
    def _create_summary(self, main_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """요약 정보 생성"""
        
        if not main_data:
            return {"total_records": 0, "columns": [], "sample": []}
        
        # 컬럼 정보
        all_columns: Set[str] = set()
        for record in main_data:
            if isinstance(record, dict):
                all_columns.update(record.keys())
        
        # 샘플 데이터
        sample_data = main_data[:5]
        
        return {
            "total_records": len(main_data),
            "columns": list(all_columns),
            "column_count": len(all_columns),
            "sample": sample_data,
            "has_nested_objects": any(
                isinstance(value, (dict, list)) 
                for record in main_data[:10] 
                for value in record.values() 
                if isinstance(record, dict)
            )
        }


class MCPResponseAdapter(DataSourceAdapter):
    """MCP 응답 어댑터"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def can_handle(self, data: Any) -> bool:
        """MCP 응답 처리 가능 여부 확인"""
        if isinstance(data, dict):
            # MCP 응답의 일반적인 구조 확인
            mcp_indicators = [
                'result', 'content', 'response', 'data',
                'tool_result', 'mcp_result', 'output'
            ]
            
            return any(key in data for key in mcp_indicators)
        return False
    
    def extract_data(self, data: Dict[str, Any]) -> ProcessedData:
        """MCP 응답 데이터 추출"""
        
        # MCP 응답에서 실제 데이터 추출
        content_data = self._extract_mcp_content(data)
        
        # JSON 어댑터로 위임 (MCP 응답도 결국 JSON 구조)
        json_adapter = JSONAdapter()
        processed = json_adapter.extract_data(content_data)
        
        # 메타데이터 업데이트
        processed.metadata.source_type = self.get_source_type()
        processed.metadata.source_info.update({
            "mcp_tool": data.get("tool", "unknown"),
            "mcp_status": data.get("status", "unknown"),
            "mcp_timestamp": data.get("timestamp"),
            "original_mcp_keys": list(data.keys())
        })
        
        # 처리 노트 추가
        processed.processing_notes.insert(0, "MCP 응답 처리")
        processed.processing_notes.append(f"MCP 도구: {data.get('tool', 'unknown')}")
        
        return processed
    
    def get_source_type(self) -> DataSourceType:
        return DataSourceType.MCP_RESPONSE
    
    def _extract_mcp_content(self, data: Dict[str, Any]) -> Any:
        """MCP 응답에서 실제 컨텐츠 추출"""
        
        # 일반적인 MCP 응답 키들
        content_keys = [
            'result', 'content', 'response', 'data', 'output',
            'tool_result', 'mcp_result', 'payload'
        ]
        
        for key in content_keys:
            if key in data:
                return data[key]
        
        # 키를 찾지 못한 경우 전체 데이터 반환
        return data


class CSVAdapter(DataSourceAdapter):
    """CSV 데이터 어댑터"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def can_handle(self, data: Any) -> bool:
        """CSV 데이터 처리 가능 여부 확인"""
        if isinstance(data, str):
            # CSV 형태의 문자열인지 확인
            lines = data.strip().split('\n')
            if len(lines) >= 2:
                # 첫 번째 줄이 헤더처럼 보이고 컬럼 구분자가 있는지 확인
                first_line = lines[0]
                if ',' in first_line or '\t' in first_line or ';' in first_line:
                    return True
        return False
    
    def extract_data(self, data: str) -> ProcessedData:
        """CSV 데이터 추출"""
        
        # 구분자 감지
        delimiter = self._detect_delimiter(data)
        
        # CSV 파싱
        try:
            csv_reader = csv.DictReader(io.StringIO(data), delimiter=delimiter)
            main_data = [row for row in csv_reader]
        except Exception as e:
            raise ValueError(f"CSV 파싱 오류: {e}")
        
        # 메타데이터 생성
        columns = list(main_data[0].keys()) if main_data else []
        data_types = {}
        
        for column in columns:
            sample_values = [str(row.get(column)) for row in main_data[:50] if row.get(column) is not None]
            data_types[column] = self._infer_csv_column_type(sample_values)
        
        metadata = DataMetadata(
            source_type=self.get_source_type(),
            total_records=len(main_data),
            columns=columns,
            data_types=data_types,
            created_at=datetime.now(),
            source_info={
                "delimiter": delimiter,
                "total_size_bytes": len(data)
            },
            quality_score=0.9  # CSV는 일반적으로 구조가 깔끔함
        )
        
        summary = {
            "total_records": len(main_data),
            "columns": columns,
            "column_count": len(columns),
            "sample": main_data[:5],
            "delimiter": delimiter
        }
        
        processing_notes = [
            "CSV 데이터 처리 완료",
            f"구분자: '{delimiter}'",
            f"컬럼 수: {len(columns)}"
        ]
        
        return ProcessedData(
            main_data=main_data,
            metadata=metadata,
            summary=summary,
            processing_notes=processing_notes
        )
    
    def get_source_type(self) -> DataSourceType:
        return DataSourceType.CSV
    
    def _detect_delimiter(self, data: str) -> str:
        """CSV 구분자 감지"""
        sample = data[:1000]  # 샘플링
        
        delimiters = [',', '\t', ';', '|']
        delimiter_counts = {}
        
        for delimiter in delimiters:
            delimiter_counts[delimiter] = sample.count(delimiter)
        
        # 가장 많이 사용된 구분자 선택
        return max(delimiter_counts, key=lambda k: delimiter_counts[k])
    
    def _infer_csv_column_type(self, sample_values: List[str]) -> str:
        """CSV 컬럼 타입 추론"""
        if not sample_values:
            return "string"
        
        # 숫자 여부 확인
        numeric_count = 0
        for value in sample_values:
            try:
                float(value)
                numeric_count += 1
            except (ValueError, TypeError):
                pass
        
        if numeric_count / len(sample_values) > 0.8:
            return "numeric"
        
        # 날짜 여부 확인
        date_count = 0
        for value in sample_values:
            if self._is_date_string(value):
                date_count += 1
        
        if date_count / len(sample_values) > 0.8:
            return "datetime"
        
        return "string"
    
    def _is_date_string(self, value: str) -> bool:
        """날짜 문자열 여부 확인"""
        import re
        
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{4}/\d{2}/\d{2}',
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, value):
                return True
        return False


class DataSourceManager:
    """데이터 소스 통합 관리자"""
    
    def __init__(self):
        self.adapters = [
            MCPResponseAdapter(),
            JSONAdapter(),
            CSVAdapter(),
        ]
        self.logger = logging.getLogger(__name__)
    
    def process_data(self, data: Any, source_hint: Optional[str] = None) -> ProcessedData:
        """데이터 처리"""
        
        # 힌트가 있는 경우 해당 어댑터 우선 시도
        if source_hint:
            specific_adapter = self._get_adapter_by_hint(source_hint)
            if specific_adapter and specific_adapter.can_handle(data):
                return specific_adapter.extract_data(data)
        
        # 자동 감지
        for adapter in self.adapters:
            if adapter.can_handle(data):
                self.logger.info(f"데이터 처리 어댑터: {adapter.__class__.__name__}")
                return adapter.extract_data(data)
        
        # 처리할 수 있는 어댑터가 없는 경우 기본 처리
        return self._fallback_processing(data)
    
    def _get_adapter_by_hint(self, hint: str) -> Optional[DataSourceAdapter]:
        """힌트로 어댑터 찾기"""
        hint_mapping = {
            "json": JSONAdapter,
            "mcp": MCPResponseAdapter,
            "csv": CSVAdapter,
        }
        
        adapter_class = hint_mapping.get(hint.lower())
        if adapter_class:
            return adapter_class()
        return None
    
    def _fallback_processing(self, data: Any) -> ProcessedData:
        """기본 처리 (어댑터를 찾지 못한 경우)"""
        
        self.logger.warning("적절한 어댑터를 찾지 못함. 기본 처리 수행")
        
        # 기본적으로 JSON 어댑터로 시도
        try:
            json_adapter = JSONAdapter()
            return json_adapter.extract_data(data)
        except Exception as e:
            # 최후의 수단: 빈 데이터 반환
            self.logger.error(f"기본 처리 실패: {e}")
            
            return ProcessedData(
                main_data=[],
                metadata=DataMetadata(
                    source_type=DataSourceType.STRUCTURED_DATA,
                    total_records=0,
                    columns=[],
                    data_types={},
                    created_at=datetime.now(),
                    source_info={"error": str(e)},
                    quality_score=0.0
                ),
                summary={"total_records": 0, "error": "처리 실패"},
                processing_notes=[f"처리 실패: {e}"]
            )
    
    def get_supported_types(self) -> List[str]:
        """지원되는 데이터 타입 목록"""
        return [adapter.get_source_type().value for adapter in self.adapters]
    
    def validate_data_quality(self, processed_data: ProcessedData) -> Dict[str, Any]:
        """데이터 품질 검증"""
        
        quality_report = {
            "overall_score": processed_data.metadata.quality_score,
            "total_records": processed_data.metadata.total_records,
            "completeness": 0.0,
            "consistency": 0.0,
            "issues": [],
            "recommendations": []
        }
        
        # 완성도 검사
        if processed_data.main_data:
            total_fields = len(processed_data.metadata.columns)
            if total_fields > 0:
                completeness_scores = []
                for column in processed_data.metadata.columns:
                    non_null_count = sum(
                        1 for record in processed_data.main_data 
                        if isinstance(record, dict) and column in record and record[column] is not None
                    )
                    completeness_scores.append(non_null_count / len(processed_data.main_data))
                
                if completeness_scores:
                    quality_report["completeness"] = sum(completeness_scores) / len(completeness_scores)

        # 일관성 검사
        quality_report["consistency"] = 0.8  # 기본값
        
        # 이슈 및 권장사항
        completeness = quality_report.get("completeness", 0.0)
        if isinstance(completeness, (int, float)) and completeness < 0.8:
            quality_report["issues"].append("데이터 완성도가 낮음 (80% 미만)")
            quality_report["recommendations"].append("결측치 처리 고려")
        
        if processed_data.metadata.total_records < 10:
            quality_report["issues"].append("데이터 양이 부족함")
            quality_report["recommendations"].append("더 많은 데이터 수집 권장")
        
        return quality_report 