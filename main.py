import asyncio
import logging
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

# 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PlayMcpServer")

# ==========================================
# 1. PlayMCP 서버 생성 조건 준수
# ==========================================
# [규칙] Server Name에 "kakao" 단어 대소문자 구분 없이 포함 금지
# [규칙] 최소 지원버전(2025-03-26) 등을 만족하는 최신 SDK 구조 사용
mcp_server = Server("biz-assistant-service")

app = FastAPI(
    title="PlayMCP Compliant Web Server",
    version="2026.06.12",
    description="Stateless Remote MCP Server for PlayMCP"
)
sse_transport = SseServerTransport("/messages")

# ==========================================
# 2. 사용자 인증 (커스텀 헤더 방식 예시)
# ==========================================
# 가이드: 사용자 인증이 필요한 경우, OAuth 인증 혹은 커스텀 헤더 방식을 지원해야 합니다.
API_KEY_NAME = "X-MCP-Authorization"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_mcp_auth(api_key: str = Depends(api_key_header)):
    # 인증이 필수가 아닌 툴이 있거나 헬스체크를 위해 구조만 마련 (필요 시 활성화)
    if api_key and api_key != "expected-secure-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MCP Authorization Token"
        )
    return api_key

# ==========================================
# 3. PlayMCP Tool 구성 규칙 준수
# ==========================================
@mcp_server.list_tools()
async def handle_list_tools():
    """
    PlayMCP에 등록될 툴 목록을 정의합니다.
    """
    return [
        Tool(
            # [규칙] 툴 이름: 1~128자, 영문 대소문자/숫자/_/- 만 허용 ("kakao" 포함 금지)
            # [규칙] Kakao Tools 반영 시 자동으로 prefix가 붙으므로 툴 이름에 직접 MCP명(서비스명) 포함하지 않음
            name="fetch_product_trends",
            
            # [규칙] Description 유의사항:
            # - 가능한 영문 작성 권장 (1,024자 이내)
            # - 고유명사로서 서비스 이름은 영문, 국문 병기 표기 규칙 준수 -> Melon(멜론) 스타일 반영
            description="Retrieves a summarized list of the current trending business items and consumer insights from the SmartStore(스마트스토어) platform.",
            
            # 입력 스키마 정의
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "The target product category (e.g., fashion, electronics, food)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of items to retrieve (max 5)",
                        "default": 3
                    }
                },
                "required": ["category"]
            },
            
            # [규칙] 반드시 포함시켜야 할 property - annotations 5대 요소 필수 기재
            annotations={
                "title": "SmartStore Trend Analyzer",
                "readOnlyHint": True,       # 단순 조회성 작업이므로 True
                "destructiveHint": False,   # 데이터 파괴/삭제가 없으므로 False
                "openWorldHint": False,     # 외부 인프라의 상태를 임의로 변경하지 않으므로 False
                "idempotentHint": True      # 동일 파라미터 호출 시 언제나 결과가 같으므로 True
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    """
    툴 호출 시 비즈니스 로직을 처리하고 가이드에 맞춰 컴팩트하게 응답합니다.
    """
    # [규칙] 툴 응답 속도는 평균 100ms 이내, p99 3,000ms 필수 (비동기 처리 최적화)
    if name == "fetch_product_trends":
        arguments = arguments or {}
        category = arguments.get("category", "all")
        limit = min(arguments.get("limit", 3), 5) # 무거운 호출 방지 제한
        
        # [규칙] result의 크기는 최소한으로 구성, API 응답 원본 그대로 사용 금지.
        # [규칙] 광고 노출 유도 금지 및 정제된 마크다운 텍스트 형식 권장.
        try:
            # 외부 API를 연동했다고 가정한 정제된 데이터 빌드
            trends_data = {
                "fashion": ["Minimalist Blazer", "Oversized Linen Shirt", "Retro Sneakers"],
                "electronics": ["Ergonomic Mechanical Keyboard", "Portable Projector", "GaN Charger"],
            }
            
            items = trends_data.get(category.lower(), ["Trending Item Alpha", "Trending Item Beta"])[:limit]
            
            # 마크다운 형태의 정제된 텍스트 응답 생성 (불필요한 메타데이터 전면 제거)
            markdown_output = f"### SmartStore(스마트스토어) [{category.upper()}] 인기 트렌드\n"
            for idx, item in enumerate(items, 1):
                markdown_output += f"{idx}. {item}\n"
            
            markdown_output += f"\n*기준: 실시간 데이터 반영 (상위 {limit}개 항목)*"
            
            return [TextContent(type="text", text=markdown_output)]
            
        except Exception as e:
            logger.error(f"Error executing tool: {str(e)}")
            # 에러 발생 시에도 API 오류 원본을 주지 않고 정제된 에러 마크다운 반환
            return [TextContent(type="text", text=f"⚠️ **트렌드 조회 실패:** {str(e)}")]
            
    raise ValueError(f"Unknown tool name: {name}")

# ==========================================
# 4. Remote MCP / Streamable HTTP (SSE) 라우팅
# ==========================================
@app.get("/health")
async def health_check():
    """서버 작동 여부 및 응답속도 보장을 위한 초경량 헬스체크"""
    return {"status": "UP", "stateless": True}

@app.get("/mcp")
async def sse_endpoint(request: Request):
    """PlayMCP 플랫폼의 연결 엔드포인트"""
    async with sse_transport.connect_scope(request.scope, request.receive, sse_transport.handle_sse):
        await asyncio.Event().wait()

@app.post("/messages")
async def messages_endpoint(request: Request, auth: str = Depends(verify_mcp_auth)):
    """PlayMCP가 전송하는 JSON-RPC 프로토콜 처리 엔드포인트"""
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)
    return {"status": "accepted"}

if __name__ == "__main__":
    import uvicorn
    # 외부 원격 접속을 허용하기 위해 host는 반드시 0.0.0.0 바인딩
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
