"""
리포트 관련 유틸리티 함수들
"""
import os
import glob
import re
from typing import List, Optional


def extract_timestamp_from_filename(filepath: str) -> int:
    """파일명에서 타임스탬프를 추출합니다."""
    filename = os.path.basename(filepath)
    # report_1753164168.html에서 1753164168 추출
    match = re.search(r'report_(\d+)\.html', filename)
    return int(match.group(1)) if match else 0


def get_latest_report(reports_dir: str = './reports') -> Optional[str]:
    """가장 최신의 리포트 파일을 반환합니다."""
    report_files = glob.glob(os.path.join(reports_dir, "report_*.html"))
    
    if not report_files:
        return None
    
    # 파일명의 타임스탬프 기준으로 최신 파일 찾기
    latest_report = max(report_files, key=extract_timestamp_from_filename)
    return latest_report


def get_all_reports(reports_dir: str = './reports') -> List[str]:
    """모든 리포트 파일을 타임스탬프 순으로 정렬하여 반환합니다."""
    report_files = glob.glob(os.path.join(reports_dir, "report_*.html"))
    
    # 타임스탬프 기준으로 정렬 (최신순)
    return sorted(report_files, key=extract_timestamp_from_filename, reverse=True)


def is_valid_report_file(filepath: str) -> bool:
    """유효한 리포트 파일인지 확인합니다."""
    if not os.path.exists(filepath):
        return False
    
    if not filepath.endswith('.html'):
        return False
    
    # 최소 크기 체크 (1KB 이상)
    if os.path.getsize(filepath) < 1024:
        return False
    
    return True 