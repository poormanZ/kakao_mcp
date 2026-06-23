from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test-mcp-server")

@mcp.tool()
def hello(name: str) -> str:
    """이름을 받아 인사말을 반환합니다."""
    return f"안녕하세요, {name}님! 테스트 MCP 서버입니다."

@mcp.tool()
def add(a: float, b: float) -> float:
    """두 숫자를 더합니다."""
    return a + b

@mcp.tool()
def get_info() -> dict:
    """서버 정보를 반환합니다."""
    return {
        "name": "test-mcp-server",
        "version": "1.0.0",
        "description": "PlayMCP 테스트용 MCP 서버",
        "tools": ["hello", "add", "get_info"]
    }

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080, path="/mcp")
