import asyncio
import logging
from fastapi import FastAPI, Request
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PlayMcpServer")

# 1. 서버 이름 규격 준수 ("kakao" 단어 제외)
mcp_server = Server("biz-trend-analyzer")

app = FastAPI(title="PlayMCP Compliant Server", version="2026.06.12")

# [중요] SSE 전송 레이어의 엔드포인트를 명확히 정의합니다.
# 이렇게 하면 PlayMCP가 주소 뒤에 붙여서 보낼 메시지 수신 경로가 세팅됩니다.
sse_transport = SseServerTransport("/mcp/messages")

@mcp_server.list_tools()
async def handle_list_tools():
    return [
        Tool(
            name="fetch_market_insights",
            description="Retrieves summarized consumer market insights from the SmartStore(스마트스토어) service.",
            inputSchema={
                "type": "object",
                "properties": {
                    "trend_type": {"type": "string", "description": "e.g., daily, weekly"}
                },
                "required": ["trend_type"]
            },
            annotations={
                "title": "Market Insight Viewer",
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
        markdown_output = "### SmartStore(스마트스토어) 시장 분석 결과\n- 현재 패션 및 리빙 카테고리 수요 증가세 고조."
        return [TextContent(type="text", text=markdown_output)]
    raise ValueError(f"Unknown tool: {name}")

# ====================================================
# 카카오 PlayMCP 연결용 스트리밍 / 메시지 라우팅 주소 세팅
# ====================================================

# PlayMCP 콘솔에 등록하는 최종 URL: https://...kakaocloud.io/mcp
@app.get("/mcp")
async def sse_endpoint(request: Request):
    """PlayMCP 플랫폼이 SSE 스트림을 연결하기 위해 진입하는 GET 엔드포인트"""
    logger.info("PlayMCP에서 SSE 연결 요청(GET /mcp)이 들어왔습니다.")
    
    async with sse_transport.connect_scope(request.scope, request.receive, sse_transport.handle_sse):
        # 연결을 끊지 않고 상시 대기 상태(Keep-Alive)로 유지합니다.
        await asyncio.Event().wait()

@app.post("/mcp/messages")
async def messages_endpoint(request: Request):
    """PlayMCP가 대화 및 제어 메시지를 보낼 때 호출하는 POST 엔드포인트"""
    logger.info("PlayMCP에서 메시지(POST /mcp/messages)가 수신되었습니다.")
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)
    return {"status": "accepted"}

@app.get("/")
async def health():
    return {"status": "alive"}
