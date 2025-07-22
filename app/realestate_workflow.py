"""
부동산 MCP 전용 워크플로우
/Users/lchangoo/Workspace/mcp-kr-realestate 기반 최적화
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import BaseTool

from app.llm_client import OpenRouterClient, ModelType
from app.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class RealestateWorkflow:
    """부동산 MCP 전용 워크플로우"""
    
    def __init__(self):
        self.llm_client = OpenRouterClient()
        self.mcp_client = MCPClient()
        self.tools = []
        
    async def initialize(self) -> bool:
        """부동산 MCP 도구 초기화"""
        try:
            logger.info("🏠 부동산 MCP 워크플로우 초기화 시작")
            
            # MCP 서버 시작
            await self.mcp_client.start_mcp_server('kr-realestate')
            tools_info = await self.mcp_client.list_tools('kr-realestate')
            
            logger.info(f"🏠 부동산 도구 {len(tools_info)}개 발견")
            self.tools = tools_info
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 부동산 워크플로우 초기화 실패: {e}")
            return False
    
    async def process_query(
        self, 
        user_query: str, 
        streaming_callback = None
    ) -> Dict[str, Any]:
        """부동산 쿼리 처리"""
        
        try:
            if streaming_callback:
                await streaming_callback.send_status("🏠 부동산 데이터 분석을 시작합니다...")  # type: ignore
                
                # 전략 수립 과정 표시
                strategy_info = {
                    "단계1": "지역 정보 파악 및 매핑",
                    "단계2": "분석 유형 결정 (아파트/오피스텔/기타)",
                    "단계3": "MCP 도구를 통한 실제 데이터 수집",
                    "단계4": "수집된 데이터 종합 분석",
                    "단계5": "LLM 기반 HTML 리포트 생성"
                }
                await streaming_callback.send_content(f"🎯 분석 전략 수립:\n```json\n{json.dumps(strategy_info, ensure_ascii=False, indent=2)}\n```")  # type: ignore
            
            # 1단계: 지역 파악
            if streaming_callback:
                await streaming_callback.send_status("1️⃣ 단계 1: 지역 정보 분석 중...")  # type: ignore
            region_info = await self._extract_region_info(user_query, streaming_callback)
            
            # 2단계: 분석 유형 파악 (아파트, 오피스텔 등)
            if streaming_callback:
                await streaming_callback.send_status("2️⃣ 단계 2: 분석 유형 결정 중...")  # type: ignore
            analysis_type = await self._determine_analysis_type(user_query)
            
            if streaming_callback:
                type_info = {
                    "분석_유형": analysis_type,
                    "한국어_유형": {
                        "apartment": "아파트",
                        "officetel": "오피스텔",
                        "house": "단독/다가구",
                        "row_house": "연립다세대"
                    }.get(analysis_type, "부동산"),
                    "관련_MCP_도구": f"get_{analysis_type}_trade_data, analyze_{analysis_type}_trade"
                }
                await streaming_callback.send_content(f"🏘️ 분석 유형 결정:\n```json\n{json.dumps(type_info, ensure_ascii=False, indent=2)}\n```")  # type: ignore
                await streaming_callback.send_status("3️⃣ 단계 3: 실제 데이터 수집 시작...")  # type: ignore
            
            # 3단계: 데이터 수집
            data_files = await self._collect_data(region_info, analysis_type, streaming_callback)
            
            # 4단계: 분석 실행
            if streaming_callback:
                await streaming_callback.send_status("4️⃣ 단계 4: 수집된 데이터 종합 분석...")  # type: ignore
            analysis_results = await self._analyze_data(data_files, streaming_callback)
            
            # 5단계: HTML 리포트 생성
            if streaming_callback:
                await streaming_callback.send_status("5️⃣ 단계 5: 전문 HTML 리포트 생성...")  # type: ignore
            report_html = await self._generate_html_report(
                user_query, region_info, analysis_type, analysis_results, streaming_callback
            )
            
            if streaming_callback:
                await streaming_callback.send_status("✅ 부동산 분석이 완료되었습니다")  # type: ignore
                
                # 최종 완료 정보
                completion_info = {
                    "분석_완료": True,
                    "처리_단계": 5,
                    "최종_결과": {
                        "지역": region_info["name"],
                        "유형": analysis_type,
                        "거래건수": analysis_results.get("total_transactions", 0),
                        "분석기간": analysis_results.get("analysis_period", "N/A")
                    }
                }
                await streaming_callback.send_content(f"🎉 분석 완료 요약:\n```json\n{json.dumps(completion_info, ensure_ascii=False, indent=2)}\n```")  # type: ignore
            
            return {
                "success": True,
                "report_content": report_html,
                "analysis_content": json.dumps(analysis_results, ensure_ascii=False, indent=2),
                "region_info": region_info,
                "analysis_type": analysis_type
            }
            
        except Exception as e:
            logger.error(f"❌ 부동산 쿼리 처리 실패: {e}")
            if streaming_callback:
                await streaming_callback.send_status(f"❌ 처리 실패: {str(e)}")  # type: ignore
            return {
                "success": False,
                "error": str(e),
                "report_content": "",
                "analysis_content": ""
            }
    
    async def _extract_region_info(self, query: str, streaming_callback) -> Dict[str, Any]:
        """지역 정보 추출"""
        
        if streaming_callback:
            await streaming_callback.send_status("📍 지역 정보를 파악 중...")  # type: ignore
        
        # 간단한 지역 매핑
        region_map = {
            "강남구": "11680", "서초구": "11650", "송파구": "11710", "강동구": "11740",
            "마포구": "11440", "영등포구": "11560", "용산구": "11170", "중구": "11140",
            "종로구": "11110", "성동구": "11200", "광진구": "11215", "동대문구": "11230",
            "중랑구": "11260", "성북구": "11290", "강북구": "11305", "도봉구": "11320",
            "노원구": "11350", "은평구": "11380", "서대문구": "11410", "양천구": "11470",
            "강서구": "11500", "구로구": "11530", "금천구": "11545", "관악구": "11620",
            "동작구": "11590", "과천시": "41290", "광명시": "41210", "하남시": "41450"
        }
        
        region_name = None
        region_code = None
        
        for name, code in region_map.items():
            if name in query:
                region_name = name
                region_code = code
                break
        
        if not region_name:
            region_name = "강남구"  # 기본값
            region_code = "11680"
        
        logger.info(f"📍 분석 지역: {region_name} ({region_code})")
        
        if streaming_callback:
            await streaming_callback.send_status(f"✅ 분석 지역 확정: {region_name}")  # type: ignore
        
        return {
            "name": region_name,
            "code": region_code
        }
    
    async def _determine_analysis_type(self, query: str) -> str:
        """분석 유형 결정"""
        
        if any(keyword in query for keyword in ["아파트", "APT", "apartment"]):
            return "apartment"
        elif any(keyword in query for keyword in ["오피스텔", "officetel"]):
            return "officetel"
        elif any(keyword in query for keyword in ["단독", "다가구", "house"]):
            return "house"
        elif any(keyword in query for keyword in ["연립", "다세대", "row"]):
            return "row_house"
        else:
            return "apartment"  # 기본값
    
    async def _collect_data(
        self, 
        region_info: Dict[str, Any], 
        analysis_type: str, 
        streaming_callback
    ) -> List[Dict[str, Any]]:
        """데이터 수집 - 실제 MCP 도구 호출"""
        
        if streaming_callback:
            await streaming_callback.send_status("📊 부동산 거래 데이터를 수집 중...")  # type: ignore
            await streaming_callback.send_tool_start(f"get_{analysis_type}_trade_data")  # type: ignore
        
        # 최근 3개월 데이터 수집
        current_date = datetime.now()
        year_months = []
        
        for i in range(3):
            if current_date.month - i > 0:
                year_month = f"{current_date.year}{current_date.month - i:02d}"
            else:
                year_month = f"{current_date.year - 1}{12 + current_date.month - i:02d}"
            year_months.append(year_month)
        
        collected_data = []
        
        for idx, year_month in enumerate(year_months):
            try:
                if streaming_callback:
                    await streaming_callback.send_status(f"📅 {year_month} 데이터 수집 중... ({idx+1}/{len(year_months)})")  # type: ignore
                
                # MCP 도구 호출하여 실제 데이터 수집
                tool_name = f"get_apt_trade_data"  # 아파트 매매 데이터
                args = {
                    "region_code": region_info["code"],
                    "year_month": year_month
                }
                
                logger.info(f"🔧 MCP 도구 호출: {tool_name}, args: {args}")
                
                if streaming_callback:
                    # JSON 형태로 도구 호출 정보 전송
                    tool_call_info = {
                        "tool": tool_name,
                        "arguments": args,
                        "region": region_info["name"],
                        "period": year_month
                    }
                    await streaming_callback.send_content(f"🔧 MCP 도구 호출:\n```json\n{json.dumps(tool_call_info, ensure_ascii=False, indent=2)}\n```")  # type: ignore
                
                result = await self.mcp_client.call_tool('kr-realestate', tool_name, args)
                
                if result and result.get('content'):
                    content = result['content'][0]['text'] if isinstance(result['content'], list) else result['content']
                    logger.info(f"📊 {year_month} 데이터 수집 완료: {content[:100]}...")
                    
                    if streaming_callback:
                        # MCP 응답 결과를 UI에 표시
                        response_info = {
                            "tool_response": {
                                "tool": tool_name,
                                "status": "success",
                                "file_path": content if content.endswith('.json') else "N/A",
                                "content_preview": content[:200] + "..." if len(content) > 200 else content
                            }
                        }
                        await streaming_callback.send_content(f"📥 MCP 응답 결과:\n```json\n{json.dumps(response_info, ensure_ascii=False, indent=2)}\n```")  # type: ignore
                        await streaming_callback.send_status(f"✅ {year_month} 원시 데이터 수집 완료")  # type: ignore
                    
                    # 파일 경로가 아닌 실제 데이터로 분석
                    if content.endswith('.json'):
                        if streaming_callback:
                            await streaming_callback.send_status(f"🔍 {year_month} 데이터 분석 중...")  # type: ignore
                        
                        # 분석 도구로 통계 생성
                        analyze_tool = f"analyze_apartment_trade"
                        analyze_args = {"file_path": content}
                        
                        if streaming_callback:
                            analyze_call_info = {
                                "tool": analyze_tool,
                                "arguments": analyze_args,
                                "data_file": content.split('/')[-1]
                            }
                            await streaming_callback.send_content(f"📊 분석 도구 호출:\n```json\n{json.dumps(analyze_call_info, ensure_ascii=False, indent=2)}\n```")  # type: ignore
                        
                        analyze_result = await self.mcp_client.call_tool('kr-realestate', analyze_tool, analyze_args)
                        if analyze_result and analyze_result.get('content'):
                            analyze_content = analyze_result['content'][0]['text'] if isinstance(analyze_result['content'], list) else analyze_result['content']
                            
                            if streaming_callback:
                                # 분석 도구 응답 결과 표시
                                analyze_response_info = {
                                    "analyze_response": {
                                        "tool": analyze_tool,
                                        "status": "success",
                                        "content_length": len(analyze_content),
                                        "response_preview": analyze_content[:300] + "..." if len(analyze_content) > 300 else analyze_content
                                    }
                                }
                                await streaming_callback.send_content(f"📥 분석 도구 응답:\n```json\n{json.dumps(analyze_response_info, ensure_ascii=False, indent=2)}\n```")  # type: ignore
                            
                            try:
                                # JSON 파싱하여 실제 분석 데이터 추출
                                analysis_data = json.loads(analyze_content)
                                collected_data.append({
                                    "year_month": year_month,
                                    "raw_file": content,
                                    "analysis": analysis_data,
                                    "raw_response": analyze_content  # 원시 응답 데이터도 보관
                                })
                                
                                if streaming_callback:
                                    # 분석 결과를 예쁜 JSON으로 표시
                                    result_summary = {
                                        "period": year_month,
                                        "transactions": analysis_data.get("총_거래건수", 0),
                                        "avg_price": analysis_data.get("평균_거래가격", 0),
                                        "max_price": analysis_data.get("최고_거래가격", 0),
                                        "min_price": analysis_data.get("최저_거래가격", 0)
                                    }
                                    await streaming_callback.send_content(f"📈 {year_month} 분석 결과:\n```json\n{json.dumps(result_summary, ensure_ascii=False, indent=2)}\n```")  # type: ignore
                                    await streaming_callback.send_status(f"✅ {year_month} 분석 완료: {analysis_data.get('총_거래건수', 0)}건")  # type: ignore
                                
                                logger.info(f"✅ {year_month} 분석 완료")
                            except json.JSONDecodeError:
                                logger.warning(f"⚠️ {year_month} 분석 결과 JSON 파싱 실패")
                                if streaming_callback:
                                    await streaming_callback.send_status(f"⚠️ {year_month} 분석 실패: JSON 파싱 오류")  # type: ignore
                
            except Exception as e:
                logger.warning(f"⚠️ {year_month} 데이터 수집 실패: {e}")
                if streaming_callback:
                    await streaming_callback.send_status(f"⚠️ {year_month} 데이터 수집 실패: {str(e)}")  # type: ignore
        
        if streaming_callback:
            await streaming_callback.send_tool_complete(f"get_{analysis_type}_trade_data", f"{len(collected_data)}개월 데이터 수집 및 분석")  # type: ignore
            await streaming_callback.send_status("📊 전체 데이터 수집 완료")  # type: ignore
        
        return collected_data
    
    async def _analyze_data(self, collected_data: List[Dict[str, Any]], streaming_callback) -> Dict[str, Any]:
        """데이터 분석 - 수집된 실제 데이터 종합"""
        
        if streaming_callback:
            await streaming_callback.send_status("🔍 수집된 데이터를 종합 분석 중...")  # type: ignore
        
        # 실제 수집된 데이터 종합
        total_transactions = 0
        total_amount = 0
        avg_prices = []
        monthly_summary = []
        
        for data in collected_data:
            analysis = data.get("analysis", {})
            if isinstance(analysis, dict):
                # 거래 건수
                if "총_거래건수" in analysis:
                    total_transactions += analysis.get("총_거래건수", 0)
                
                # 거래 금액
                if "총_거래금액" in analysis:
                    total_amount += analysis.get("총_거래금액", 0)
                
                # 평균 가격
                if "평균_거래가격" in analysis:
                    avg_prices.append(analysis.get("평균_거래가격", 0))
                
                # 월별 요약
                monthly_summary.append({
                    "month": data["year_month"],
                    "transactions": analysis.get("총_거래건수", 0),
                    "avg_price": analysis.get("평균_거래가격", 0),
                    "max_price": analysis.get("최고_거래가격", 0),
                    "min_price": analysis.get("최저_거래가격", 0)
                })
        
        analysis_results = {
            "total_transactions": total_transactions,
            "total_amount": total_amount,
            "avg_price_overall": sum(avg_prices) / len(avg_prices) if avg_prices else 0,
            "monthly_data": monthly_summary,
            "data_files_count": len(collected_data),
            "analysis_period": f"{len(collected_data)}개월"
        }
        
        if streaming_callback:
            # 종합 분석 결과를 예쁜 JSON으로 표시
            summary_json = {
                "종합_분석_결과": {
                    "총_거래건수": total_transactions,
                    "평균_거래가격": f"{analysis_results['avg_price_overall']:,.0f}만원",
                    "분석_기간": analysis_results['analysis_period'],
                    "데이터_파일_수": len(collected_data)
                },
                "월별_요약": monthly_summary
            }
            await streaming_callback.send_content(f"📊 종합 분석 결과:\n```json\n{json.dumps(summary_json, ensure_ascii=False, indent=2)}\n```")  # type: ignore
            await streaming_callback.send_status(f"✅ 종합 분석 완료: 총 {total_transactions}건, 평균 {analysis_results['avg_price_overall']:,.0f}만원")  # type: ignore
        
        logger.info(f"📊 종합 분석 완료: 총 {total_transactions}건, 평균가 {analysis_results['avg_price_overall']:,.0f}만원")
        
        return analysis_results
    
    async def _generate_html_report(
        self,
        user_query: str,
        region_info: Dict[str, Any],
        analysis_type: str,
        analysis_results: Dict[str, Any],
        streaming_callback
    ) -> str:
        """HTML 리포트 생성 - 실제 분석 데이터를 LLM에게 전달"""
        
        if streaming_callback:
            await streaming_callback.send_status("📝 LLM이 분석 리포트를 생성 중...")  # type: ignore
        
        # 모든 도구 호출 결과와 응답 데이터를 LLM에게 전달
        comprehensive_data = {
            "사용자_요청": user_query,
            "분석_지역": {
                "이름": region_info['name'],
                "코드": region_info['code']
            },
            "분석_유형": analysis_type,
            "종합_분석_결과": analysis_results,
            "월별_상세_데이터": []  # type: ignore
        }
        
        # 각 월별 상세 데이터 추가
        monthly_data_list = analysis_results.get("monthly_data", [])
        if isinstance(monthly_data_list, list):
            for data in monthly_data_list:
                monthly_detail = {
                    "월": data.get("month"),
                    "거래건수": data.get("transactions", 0),
                    "평균가격": data.get("avg_price", 0),
                    "최고가격": data.get("max_price", 0),
                    "최저가격": data.get("min_price", 0)
                }
                comprehensive_data["월별_상세_데이터"].append(monthly_detail)  # type: ignore
        
        # 실제 분석 결과를 LLM에게 전달
        prompt = f"""
