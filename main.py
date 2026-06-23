import asyncio
from fastapi import FastAPI, Request
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

# 서버 이름 (kakao 단어 배제)
mcp_server = Server("music-trend-service-server")

app = FastAPI(title="PlayMCP Compliant Gateway")
sse_transport = SseServerTransport("/messages")

@mcp_server.list_tools()
async def handle_list_tools():
    """
    PlayMCP 최신 규격을 준수하는 툴 목록 반환
    """
    return [
        Tool(
            name="get_trending_music",
            description="Retrieves a list of the current most popular or trending songs from Melon(멜론) service.",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Number of songs to retrieve (1-10)"}
                },
                "required": ["count"]
            },
            annotations={
                "title": "Melon Trending Music Retriever",
                "readOnlyHint": True,
                "destructiveHint": False,
                "openWorldHint": False,
                "idempotentHint": True
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    """툴 실행 및 결과 반환"""
    if name == "get_trending_music":
        count = arguments.get("count", 5) if arguments else 5

        markdown_result = (
            "### Melon(멜론) 실시간 트렌드 TOP 3\n"
            "1. **Song A** - Artist X\n"
            "2. **Song B** - Artist Y\n"
            "3. **Song C** - Artist Z\n"
            f"\n*조회된 개수: {count}개*"
        )

        return [TextContent(type="text", text=markdown_result)]

    raise ValueError(f"Unknown tool: {name}")


# --- SSE 엔드포인트 (MCP 연결용) ---

@app.get("/")
async def root():
    return {"status": "healthy"}

@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE 연결 엔드포인트 - MCP 클라이언트가 여기로 접속합니다"""
    async with sse_transport.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options(),
        )

@app.post("/messages")
async def messages_endpoint(request: Request):
    """POST 메시지 엔드포인트 - SSE 세션으로 메시지를 라우팅합니다"""
    await sse_transport.handle_post_message(
        request.scope,
        request.receive,
        request._send,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
