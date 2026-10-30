"""好啦体检 MCP 客户端。"""

from .client import AuthRequired, DEFAULT_URL, PROTOCOL_VERSION, HaolaMCP, MCPError

__all__ = ["HaolaMCP", "MCPError", "AuthRequired", "DEFAULT_URL", "PROTOCOL_VERSION"]
__version__ = "0.1.0"
