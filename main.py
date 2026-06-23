from mcp.server.fastmcp import FastMCP

# PlayMCP 가이드 준수:
# - 서버명/툴명에 "kakao" 포함 불가 (대소문자 무관)
# - Streamable HTTP 방식 필수
# - Stateless 권장
mcp = FastMCP(
    name="music-trend-service-server",
    host="0.0.0.0",
    port=8000,
    stateless_http=True,   # PlayMCP 가이드: Stateless 권장
)

@mcp.tool(
    # 1. 툴 이름: 영문/숫자/_ 만 허용, "kakao" 포함 불가
    name="get_trending_music",

    # 2. description: 영문 권장, 서비스명 국/영문 병기, 1024자 이내
    description=(
        "Retrieves a list of the current most popular or trending songs "
        "from Melon(멜론) service."
    ),
    # 3. annotations: 5대 요소 모두 지정 필수
    annotations={
        "title": "Melon Trending Music Retriever",
        "readOnlyHint": True,       # 데이터 조회만, 변경 없음
        "destructiveHint": False,   # 데이터 파괴 없음
        "openWorldHint": False,     # 외부 상태 변경 없음
        "idempotentHint": True,     # 멱등성 만족
    },
)
def get_trending_music(count: int) -> str:
    """
    Melon(멜론) 실시간 트렌드 음악을 조회합니다.

    Args:
        count: 조회할 곡 수 (1-10)
    """
    # PlayMCP 가이드: result 크기 최소화, 정제된 마크다운 형식 권장
    count = max(1, min(count, 10))  # 1~10 범위 보정

    markdown_result = (
        "### Melon(멜론) 실시간 트렌드 TOP 3\n"
        "1. **Song A** - Artist X\n"
        "2. **Song B** - Artist Y\n"
        "3. **Song C** - Artist Z\n"
        f"\n*조회된 개수: {count}개*"
    )
    return markdown_result


if __name__ == "__main__":
    # PlayMCP 가이드: Streamable HTTP 방식만 지원
    mcp.run(transport="streamable-http")
