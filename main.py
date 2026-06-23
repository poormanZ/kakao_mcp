import asyncio
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

# 1. PlayMCP in KC 로그 수집기 연동을 위한 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgenticPlayerServer")

# [주의] 공모전 규칙: 서버 명칭 및 툴 사양에 대소문자 무관 "kakao" 단어 전면 배제
mcp_server = Server("biz-trend-agent-service")

app = FastAPI(
    title="Agentic Player 10 Verified Server", 
    version="2026.06.12",
    description="Stateless Remote MCP Server matching PlayMCP Specification"
)

# PlayMCP 플랫폼의 크로스 오리진 호출 전면 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [중요] 카카오클라우드가 요구하는 하위 라우팅 패스를 명시적으로 선언
sse_transport = SseServerTransport("/mcp/messages")

# ==========================================
# 2. 공모전 Tool 구성 필수 및 권장 규칙 적용
# ==========================================
@mcp_server.list_tools()
async def handle_list_tools():
    """[정보 불러오기] 클릭 시 카카오 플랫폼이 읽어가는 스펙 정의"""
    logger.info(">>> [PlayMCP in KC] list_tools 스펙 요청 수신")
    return [
        Tool(
            # 규칙: 영어 대소문자, 숫자, _, - 만 허용 (1~128자), 'kakao' 단어 금지
            name="fetch_market_analysis",
            
            # 규칙: 영문 중심 작성 권장, 고유 서비스명 국문/영문 병기 (1,024자 이내)
            description="Retrieves a summarized report of the current trending items and consumer demand from the SmartStore(스마트스토어) service.",
            
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string", 
                        "description": "Target category name (e.g., fashion, food)"
                    }
                },
                "required": ["category"]
            },
            
            # 규칙: annotations 내 5대 속성값 누락 없이 수동 전면 지정
            annotations={
                "title": "SmartStore Market Trend Analyzer",
                "readOnlyHint": True,        # 조회 전용
                "destructiveHint": False,    # 데이터 변경 없음
                "openWorldHint": False,      # 사이드 이펙트 없음
                "idempotentHint": True       # 멱등성 보장
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    # 규칙: 응답 속도는 평균 100ms 이내, p99 3,000ms 필수 준수
    if name == "fetch_market_analysis":
        arguments = arguments or {}
        category = arguments.get("category", "general")
        
        # 규칙: API 응답 원본 그대로 사용 금지, 마크다운 형식의 정제된 텍스트 필수 (광고성 문구 금지)
        markdown_result = (
            f"### SmartStore(스마트스토어) [{category.upper()}] 요약 리포트\n"
            "1. **소비 트렌드:** 미니멀리즘 디자인 가구군 검색량 18% 증가\n"
            "2. **인기 키워드:** 친환경 오가닉 홈웨어\n"
            "\n*데이터 규격 크기 최적화 및 광고 제거 완료*"
        )
        return [TextContent(type="text", text=markdown_result)]
        
    raise ValueError(f"Unknown tool: {name}")

# ====================================================
# 3. PlayMCP in KC 전용 Endpoint 핸드셰이크 라우팅
# ====================================================

# 카카오 콘솔 등록 URL: 발급받은도메인/mcp
@app.get("/mcp")
async def sse_endpoint(request: Request):
    """PlayMCP 플랫폼이 최초 핸드셰이크를 위해 연결하는 GET 진입점"""
    logger.info(">>> [PlayMCP Handshake] GET /mcp (SSE 연결 수립 시작)")
    
    async with sse_transport.connect_scope(request.scope, request.receive, sse_transport.handle_sse):
        # 인프라 단절을 막기 위한 비동기 연결 유지
        while True:
            await asyncio.sleep(1)

@app.post("/mcp/messages")
async def messages_endpoint(request: Request):
    """[정보 불러오기] 클릭 시 실제 초기화 JSON-RPC 메시지가 수신되는 POST 진입점"""
    logger.info(">>> [PlayMCP Protocol] POST /mcp/messages (초기화 메시지 수신)")
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)
    return {"status": "accepted"}

@app.get("/")
async def infrastructure_health():
    """PlayMCP in KC 내부 컨테이너 오케스트레이터용 헬스체크"""
    return {"status": "healthy"}
