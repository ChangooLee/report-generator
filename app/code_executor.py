import tempfile
import os
import json
import asyncio
import logging
import uuid
import subprocess
from typing import Dict, Any, Optional
from .utils.security import SecurityValidator

logger = logging.getLogger(__name__)

class CodeExecutor:
    """안전한 코드 실행 환경을 제공하는 클래스"""
    
    def __init__(self):
        self.security_validator = SecurityValidator()
        # 현재 작업 디렉토리 기준으로 reports 경로 설정
        self.reports_path = os.getenv('REPORTS_PATH', os.path.join(os.getcwd(), 'reports'))
        self.max_execution_time = int(os.getenv('MAX_EXECUTION_TIME', '300'))
        
        # 리포트 디렉토리 생성
        os.makedirs(self.reports_path, exist_ok=True)
        
    async def execute_code(
        self, 
        code: Dict[str, Any], 
        session_id: str, 
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """격리된 환경에서 코드를 실행합니다."""
        
        try:
            # Python 코드가 있는지 확인
            python_code = code.get('python_code')
            if not python_code:
                return {
                    "success": False,
                    "error": "실행할 Python 코드가 없습니다.",
                    "output": ""
                }
            
            # 보안 검증
            security_result = self.security_validator.validate_code(python_code)
            if not security_result["is_safe"]:
                return {
                    "success": False,
                    "error": f"보안 검증에 실패했습니다: {', '.join(security_result['errors'])}",
                    "output": ""
                }
            
            # 컨텍스트 데이터 파일 생성
            context_file = f"/tmp/context_{session_id}.json"
            logger.info(f"컨텍스트 데이터 저장 시작: {context_file}")
            logger.info(f"컨텍스트 데이터 타입: {type(context_data)}, 키 개수: {len(context_data) if isinstance(context_data, dict) else 'N/A'}")
            
            try:
                logger.info(f"JSON 덤프 시작, 데이터 타입: {type(context_data)}")
                logger.info(f"JSON 덤프할 데이터 키: {list(context_data.keys()) if isinstance(context_data, dict) else 'N/A'}")
                
                with open(context_file, 'w', encoding='utf-8') as f:
                    json.dump(context_data, f, ensure_ascii=False, indent=2)
                logger.info(f"컨텍스트 데이터 저장 완료: {os.path.getsize(context_file)} bytes")
            except (TypeError, ValueError) as e:
                logger.error(f"JSON 직렬화 오류: {e}")
                logger.error(f"문제가 된 데이터: {context_data}")
                raise
            except Exception as e:
                logger.error(f"컨텍스트 데이터 저장 실패: {e}")
                logger.error(f"에러 타입: {type(e).__name__}")
                import traceback
                logger.error(f"스택 트레이스: {traceback.format_exc()}")
                raise
            
            # 실행 스크립트 생성
            script_content = self._create_simple_script(
                python_code, 
                session_id, 
                context_file
            )
            
            # 임시 스크립트 파일 생성
            script_file = f"/tmp/script_{session_id}.py"
            logger.info(f"실행 스크립트 저장: {script_file}")
            
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(script_content)
                
            logger.info(f"실행 스크립트 크기: {os.path.getsize(script_file)} bytes")
            logger.info(f"생성된 Python 코드 미리보기:\n{python_code[:300]}...")
            logger.info(f"생성된 스크립트 미리보기:\n{script_content[:500]}...")
            
            # 스크립트 실행
            process = await asyncio.create_subprocess_exec(
                'python', script_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.reports_path
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.max_execution_time
                )
                
                # 결과 처리
                output = stdout.decode('utf-8')
                error_output = stderr.decode('utf-8')
                
                if process.returncode == 0:
                    # 성공 - 생성된 파일 확인
                    report_filename = f"report_{session_id}.html"
                    
                    # 여러 경로에서 파일 찾기
                    possible_paths = [
                        os.path.join(self.reports_path, report_filename),  # /app/reports/
                        os.path.join("/reports", report_filename),  # /reports/
                        report_filename  # 현재 디렉토리
                    ]
                    
                    report_path = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            report_path = path
                            break
                    
                    if report_path:
                        # 파일을 올바른 위치로 이동 (필요한 경우)
                        final_path = os.path.join(self.reports_path, report_filename)
                        if report_path != final_path:
                            import shutil
                            shutil.move(report_path, final_path)
                            report_path = final_path
                        
                        return {
                            "success": True,
                            "output": output,
                            "report_filename": report_filename,
                            "report_path": report_path
                        }
                    else:
                        # 디버깅 정보 추가
                        debug_info = []
                        for path in possible_paths:
                            debug_info.append(f"  - {path}: {'존재' if os.path.exists(path) else '없음'}")
                        
                        return {
                            "success": False,
                            "error": f"리포트 파일이 생성되지 않았습니다.\n확인한 경로들:\n" + "\n".join(debug_info),
                            "output": output,
                            "stderr": error_output
                        }
                else:
                    return {
                        "success": False,
                        "error": f"코드 실행 실패 (종료 코드: {process.returncode})",
                        "output": output,
                        "stderr": error_output
                    }
                    
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "success": False,
                    "error": f"코드 실행 시간 초과 ({self.max_execution_time}초)",
                    "output": ""
                }
            finally:
                # 디버깅을 위해 임시 파일 보존
                logger.info(f"디버깅용 파일 보존:")
                logger.info(f"  - 스크립트: {script_file}")
                logger.info(f"  - 컨텍스트: {context_file}")
                # 임시 파일 정리 (디버깅 시 주석 처리)
                # try:
                #     os.remove(script_file)
                #     os.remove(context_file)
                # except:
                #     pass
                    
        except Exception as e:
            logger.error(f"코드 실행 중 오류 발생: {e}")
            logger.error(f"오류 타입: {type(e).__name__}")
            logger.error(f"오류 문자열 표현: {repr(e)}")
            import traceback
            logger.error(f"전체 스택 트레이스:\n{traceback.format_exc()}")
            return {
                "success": False,
                "error": f"코드 실행 중 오류: {str(e)}",
                "output": ""
            }
    
    def _create_simple_script(
        self, 
        python_code: str, 
        session_id: str,
        context_file: str
    ) -> str:
        """간단한 실행 스크립트를 생성합니다."""
        
        script = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import traceback

