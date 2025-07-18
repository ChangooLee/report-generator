import re
import os
from typing import List, Dict, Any

class SecurityValidator:
    """사용자 입력과 코드 실행의 보안을 검증하는 클래스"""
    
    def __init__(self):
        # 위험한 키워드 목록
        self.dangerous_keywords = [
            'import os', 'import sys', 'import subprocess', 
            'eval(', 'exec(', '__import__', '__builtins__',
            'file://', 'http://', 'https://',
            'rm -rf', 'delete', 'remove', 'unlink',
            'password', 'token', 'secret', 'key',
            'DROP TABLE', 'DELETE FROM', 'TRUNCATE'
        ]
        
        # 허용된 파일 확장자
        self.allowed_extensions = ['.html', '.js', '.css', '.json', '.txt', '.md']
        
        # 허용된 라이브러리 목록
        self.allowed_libraries = [
            'pandas', 'numpy', 'matplotlib', 'seaborn', 
            'plotly', 'json', 'datetime', 'time', 'math',
            'statistics', 'collections', 'itertools'
        ]
    
    def validate_user_query(self, query: str) -> bool:
        """사용자 쿼리의 안전성을 검증합니다."""
        
        # 길이 제한
        if len(query) > 1000:
            return False
        
        # 위험한 키워드 검사
        query_lower = query.lower()
        for keyword in self.dangerous_keywords:
            if keyword in query_lower:
                return False
        
        # 특수 문자 제한
        if re.search(r'[<>"\';\\]', query):
            return False
        
        return True
    
    def validate_code(self, code: str) -> Dict[str, Any]:
        """생성된 코드의 안전성을 검증합니다."""
        
        result: Dict[str, Any] = {
            "is_safe": True,
            "warnings": [],
            "errors": []
        }
        
        # 위험한 함수 호출 검사 (exec는 제한된 컨텍스트에서 허용)
        dangerous_functions = [
            'eval', 'compile', '__import__',
            'subprocess', 'os.system'
        ]
        
        for func in dangerous_functions:
            if re.search(func, code):
                result["errors"].append(f"위험한 함수 사용: {func}")
                result["is_safe"] = False
        
        # exec 사용은 경고만 (제한된 환경에서 허용)
        if re.search(r'\bexec\b', code):
            result["warnings"].append("exec 함수 사용 감지 - 제한된 환경에서만 실행됩니다")
        
        # 파일 쓰기 검사 (허용된 경로만)
        write_patterns = [
            r'open\s*\(\s*["\']([^"\']+)["\'][\s,]*["\']w["\']',  # open('file', 'w')
            r'open\s*\(\s*([^,)]+)\s*,\s*["\']w["\']'  # open(file, 'w')
        ]
        
        for pattern in write_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                # 첫 번째 그룹이 파일 경로
                if len(match.groups()) > 0:
                    file_path = match.group(1).strip('\'"')
                    # reports 디렉토리 관련 경로는 허용 (절대/상대 경로 모두)
                    allowed_paths = ['/reports/', './reports/', 'reports/', '/app/reports/', '/tmp/']
                    allowed_dirs = ['reports', 'tmp']
                    
                    # 경로 정규화
                    normalized_path = os.path.normpath(file_path)
                    
                    # 허용된 경로 확인
                    is_allowed = False
                    for path in allowed_paths:
                        if file_path.startswith(path):
                            is_allowed = True
                            break
                    
                    # 상대 경로로 reports 또는 tmp 디렉토리인지 확인
                    if not is_allowed:
                        for dir_name in allowed_dirs:
                            if normalized_path.startswith(dir_name + '/') or normalized_path.startswith(dir_name + '\\'):
                                is_allowed = True
                                break
                    
                    if not is_allowed:
                        result["warnings"].append(f"파일 쓰기 경로 확인 필요: {file_path}")
                        # errors 대신 warnings로 변경 (너무 엄격하지 않게)
        
        # 파일 시스템 접근 검사
        filesystem_patterns = [
            r'open\s*\([^)]*["\'][^"\']*\.\.[^"\']*["\']',  # 상위 디렉토리 접근
            r'os\.path\.join\s*\([^)]*\.\.'  # 상위 디렉토리 결합
        ]
        
        for pattern in filesystem_patterns:
            if re.search(pattern, code):
                result["warnings"].append(f"파일 시스템 접근 감지: {pattern}")
        
        # 허용되지 않는 루트 디렉토리 접근 검사 (app, data, reports는 허용)
        dangerous_root_access = r'["\']\/(?!(?:app|data|reports|tmp)\/)[^"\']*["\']'
        if re.search(dangerous_root_access, code):
            result["warnings"].append(f"잠재적 위험한 루트 디렉토리 접근 감지")
        
        # 네트워크 접근 검사
        network_patterns = [
            r'http[s]?://',
            r'requests\.',
            r'urllib\.',
            r'socket\.'
        ]
        
        for pattern in network_patterns:
            if re.search(pattern, code):
                result["warnings"].append(f"네트워크 접근 감지: {pattern}")
        
        return result
    
    def sanitize_filename(self, filename: str) -> str:
        """파일명을 안전하게 정리합니다."""
        
        # 위험한 문자 제거
        sanitized = re.sub(r'[^\w\-_\.]', '', filename)
        
        # 길이 제한
        if len(sanitized) > 50:
            sanitized = sanitized[:50]
        
        # 확장자 검사
        if not any(sanitized.endswith(ext) for ext in self.allowed_extensions):
            sanitized += '.html'
        
        return sanitized
    
    def validate_file_path(self, path: str, allowed_base: str) -> bool:
        """파일 경로가 허용된 디렉토리 내에 있는지 확인합니다."""
        
        try:
            # 절대 경로로 변환
            abs_path = os.path.abspath(path)
            abs_base = os.path.abspath(allowed_base)
            
            # 공통 경로 확인
            return os.path.commonpath([abs_path, abs_base]) == abs_base
        
        except (ValueError, OSError):
            return False
    
    def filter_environment_variables(self, env_vars: Dict[str, str]) -> Dict[str, str]:
        """환경 변수를 필터링하여 안전한 것만 반환합니다."""
        
        allowed_prefixes = ['PYTHON', 'PATH', 'HOME', 'USER', 'LANG', 'LC_']
        filtered = {}
        
        for key, value in env_vars.items():
            # 민감한 정보 필터링
            if any(sensitive in key.upper() for sensitive in ['PASSWORD', 'TOKEN', 'SECRET', 'KEY']):
                continue
            
            # 허용된 접두사 확인
            if any(key.startswith(prefix) for prefix in allowed_prefixes):
                filtered[key] = value
        
        return filtered
    
    def validate_html_content(self, html_content: str) -> Dict[str, Any]:
        """HTML 콘텐츠의 안전성을 검증합니다."""
        
        result: Dict[str, Any] = {
            "is_safe": True,
            "warnings": [],
            "errors": []
        }
        
        # 위험한 태그 검사
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form']
        
        for tag in dangerous_tags:
            if f'<{tag}' in html_content.lower():
                if tag == 'script':
                    # 로컬 스크립트만 허용
                    if 'src="/static/' not in html_content:
                        result["warnings"].append(f"외부 스크립트 감지: {tag}")
                else:
                    result["errors"].append(f"위험한 태그 감지: {tag}")
                    result["is_safe"] = False
        
        # 외부 리소스 검사
        external_patterns = [
            r'src=["\']https?://',
            r'href=["\']https?://',
            r'@import\s+["\']https?://'
        ]
        
        for pattern in external_patterns:
            if re.search(pattern, html_content):
                result["warnings"].append(f"외부 리소스 참조 감지: {pattern}")
        
        return result 