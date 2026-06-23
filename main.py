import asyncio
from fastapi import FastAPI, Request
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

# [수정] 서버 이름에 "kakao" 단어를 완전히 배제합니다.
mcp_server = Server("music-trend-service-server")

app = FastAPI(title="PlayMCP Compliant Gateway")
sse_transport = SseServerTransport("/messages")

@mcp_server.list_tools()
async def handle_list_tools():
    """
    PlayMCP 최신 규격(2026-06-12)을 준수하는 툴 목록 반환
    """
    return [
        Tool(
            # 1. 툴 이름 규칙: 영문, 숫자, _, - 만 허용 ("kakao" 포함 금지)
            name="get_trending_music",
            
            # 2. 설명 규칙: 영문 권장, 서비스명 국문/영문 병기 (Melon(멜론)), 1024자 이내
            description="Retrieves a list of the current most popular or trending songs from Melon(멜론) service.",
            
            # 3. 입력 스키마 정의
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Number of songs to retrieve (1-10)"}
                },
                "required": ["count"]
            },
            
            # 4. [필수] 가이드라인 명시 annotations 5대 요소 누락 없이 전체 지정
            annotations={
                "title": "Melon Trending Music Retriever",
                "readOnlyHint": True,         # 단순히 데이터만 조회하므로 True
                "destructiveHint": False,     # 데이터를 삭제하거나 파괴하지 않으므로 False
                "openWorldHint": False,       # 외부 세계 상태를 무작정 바꾸지 않음
                "idempotentHint": True        # 여러 번 호출해도 결과가 같은 멱등성 만족
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    """툴 실행 및 결과 반환"""
    if name == "get_trending_music":
        count = arguments.get("count", 5) if arguments else 5
        
        # 가이드라인 준수: API 원본 데이터를 그대로 쏘지 말고, 최소한의 정제된 마크다운으로 구성
        # 데이터 크기를 최소화하여 LLM이 답변하기 좋게 만듭니다.
        markdown_result = (
            "### Melon(멜론) 실시간 트렌드 TOP 3\n"
            "1. **Song A** - Artist X\n"
            "2. **Song B** - Artist Y\n"
            "3. **Song C** - Artist Z\n"
            f"\n*조회된 개수: {count}개*"
        )
        
        return [TextContent(type="text", text=markdown_result)]
    
    raise ValueError(f"Unknown tool: {name}")

# --- PlayMCP 연동 프로토콜 (Streamable HTTP / SSE) ---

@app.get("/")
async def root():
    return {"status": "healthy"}

@app.get("/sse")
async def sse_endpoint(request: Request):
    async with sse_transport.connect_scope(request.scope, request.receive, sse_transport.handle_sse):
        await asyncio.Event().wait()

@app.post("/messages")
async def messages_endpoint(request: Request):
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)
    return {"status": "accepted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
