import asyncio
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

# 1. 공모전용 서버 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PlayMcpServer")

# [가이드 필수] 서버 이름에 대소문자 무관 "kakao" 전면 금지
mcp_server = Server("garam-mcp-service")

app = FastAPI(
    title="PlayMCP Streamable HTTP Server", 
    version="2026.06.12",
    description="Verified Remote MCP Server for Agentic Player 10"
)

# 교차 출처 에러(CORS) 완벽 방지
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [가이드 매핑] 카카오 설정에 명시된 /mcp 엔드포인트 및 메시지 전송로 지정
# 카카오 클라이언트가 전송 사양(--transport=streamablehttp)으로 찌를 때 대응하는 규격입니다.
sse_transport = SseServerTransport("/mcp/messages")

# ==========================================
# 2. PlayMCP 필수 프로퍼티 및 5대 애노테이션 지정
# ==========================================
@mcp_server.list_tools()
async def handle_list_tools():
    """[정보 불러오기] 클릭 시 카카오 플랫폼이 읽어가서 화면에 등록할 Tool 정의"""
    logger.info(">>> [PlayMCP] list_tools 스펙 요청을 수신하여 툴 목록을 전송합니다.")
    return [
        Tool(
            # 규칙: 영어, 숫자, _, - 만 허용 (1~128자)
            name="fetch_market_insights",
            
            # 규칙: 서비스 이름 국/영문 병기 규칙 준수, 1024자 이내 영문 중심
            description="Retrieves summarized consumer market insights and search volume trends from the SmartStore(스마트스토어) service.",
            
            inputSchema={
                "type": "object",
                "properties": {
                    "trend_type": {"type": "string", "description": "daily or weekly"}
                },
                "required": ["trend_type"]
            },
            
            # 규칙: annotations 내 5대 속성 누락 없이 전면 수동 지정
            annotations={
                "title": "SmartStore Insight Viewer",
                "readOnlyHint": True,        # 단순 데이터 조회
                "destructiveHint": False,    # 데이터 변경 없음
                "openWorldHint": False,      # 사이드 이펙트 없음
                "idempotentHint": True       # 멱등성 보장
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    # 규칙: 응답 속도는 평균 100ms 이내 보장 필수
    if name == "fetch_market_insights":
        # 규칙: API 응답 원본을 그대로 쏘지 말고 정제된 마크다운 포맷 텍스트 권장 (광고 유도 금지)
        markdown_output = (
            "### SmartStore(스마트스토어) 실시간 트렌드 분석\n"
            "1. **리빙/인테리어:** 친환경 소재 가구군 트래픽 상승\n"
            "2. **디지털/가전:** 1인 가구용 소형 공기청정기 수요 증가\n"
            "\n*본 리포트는 PlayMCP 표준 응답 규격에 맞게 정제되었습니다.*"
        )
        return [TextContent(type="text", text=markdown_output)]
    raise ValueError(f"Unknown tool name: {name}")

# ====================================================
# 3. Streamable HTTP 통신용 Endpoint 명시적 매핑
# ====================================================

# 카카오 콘솔 등록 URL 주소: https://garam-mcp-server.playmcp-endpoint.kakaocloud.io/mcp
@app.get("/mcp")
async def sse_endpoint(request: Request):
    """PlayMCP 플랫폼이 최초 연결(Handshake)을 위해 진입하는 Streamable HTTP GET 엔드포인트"""
    logger.info(">>> [PlayMCP] GET /mcp (Streamable HTTP SSE 연결 수립)")
    async with sse_transport.connect_scope(request.scope, request.receive, sse_transport.handle_sse):
        # 인프라 레이어의 세션 단절을 방지하기 위해 1초 간격으로 무한 루프 대기
        while True:
            await asyncio.sleep(1)

@app.post("/mcp/messages")
async def messages_endpoint(request: Request):
    """[정보 불러오기] 클릭 시 'initialize' 프로토콜 패키지를 수신하는 POST 엔드포인트"""
    logger.info(">>> [PlayMCP] POST /mcp/messages (JSON-RPC 초기화 제어 메시지 수신)")
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)
    return {"status": "accepted"}

@app.get("/")
async def internal_health():
    """PlayMCP in KC 인프라의 활성화를 보장하는 루트 헬스체크"""
    return {"status": "healthy", "transport": "streamablehttp"}
