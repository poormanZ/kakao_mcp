import asyncio
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PlayMcpServer")

app = FastAPI(title="PlayMCP Agentic Contest Server", version="2026.06.12")

# PlayMCP 플랫폼 교차 출처 에러(CORS) 방지
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================================================
# [가이드라인 100% 매핑] 카카오 검증기가 수집해갈 Tool 정의
# ====================================================
PLAYMCP_TOOLS = [
    {
        # 규칙 1: 영어 대소문자, 숫자, _, - 만 허용 (1~128자) / "kakao" 단어 전면 금지
        "name": "fetch_market_insights",
        
        # 규칙 2: 영문 중심 작성 권장, 고유 서비스명 국문/영문 병기 (1,024자 이내)
        "description": "Retrieves summarized consumer market insights and search volume trends from the SmartStore(스마트스토어) service.",
        
        "inputSchema": {
            "type": "object",
            "properties": {
                "trend_type": {
                    "type": "string",
                    "description": "The period type of trend, such as daily or weekly"
                }
            },
            "required": ["trend_type"]
        },
        
        # 규칙 3: annotations 5대 필수 속성값 누락 없이 수동 전면 지정 (★가장 중요)
        "annotations": {
            "title": "SmartStore Insight Viewer",
            "readOnlyHint": True,
            "destructiveHint": False,
            "openWorldHint": False,
            "idempotentHint": True
        }
    }
]

# ====================================================
# PlayMCP Endpoint 라우팅 매핑 (Streamable HTTP / SSE)
# ====================================================

@app.get("/mcp")
async def sse_endpoint(request: Request):
    """PlayMCP 플랫폼이 최초 연결(Handshake)을 위해 진입하는 GET 엔드포인트"""
    logger.info(">>> [PlayMCP] GET /mcp (SSE 연결 수립)")
    
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"
    }
    
    async def event_generator():
        yield "data: {\"type\": \"ping\"}\n\n"
        while True:
            await asyncio.sleep(1)
            yield ": keepalive\n\n"

    return StreamingResponse(event_generator(), headers=headers)


@app.post("/mcp/messages")
async def messages_endpoint(request: Request):
    """[정보 불러오기] 클릭 시 초기화 프로토콜 및 툴 목록을 전송하는 핵심 포트"""
    body = await request.json()
    msg_id = body.get("id")
    method = body.get("method")
    
    logger.info(f">> [PlayMCP 수신] method: {method}, id: {msg_id}")
    
    # 1. 초기화 핸드셰이크 규격 처리 (가이드 명시 최소 지원버전 2025-03-26 대응)
    if method == "initialize":
        response_data = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "biz-intelligence-service",
                    "version": "1.0.0"
                }
            }
        }
        return JSONResponse(content=response_data)
        
    # 2. 툴 리스트 조회 프로토콜 처리 (여기에 올바른 데이터를 줘야 '지원 Tools'가 채워집니다)
    elif method == "tools/list" or body.get("params", {}).get("method") == "tools/list":
        response_data = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": PLAYMCP_TOOLS
            }
        }
        return JSONResponse(content=response_data)
    
    # 3. 실제 툴 실행 요청 처리 (결과는 광고 없이 정제된 마크다운 텍스트 권장)
    elif method == "tools/call":
        markdown_text = "### SmartStore(스마트스토어) 시장 트렌드 결과\n- 가이드라인 표준 규격 정제 완료."
        response_data = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [{"type": "text", "text": markdown_text}]
            }
        }
        return JSONResponse(content=response_data)

    return JSONResponse(content={"jsonrpc": "2.0", "id": msg_id, "result": {}})

@app.get("/")
async def health():
    return {"status": "healthy"}
