"""好啦体检 MCP 客户端。

能力边界由 client.py 的 ALLOWED_TOOLS / ANONYMOUS_TOOLS / USE_LOCAL_TOKEN 决定，
构建时按 skill 写入，运行时不变。
"""

from .client import (
    ALLOWED_TOOLS,
    ANONYMOUS_TOOLS,
    DEFAULT_URL,
    PROTOCOL_VERSION,
    HaolaMCP,
    LoginRequired,
    MCPError,
)

__all__ = [
    "HaolaMCP",
    "MCPError",
    "LoginRequired",
    "ANONYMOUS_TOOLS",
    "ALLOWED_TOOLS",
    "DEFAULT_URL",
    "PROTOCOL_VERSION",
]
__version__ = "1.1.0"
