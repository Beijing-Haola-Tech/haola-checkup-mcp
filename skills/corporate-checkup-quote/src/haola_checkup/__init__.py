"""好啦体检 MCP 客户端（仅免登录工具）。"""

from .client import ANONYMOUS_TOOLS, DEFAULT_URL, PROTOCOL_VERSION, HaolaMCP, LoginRequired, MCPError

__all__ = [
    "HaolaMCP",
    "MCPError",
    "LoginRequired",
    "ANONYMOUS_TOOLS",
    "DEFAULT_URL",
    "PROTOCOL_VERSION",
]
__version__ = "1.0.2"