# 세션 정보
SESSION_ID = "{session_id}"
REPORT_FILENAME = f"report_{{SESSION_ID}}.html"

print(f"🔍 디버그 정보:")
print(f"  - 세션 ID: {{SESSION_ID}}")
print(f"  - 컨텍스트 파일: {context_file}")
print(f"  - 현재 디렉토리: {{os.getcwd()}}")

# 컨텍스트 데이터 로드
try:
    print(f"📂 컨텍스트 파일 존재 여부: {{os.path.exists('{context_file}')}}")
    with open("{context_file}", "r", encoding="utf-8") as f:
        context_data = json.load(f)
    print(f"✅ 컨텍스트 데이터 로드 성공: {{len(context_data)}}개 키")
    print(f"  - 데이터 키: {{list(context_data.keys())}}")
except Exception as e:
    print(f"⚠️ 컨텍스트 데이터 로드 실패: {{e}}")
    print(f"  - 에러 타입: {{type(e).__name__}}")
    traceback.print_exc()
    context_data = {{}}

print(f"🚀 사용자 코드 실행 시작")
print("=" * 50)

try:
{self._indent_code(python_code)}
    print("=" * 50)
    print(f"✅ 사용자 코드 실행 완료")
    
    # 리포트 파일 생성 확인
    if os.path.exists(REPORT_FILENAME):
        print(f"📄 리포트 파일 생성 확인: {{REPORT_FILENAME}}")
        print(f"  - 파일 크기: {{os.path.getsize(REPORT_FILENAME)}} bytes")
    else:
        print(f"⚠️ 리포트 파일이 생성되지 않음: {{REPORT_FILENAME}}")
        
except Exception as e:
    print("=" * 50)
    print(f"❌ 사용자 코드 실행 오류: {{e}}")
    print(f"  - 에러 타입: {{type(e).__name__}}")
    print(f"  - 에러 상세:")
    traceback.print_exc()
    sys.exit(1)
'''
        return script
    
    def _indent_code(self, code: str, indent_level: int = 4) -> str:
        """코드를 지정된 레벨로 들여쓰기합니다."""
        lines = code.split('\n')
        indented_lines = []
        
        for line in lines:
            if line.strip():  # 빈 줄이 아닌 경우만 들여쓰기
                indented_lines.append(' ' * indent_level + line)
            else:
                indented_lines.append('')  # 빈 줄은 그대로
                
        return '\n'.join(indented_lines)
    
    def get_report_path(self, session_id: str) -> str:
        """리포트 파일 경로를 반환합니다."""
        return os.path.join(self.reports_path, f"report_{session_id}.html")
    
    def cleanup_old_reports(self, max_age_hours: int = 24):
        """오래된 리포트 파일을 정리합니다."""
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for filename in os.listdir(self.reports_path):
                if filename.startswith('report_') and filename.endswith('.html'):
                    file_path = os.path.join(self.reports_path, filename)
                    file_age = current_time - os.path.getmtime(file_path)
                    
                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        logger.info(f"오래된 리포트 파일 삭제: {filename}")
                        
        except Exception as e:
            logger.error(f"리포트 파일 정리 실패: {e}")
    
    def validate_report_file(self, session_id: str) -> Dict[str, Any]:
        """생성된 리포트 파일을 검증합니다."""
        report_path = self.get_report_path(session_id)
        
        if not os.path.exists(report_path):
            return {
                "valid": False,
                "error": "리포트 파일이 존재하지 않습니다."
            }
        
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # HTML 구조 검증
            if not content.strip():
                return {
                    "valid": False,
                    "error": "리포트 파일이 비어있습니다."
                }
            
            if '<html' not in content.lower():
                return {
                    "valid": False,
                    "error": "유효한 HTML 구조가 아닙니다."
                }
            
            # 보안 검증
            security_result = self.security_validator.validate_html_content(content)
            
            return {
                "valid": security_result["is_safe"],
                "warnings": security_result.get("warnings", []),
                "errors": security_result.get("errors", []),
                "file_size": len(content),
                "content_preview": content[:200] + "..." if len(content) > 200 else content
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"파일 검증 실패: {str(e)}"
            } 