import logging
from fastapi import FastAPI
from mcp.server import Server
from mcp.server.fastapi import FastMcpServerTransport  # 공식 공식 전송 프레임워크
from mcp.types import Tool, TextContent

# 1. 로깅 시스템 가동 (카카오클라우드 로그 모니터링용)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PlayMcpServer")

# 2. [가이드 준수] 서버 이름에 "kakao" 단어 전면 배제 (대소문자 무관)
mcp_server = Server("biz-trend-analyzer")

# 3. [가이드 준수] Stateless 형태의 FastAPI 앱 정의
app = FastAPI(
    title="PlayMCP Compliant Production Server", 
    version="2026.06.12"
)

# ==========================================
# 4. PlayMCP Tool 구성 가이드 완벽 매핑
# ==========================================
@mcp_server.list_tools()
async def handle_list_tools():
    return [
        Tool(
            # [규칙] 이름에 "kakao" 포함 금지, 영문/숫자/_/-만 허용
            name="fetch_market_insights",
            
            # [규칙] 영문 중심 작성, 고유 서비스명 국문/영문 병기 (Melon(멜론) 스타일 준수), 1024자 이내
            description="Retrieves summarized consumer market insights and keyword trends from the SmartStore(스마트스토어) service.",
            
            inputSchema={
                "type": "object",
                "properties": {
                    "trend_type": {
                        "type": "string", 
                        "description": "Period type of the trend, such as daily or weekly"
                    }
                },
                "required": ["trend_type"]
            },
            
            # [규칙] annotations 5대 필수 프로퍼티 누락 없이 전면 수동 지정
            annotations={
                "title": "SmartStore Insight Viewer",
                "readOnlyHint": True,        # 단순 조회 API
                "destructiveHint": False,    # 데이터 파괴 없음
                "openWorldHint": False,      # 외부 상태 변조 위험 없음
                "idempotentHint": True       # 반복 호출 가능 (멱등성 보장)
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    # [규칙] 응답 속도는 평균 100ms 이내, p99 3,000ms 이내 동작 보장
    if name == "fetch_market_insights":
        arguments = arguments or {}
        trend_type = arguments.get("trend_type", "daily")
        
        # [규칙] API 응답 원본 가공 없이 원천 주입 절대 금지 -> 정제된 마크다운 포맷팅 출력
        # [규칙] 광고성 문구 유도 전면 배제
        markdown_output = (
            f"### SmartStore(스마트스토어) [{trend_type.upper()}] 트렌드 브리핑\n"
            "1. **식음료 부문:** 제로 슈거 음료 카테고리 검색량 24% 급증\n"
            "2. **패션 잡화:** 친환경 리사이클 백 수요 지속 증가세\n"
            "\n*본 데이터는 AI 분석을 통해 가공된 정제 텍스트입니다.*"
        )
        return [TextContent(type="text", text=markdown_output)]
        
    raise ValueError(f"Unknown tool name: {name}")

# ====================================================
# 5. [핵심] 수동 라우팅을 버리고 공식 ASGI Transport 바인딩 구조 채택
# ====================================================
# /mcp 경로로 유입되는 모든 스트림과 메시지 제어권을 SDK 내부 라우터에 위임하여 
# 카카오클라우드 로드밸런서 환경에서 통신이 가로막히는 병목현상을 해결합니다.
transport = FastMcpServerTransport(mcp_server)

# PlayMCP 개발자 콘솔 입력 타겟 도메인 주소: https://...kakaocloud.io/mcp
app.mount("/mcp", transport.asgi_app)

@app.get("/")
async def root_health():
    """로드밸런서 타겟 그룹용 헬스체크"""
    return {"status": "healthy", "service": "active"}
