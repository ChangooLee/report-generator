import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TestCodeExecutor:
    """간단한 테스트용 코드 실행기"""
    
    def __init__(self):
        self.reports_path = os.getenv('REPORTS_PATH', os.path.join(os.getcwd(), 'reports'))
        os.makedirs(self.reports_path, exist_ok=True)
        
    async def execute_code(
        self, 
        code: Dict[str, Any], 
        session_id: str, 
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """간단한 HTML 리포트를 생성합니다."""
        
        logger.info(f"테스트 실행기 시작 - 세션: {session_id}")
        logger.info(f"받은 코드 타입: {type(code)}, 키: {list(code.keys()) if isinstance(code, dict) else 'N/A'}")
        logger.info(f"컨텍스트 데이터 타입: {type(context_data)}, 키 개수: {len(context_data) if isinstance(context_data, dict) else 'N/A'}")
        
        try:
            # 간단한 HTML 리포트 생성
            html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>테스트 리포트</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .content {{ margin: 20px 0; }}
        .info {{ background: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; }}
    </style>
</head>
<body>
    <h1 class="header">테스트 리포트</h1>
    <div class="content">
        <div class="info">
            <h3>세션 정보</h3>
            <p><strong>세션 ID:</strong> {session_id}</p>
            <p><strong>생성 시간:</strong> {self._get_current_time()}</p>
            <p><strong>코드 정보:</strong></p>
            <ul>
                <li>Python 코드 존재: {code.get('python_code') is not None}</li>
                <li>HTML 코드 존재: {code.get('html_code') is not None}</li>
                <li>JavaScript 코드 존재: {code.get('javascript_code') is not None}</li>
            </ul>
            <p><strong>컨텍스트 데이터 키:</strong> {list(context_data.keys()) if isinstance(context_data, dict) else 'N/A'}</p>
        </div>
        
        <h3>전달받은 Python 코드</h3>
        <pre style="background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto;">
{code.get('python_code', '코드가 없습니다.')[:500]}...
        </pre>
        
        <h3>성공적으로 처리됨</h3>
        <p>이것은 테스트용 리포트입니다. 실제 코드 실행 없이 HTML 파일을 생성했습니다.</p>
    </div>
</body>
</html>
"""
            
            # 리포트 파일 저장
            report_filename = f"report_{session_id}.html"
            report_path = os.path.join(self.reports_path, report_filename)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"테스트 리포트 생성 완료: {report_path}")
            
            return {
                "success": True,
                "output": "테스트 리포트가 성공적으로 생성되었습니다.",
                "report_filename": report_filename,
                "report_path": report_path
            }
            
        except Exception as e:
            logger.error(f"테스트 실행기 오류: {e}")
            return {
                "success": False,
                "error": f"테스트 실행기 오류: {str(e)}",
                "output": ""
            }
    
    def _get_current_time(self) -> str:
        """현재 시간을 문자열로 반환합니다."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S") 