당신은 부동산 분석 전문가입니다. 아래의 실제 부동산 거래 데이터를 바탕으로 전문적이고 상세한 HTML 분석 리포트를 생성해주세요.

=== 수집된 모든 데이터 ===
{json.dumps(comprehensive_data, ensure_ascii=False, indent=2)}

=== 요구사항 ===
1. 완전한 HTML 문서 (<!DOCTYPE html>부터 시작)
2. 실제 수집된 데이터를 기반으로 한 구체적이고 정확한 분석
3. 다음 요소들을 포함한 시각적 리포트:
   - 월별 거래량 차트 (JavaScript Chart.js 사용)
   - 가격 추이 그래프
   - 거래 현황 테이블
   - 주요 지표 요약 카드
4. 전문적인 분석 인사이트:
   - 거래량 변화 트렌드
   - 가격 변동 분석
   - 시장 동향 해석
5. 반응형 디자인과 내장 CSS 스타일링
6. Chart.js CDN을 포함하여 차트가 실제로 작동하도록 구현

=== 중요 ===
- 실제 데이터 수치를 정확히 반영해주세요
- 거래건수가 0인 경우 "데이터 없음" 또는 "거래 없음"으로 표시
- 모든 금액은 "만원" 단위로 표시
- HTML 코드만 반환하고 설명이나 주석은 제외하세요

