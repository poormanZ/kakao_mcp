import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

# 1. MCP 서버 초기화 (서버 이름 및 버전 정의)
mcp_server = Server("kakao-playmcp-server")

# 2. FastAPI 앱 생성
app = FastAPI(title="Kakao PlayMCP Gateway")
sse_transport = SseServerTransport("/messages")

# [샘플 툴 등록] 카카오 PlayMCP가 인식할 기능을 정의합니다.
@mcp_server.list_tools()
async def handle_list_tools():
    """
    PlayMCP 등록 시 이 함수가 자동 호출되어 툴 목록을 수집합니다.
    설명(description)은 명확하고 간결하게 영어로 작성하는 것이 좋습니다.
    """
    return [
        Tool(
            name="get_kakao_status",
            description="Get the current status or mock data for Kakao service.",
            inputSchema={
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "e.g., talk, map, taxi"}
                },
                "required": ["service_name"]
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    """실제 AI가 툴을 실행할 때 호출되는 로직입니다."""
    if name == "get_kakao_status":
        service = arguments.get("service_name", "unknown")
        # 실제 처리 로직 수행 (예: 카카오 API 연동 등)
        return [TextContent(type="text", text=f"Service '{service}' is running normally.")]
    
    raise ValueError(f"Unknown tool: {name}")

# --- PlayMCP 연동을 위한 SSE 엔드포인트 설정 ---

@app.get("/")
async def root():
    """서버가 살아있는지 검증하는 헬스체크용 경로"""
    return {"status": "healthy", "mcp_server": "active"}

@app.get("/sse")
async def sse_endpoint(request: Request):
    """
    PlayMCP가 서버에 이벤트를 구독하기 위해 연결하는 엔드포인트입니다.
    PlayMCP 등록창의 'URL' 항목에 이 주소(예: https://your-domain.ngrok-free.app/sse)를 입력해야 합니다.
    """
    async with sse_transport.connect_scope(request.scope, request.receive, sse_transport.handle_sse):
        # 연결 유지 및 스트리밍 처리
        await asyncio.Event().wait()

@app.post("/messages")
async def messages_endpoint(request: Request):
    """PlayMCP가 JSON-RPC 메시지(요청)를 보낼 때 사용하는 엔드포인트입니다."""
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)
    return {"status": "accepted"}

if __name__ == "__main__":
    import uvicorn
    # 외부(PlayMCP)에서 접속할 수 있도록 0.0.0.0 포트로 호스팅합니다.
    uvicorn.run(app, host="0.0.0.0", port=8000)
