import asyncio
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PlayMcpServer")

# [가이드 준수] "kakao" 단어 전면 배제
mcp_server = Server("biz-assistant-service")

app = FastAPI(title="PlayMCP Endpoint Server", version="2026.06.12")

# 크로스 도메인 이슈 방지 (PlayMCP 플랫폼의 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [필수 핵심] 카카오가 요구하는 하위 메시지 경로(/mcp/messages)를 생성자에 강제 주입
sse_transport = SseServerTransport("/mcp/messages")

@mcp_server.list_tools()
async def handle_list_tools():
    """[정보 불러오기] 클릭 시 카카오 플랫폼에 노출될 필수 규격 준수 툴"""
    return [
        Tool(
            name="fetch_market_insights",
            description="Retrieves summarized consumer market insights from the SmartStore(스마트스토어) service.",
            inputSchema={
                "type": "object",
                "properties": {
                    "trend_type": {"type": "string", "description": "daily or weekly"}
                },
                "required": ["trend_type"]
            },
            annotations={
                "title": "SmartStore Insight Viewer",
                "readOnlyHint": True,
                "destructiveHint": False,
                "openWorldHint": False,
                "idempotentHint": True
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    if name == "fetch_market_insights":
        return [TextContent(type="text", text="### 정제된 마크다운 결과 리턴")]
    raise ValueError(f"Unknown tool: {name}")

# ====================================================
# [정보 불러오기] 전용 Endpoint 라우팅 매핑
# ====================================================

# 카카오 콘솔 등록 타겟: https://...kakaocloud.io/mcp
@app.get("/mcp")
async def sse_endpoint(request: Request):
    """카카오 플랫폼이 최초로 연결(Handshake)하는 SSE 진입점"""
    logger.info(">>> [PlayMCP] GET /mcp (SSE 연결 수립 요청)")
    async with sse_transport.connect_scope(request.scope, request.receive, sse_transport.handle_sse):
        # 연결이 중간에 끊기지 않도록 대기 상태 유지
        while True:
            await asyncio.sleep(1)

@app.post("/mcp/messages")
async def messages_endpoint(request: Request):
    """[정보 불러오기] 클릭 시 'initialize' 프로토콜을 수신하는 포트"""
    logger.info(">>> [PlayMCP] POST /mcp/messages (초기화 데이터 수신)")
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)
    return {"status": "accepted"}

@app.get("/")
async def lb_health_check():
    """로드밸런서 활성화용 루트 헬스체크"""
    return {"status": "healthy"}
