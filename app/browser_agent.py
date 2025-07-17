"""
Browser Testing Agent
브라우저에서 HTML 검증 및 테스트하는 에이전트
"""

import asyncio
import json
import tempfile
import os
import subprocess
import time
from typing import Dict, Any, List, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BrowserTestResult:
    """브라우저 테스트 결과"""
    success: bool
    html_loads: bool
    javascript_errors: List[str]
    chart_elements_found: int
    chart_errors: List[str]
    data_populated: bool
    console_logs: List[str]
    suggestions: List[str]
    screenshot_path: Optional[str] = None


class BrowserAgent:
    """브라우저에서 HTML 테스트하는 에이전트"""
    
    def __init__(self):
        self.has_playwright = self._check_playwright()
    
    def _check_playwright(self) -> bool:
        """Playwright 설치 여부 확인"""
        try:
            import playwright
            return True
        except ImportError:
            logger.warning("Playwright가 설치되지 않음. 기본 검증만 수행")
            return False
    
    async def test_html_in_browser(self, html_content: str) -> BrowserTestResult:
        """브라우저에서 HTML 테스트"""
        
        if not self.has_playwright:
            return await self._basic_html_validation(html_content)
        
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                # 브라우저 실행 (headless)
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 콘솔 로그 및 오류 수집
                console_logs = []
                javascript_errors = []
                
                page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
                page.on("pageerror", lambda err: javascript_errors.append(str(err)))
                
                # 임시 HTML 파일 생성
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    f.write(html_content)
                    temp_path = f.name
                
                try:
                    # HTML 로드
                    await page.goto(f"file://{temp_path}")
                    
                    # 페이지 로딩 대기
                    await page.wait_for_timeout(3000)
                    
                    # Chart.js 로딩 확인
                    chart_loaded = await page.evaluate("typeof Chart !== 'undefined'")
                    
                    # 차트 요소 확인
                    chart_elements = await page.query_selector_all("canvas")
                    chart_count = len(chart_elements)
                    
                    # 차트 렌더링 확인
                    chart_errors = []
                    chart_rendered_count = 0
                    
                    for i, canvas in enumerate(chart_elements):
                        try:
                            # 캔버스가 그려졌는지 확인
                            canvas_data = await canvas.evaluate("el => el.toDataURL()")
                            if canvas_data and len(canvas_data) > 100:  # 기본 빈 캔버스보다 크면 렌더링됨
                                chart_rendered_count += 1
                        except Exception as e:
                            chart_errors.append(f"차트 {i+1} 렌더링 오류: {str(e)}")
                    
                    # 데이터 확인
                    data_elements = await page.query_selector_all(".stat-number, .stat-change")
                    data_populated = len(data_elements) > 0
                    
                    # 수치 데이터 확인
                    stat_numbers = await page.evaluate("""
                        Array.from(document.querySelectorAll('.stat-number')).map(el => el.textContent.trim())
                    """)
                    
                    has_data = any(
                        num and num != "0" and num != "N/A" and not num.startswith("예시")
                        for num in stat_numbers
                    )
                    
                    # 스크린샷 촬영
                    screenshot_path = temp_path.replace('.html', '_screenshot.png')
                    await page.screenshot(path=screenshot_path, full_page=True)
                    
                    # 검증 결과 생성
                    suggestions = []
                    
                    if not chart_loaded:
                        suggestions.append("Chart.js 라이브러리가 로드되지 않았습니다")
                    
                    if chart_count == 0:
                        suggestions.append("차트 요소(canvas)가 없습니다")
                    
                    if chart_rendered_count < chart_count:
                        suggestions.append(f"차트 {chart_count}개 중 {chart_rendered_count}개만 렌더링됨")
                    
                    if not has_data:
                        suggestions.append("데이터 대신 예시/기본값이 표시되고 있습니다")
                    
                    if javascript_errors:
                        suggestions.append("JavaScript 오류가 발생했습니다")
                    
                    success = (
                        chart_loaded and 
                        chart_count > 0 and 
                        chart_rendered_count == chart_count and 
                        has_data and 
                        len(javascript_errors) == 0
                    )
                    
                    return BrowserTestResult(
                        success=success,
                        html_loads=True,
                        javascript_errors=javascript_errors,
                        chart_elements_found=chart_count,
                        chart_errors=chart_errors,
                        data_populated=has_data,
                        console_logs=console_logs[-10:],  # 최근 10개만
                        suggestions=suggestions,
                        screenshot_path=screenshot_path
                    )
                
                finally:
                    await browser.close()
                    # 임시 파일 정리
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"브라우저 테스트 실패: {e}")
            return BrowserTestResult(
                success=False,
                html_loads=False,
                javascript_errors=[str(e)],
                chart_elements_found=0,
                chart_errors=[],
                data_populated=False,
                console_logs=[],
                suggestions=["브라우저 테스트 실행 실패"]
            )
    
    async def _basic_html_validation(self, html_content: str) -> BrowserTestResult:
        """기본적인 HTML 검증 (Playwright 없을 때)"""
        
        suggestions = []
        javascript_errors = []
        
        # 기본 구조 확인
        if not html_content.startswith('<!DOCTYPE'):
            suggestions.append("DOCTYPE 선언이 없습니다")
        
        # Chart.js 확인
        if 'chart.js' not in html_content.lower():
            suggestions.append("Chart.js 라이브러리가 포함되지 않았습니다")
        
        # 차트 요소 확인
        chart_count = html_content.count('<canvas')
        if chart_count == 0:
            suggestions.append("차트 요소(canvas)가 없습니다")
        
        # JavaScript 오류 가능성 확인
        if 'new Chart(' in html_content and 'chart.js' not in html_content.lower():
            javascript_errors.append("Chart.js 없이 new Chart() 사용")
        
        # 예시 데이터 확인
        if '예시' in html_content or '가정' in html_content:
            suggestions.append("예시 데이터가 포함되어 있습니다")
        
        success = len(suggestions) == 0 and len(javascript_errors) == 0
        
        return BrowserTestResult(
            success=success,
            html_loads=True,
            javascript_errors=javascript_errors,
            chart_elements_found=chart_count,
            chart_errors=[],
            data_populated=True,  # 기본 검증에서는 확인 불가
            console_logs=[],
            suggestions=suggestions
        )
    
    def generate_fix_instructions(self, test_result: BrowserTestResult, html_content: str) -> str:
        """테스트 결과를 바탕으로 수정 지시사항 생성"""
        
        if test_result.success:
            return "HTML이 완벽하게 작동합니다! 수정 불필요."
        
        fix_instructions = """
다음 문제들을 수정해주세요:

## 발견된 문제점:
"""

        if test_result.javascript_errors:
            fix_instructions += f"""
### JavaScript 오류:
{chr(10).join(f"- {error}" for error in test_result.javascript_errors)}

**수정방법:** 
- Chart.js CDN이 제대로 로드되었는지 확인
- 변수명과 함수 호출이 정확한지 확인
- HTML 문법 오류 제거
"""

        if test_result.chart_elements_found == 0:
            fix_instructions += """
### 차트 요소 없음:
- <canvas> 태그가 없습니다

**수정방법:**
- 각 차트마다 고유한 ID를 가진 <canvas> 태그 추가
- 예: <canvas id="myChart"></canvas>
"""

        if test_result.chart_errors:
            fix_instructions += f"""
### 차트 렌더링 오류:
{chr(10).join(f"- {error}" for error in test_result.chart_errors)}

**수정방법:**
- 차트 데이터 형식 확인
- Chart.js 문법 확인
- DOM 요소가 존재하는지 확인
"""

        if not test_result.data_populated:
            fix_instructions += """
### 데이터 부족:
- 예시 데이터나 빈 값이 표시되고 있습니다

**수정방법:**
- MCP 데이터를 HTML에 정확히 삽입
- 숫자 포맷팅 확인
- 데이터 바인딩 확인
"""

        if test_result.suggestions:
            fix_instructions += f"""
### 개선 제안:
{chr(10).join(f"- {suggestion}" for suggestion in test_result.suggestions)}
"""

        fix_instructions += """
## 수정된 HTML 작성 요구사항:
1. 모든 JavaScript 오류 제거
2. Chart.js CDN 정확히 포함
3. MCP 데이터 사용 (예시 데이터 금지)
4. 차트가 정상 렌더링되도록 수정
5. 브라우저에서 완벽히 작동하는 HTML 생성

완전히 새로운 HTML을 생성해주세요.
"""

        return fix_instructions


async def install_playwright_if_needed():
    """필요시 Playwright 설치"""
    try:
        import playwright
        logger.info("✅ Playwright 이미 설치됨")
        return True
    except ImportError:
        logger.info("📦 Playwright 설치 중...")
        try:
            subprocess.run(["pip", "install", "playwright"], check=True)
            subprocess.run(["playwright", "install", "chromium"], check=True)
            logger.info("✅ Playwright 설치 완료")
            return True
        except Exception as e:
            logger.error(f"❌ Playwright 설치 실패: {e}")
            return False 