HTML 코드만 반환하세요:
"""
        
        if streaming_callback:
            # LLM에게 전달하는 종합 데이터 정보 표시
            llm_data_info = {
                "전달_데이터_요약": {
                    "총_거래건수": analysis_results.get("total_transactions", 0),
                    "분석_기간": analysis_results.get("analysis_period", "N/A"),
                    "월별_데이터_수": len(analysis_results.get("monthly_data", [])),
                    "지역": region_info["name"],
                    "프롬프트_길이": len(prompt)
                },
                "포함된_데이터": [
                    "종합 분석 결과",
                    "월별 상세 거래 데이터",
                    "가격 통계 (평균/최고/최저)",
                    "거래량 트렌드"
                ]
            }
            await streaming_callback.send_content(f"🤖 LLM에게 전달하는 종합 데이터:\n```json\n{json.dumps(llm_data_info, ensure_ascii=False, indent=2)}\n```")  # type: ignore
            await streaming_callback.send_status("🧠 LLM이 실제 데이터를 분석하여 HTML을 생성 중...")  # type: ignore
        
        try:
            html_content = await self.llm_client.generate_code(
                prompt=prompt,
                model_type=ModelType.LLM
            )
            
            if streaming_callback:
                await streaming_callback.send_status("✅ LLM HTML 생성 완료, 검증 중...")  # type: ignore
            
            # HTML 검증 및 저장
            if '<!DOCTYPE' in html_content and '<html' in html_content:
                timestamp = int(datetime.now().timestamp())
                filename = f"realestate_report_{timestamp}.html"
                filepath = f"./reports/{filename}"
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                if streaming_callback:
                    # 생성된 HTML 정보 표시
                    html_info = {
                        "file_name": filename,
                        "file_path": filepath,
                        "html_size": len(html_content),
                        "contains_charts": "chart" in html_content.lower() or "canvas" in html_content.lower(),
                        "contains_tables": "<table" in html_content.lower(),
                        "data_driven": True,
                        "based_on_real_data": comprehensive_data["종합_분석_결과"]["total_transactions"] > 0  # type: ignore
                    }
                    await streaming_callback.send_content(f"📄 데이터 기반 HTML 리포트:\n```json\n{json.dumps(html_info, ensure_ascii=False, indent=2)}\n```")  # type: ignore
                    await streaming_callback.send_code(html_content)  # type: ignore
                    await streaming_callback.send_status(f"✅ 실제 데이터 기반 HTML 저장: {filename}")  # type: ignore
                
                logger.info(f"📝 실제 데이터 기반 HTML 리포트 생성 완료: {filepath}")
                return html_content
            else:
                logger.warning("⚠️ LLM이 완전한 HTML을 생성하지 못함")
                if streaming_callback:
                    await streaming_callback.send_status("⚠️ LLM HTML 검증 실패, 폴백 HTML 생성 중...")  # type: ignore
                return self._generate_fallback_html(user_query, region_info, analysis_type, analysis_results)
                
        except Exception as e:
            logger.error(f"❌ LLM HTML 생성 실패: {e}")
            if streaming_callback:
                await streaming_callback.send_status(f"❌ LLM 오류: {str(e)}, 폴백 HTML 생성 중...")  # type: ignore
            return self._generate_fallback_html(user_query, region_info, analysis_type, analysis_results)
    
    def _generate_fallback_html(self, user_query: str, region_info: Dict[str, Any], analysis_type: str, analysis_results: Dict[str, Any]) -> str:
        """폴백 HTML 생성 - 실제 데이터 포함"""
        
        analysis_type_kr = {
            "apartment": "아파트",
            "officetel": "오피스텔", 
            "house": "단독/다가구",
            "row_house": "연립다세대"
        }.get(analysis_type, "부동산")
        
        monthly_rows = ""
        for month_data in analysis_results.get("monthly_data", []):
            monthly_rows += f"""
            <tr>
                <td>{month_data['month']}</td>
                <td>{month_data['transactions']:,}건</td>
                <td>{month_data['avg_price']:,.0f}만원</td>
                <td>{month_data['max_price']:,.0f}만원</td>
                <td>{month_data['min_price']:,.0f}만원</td>
            </tr>"""
        
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{region_info['name']} {analysis_type_kr} 분석 리포트</title>
    <style>
        body {{ font-family: 'Noto Sans KR', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        .summary {{ background: #ecf0f1; padding: 20px; border-radius: 5px; margin: 20px 0; }}
        .highlight {{ color: #e74c3c; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: center; }}
        th {{ background: #3498db; color: white; }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #3498db; color: white; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏠 {region_info['name']} {analysis_type_kr} 분석 리포트</h1>
        
        <div class="summary">
            <h2>📊 분석 개요</h2>
            <div class="metric">총 거래건수: {analysis_results.get('total_transactions', 0):,}건</div>
            <div class="metric">평균 거래가격: {analysis_results.get('avg_price_overall', 0):,.0f}만원</div>
            <div class="metric">분석 기간: {analysis_results.get('analysis_period', 'N/A')}</div>
        </div>
        
        <div class="summary">
            <h2>🔍 사용자 요청</h2>
            <p>{user_query}</p>
        </div>
        
        <div class="summary">
            <h2>📈 월별 거래 현황</h2>
            <table>
                <thead>
                    <tr>
                        <th>년월</th>
                        <th>거래건수</th>
                        <th>평균가격</th>
                        <th>최고가격</th>
                        <th>최저가격</th>
                    </tr>
                </thead>
                <tbody>
                    {monthly_rows}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>"""
        
        # 파일 저장
        timestamp = int(datetime.now().timestamp())
        filename = f"realestate_report_{timestamp}.html"
        filepath = f"./reports/{filename}"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return html 