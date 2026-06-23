import asyncio
import logging
from fastapi import FastAPI, Request
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PlayMcpServer")

# 1. 가이드 준수: 서버 이름에 "kakao" 단어 제외
mcp_server = Server("biz-trend-analyzer")

# 2. 메인 FastAPI 앱 생성
app = FastAPI(title="PlayMCP Production Server", version="2026.06.12")

# 중요: 수동 패스 매핑 오류를 방지하기 위해 단일 SSE 트랜스포트 객체 정의
# 메인 주소가 /mcp 이므로, 메시지는 /mcp/messages로 전송되도록 명시적 세팅
sse_transport = SseServerTransport("/mcp/messages")

# ==========================================
# PlayMCP Tool 구성 규칙 100% 매핑
# ==========================================
@mcp_server.list_tools()
async def handle_list_tools():
    return [
        Tool(
            name="fetch_market_insights",
            description="Retrieves summarized consumer market insights from the SmartStore(스마트스토어) service.",
            inputSchema={
                "type": "object",
                "properties": {
                    "trend_type": {"type": "string", "description": "e.g., daily"}
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
        markdown_output = "### SmartStore(스마트스토어) 시장 분석 결과\n- 가이드라인에 맞춘 마크다운 포맷 텍스트."
        return [TextContent(type="text", text=markdown_output)]
    raise ValueError(f"Unknown tool: {name}")

# ====================================================
# [503 에러 해결] 인프라 헬스체크 및 라우팅 명확화
# ====================================================

@app.get("/")
async def root_health():
    """
    [★중요] 카카오클라우드 로드밸런서(LB) 헬스체크용 엔드포인트
    LB가 이 경로로 200 OK를 받아야 503 에러를 풀고 트래픽을 열어줍니다.
    """
    return {"status": "healthy", "mcp_server": "running"}

@app.get("/mcp")
async def sse_endpoint(request: Request):
    """PlayMCP 플랫폼 진입용 SSE 연결 경로"""
    logger.info("PlayMCP 플랫폼으로부터 SSE Handshake 요청 수신.")
    async with sse_transport.connect_scope(request.scope, request.receive, sse_transport.handle_sse):
        # 무한 블로킹으로 인한 인프라 타임아웃 방지를 위해 세션 유지 루프 가동
        while True:
            await asyncio.sleep(1)

@app.post("/mcp/messages")
async def messages_endpoint(request: Request):
    """PlayMCP 제어 메시지 처리 경로"""
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)
    return {"status": "accepted"}
