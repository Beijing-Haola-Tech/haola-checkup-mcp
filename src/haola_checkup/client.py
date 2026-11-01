"""好啦体检 MCP 的零依赖客户端（Python 标准库实现）。

只做一件事：把 MCP Streamable HTTP 的握手、会话、SSE 解析包起来，
让 Skill 的脚本可以直接调用远端工具，不需要客户预先配置 MCP。

能力边界由下面三个模块级开关决定，构建时按 skill 覆写：

    USE_LOCAL_TOKEN                 是否读取本机凭据（~/.haola/token.json）
    RELAX_ALLOWLIST_WHEN_LOGGED_IN  有凭据时是否放开白名单
    ENABLE_CORPORATE_QUOTE          是否提供企业团检报价

个人版：三个都 True，登录后可用全部工具。
企业版：后两个为 False，且不读凭据 —— 本机存着个人 token 也不会扩大企业链路的能力，
        它永远只能调用企业白名单里的工具。

白名单本身见 ANONYMOUS_TOOLS，也是构建时写入的。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

__all__ = [
    "HaolaMCP",
    "MCPError",
    "LoginRequired",
    "ANONYMOUS_TOOLS",
    "DEFAULT_URL",
    "PROTOCOL_VERSION",
]

DEFAULT_URL = "https://ai.ihaola.com.cn/api/mcp/haola-pe"
PROTOCOL_VERSION = "2025-06-18"

# ---------------------------------------------------------------------------
# 本 skill 的能力边界。三个开关由构建脚本按 skill 覆写（见 build.mjs），
# 运行时不改：它们是本 skill 对外的承诺，安全审计会逐项核对实现与声明是否一致。
# ---------------------------------------------------------------------------

#: 是否读取本机凭据（~/.haola/token.json）。
#: 个人版 True —— 登录一次，之后可用需要登录的工具。
#: 企业版 False —— 企业链路全程免登录，既不读取也不使用个人凭据。
USE_LOCAL_TOKEN = True

#: 已有凭据时是否放开 ANONYMOUS_TOOLS 白名单。
#: 个人版 True —— 登录后全部工具可用。
#: 企业版 False —— 即使本机存着个人凭据，也仍只放行企业白名单内的工具。
RELAX_ALLOWLIST_WHEN_LOGGED_IN = True

#: 是否提供企业团检报价（plan_quotation）。
#: 企业版 True；个人版 False —— 个人场景不做团检报价。
ENABLE_CORPORATE_QUOTE = True

#: 客户端被允许调用的工具白名单，构建时按 skill 覆写。
ANONYMOUS_TOOLS = frozenset(
    {
        "plan_quotation",
        "vendor_brands",
        "vendor_list",
        "knowledge_get",
        "faq",
        "corp_inquiry",
        "corp_contact",
        "help",
        "progress_report",
    }
)


class MCPError(RuntimeError):
    """JSON-RPC 层或传输层返回的错误。"""

    def __init__(self, message: str, code: int | None = None, data=None, status: int | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data
        self.status = status

    def __str__(self) -> str:
        bits = []
        if self.status is not None:
            bits.append(f"HTTP {self.status}")
        if self.code is not None:
            bits.append(f"code {self.code}")
        head = " / ".join(bits)
        return f"{head}: {self.message}" if head else self.message


class LoginRequired(MCPError):
    """该动作要在网页上登录后完成，客户端不参与。"""


class HaolaMCP:
    """好啦体检 MCP 的最小客户端（仅免登录工具）。

    :param url:     MCP 端点，默认 https://ai.ihaola.com.cn/api/mcp/haola-pe
    :param timeout: 单次请求超时秒数
    """

    def __init__(
        self,
        url: str = DEFAULT_URL,
        timeout: int = 60,
        client_name: str = "haola-checkup-skill",
        client_version: str = "1.0.2",
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.client_name = client_name
        self.client_version = client_version

        self.session_id: str | None = None
        self.server_info: dict | None = None
        self._next_id = 0
        self._ready = False

    # ---------------------------------------------------------------- 底层传输

    def _headers(self) -> dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            h["mcp-session-id"] = self.session_id
        try:
            from . import auth as _auth
            tok = _auth.access_token()
        except Exception:
            tok = None
        if tok:
            h["Authorization"] = "Bearer " + tok
        return h

    def _post(self, payload: dict) -> dict | None:
        """发一个 JSON-RPC 包，返回解析后的响应（通知类返回 None）。"""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self.url, data=body, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                sid = resp.headers.get("mcp-session-id")
                if sid:
                    self.session_id = sid
                raw = resp.read().decode("utf-8", "replace")
                return self._parse(raw)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            msg = self._extract_error_message(raw) or e.reason or "request failed"
            if e.code == 401:
                raise LoginRequired("需要登录后才能调用。在本机跑 `python scripts/haola.py login` 登录一次即可。", status=401) from None
            raise MCPError(msg, status=e.code) from None

    @staticmethod
    def _extract_error_message(raw: str) -> str | None:
        try:
            obj = json.loads(raw)
        except Exception:
            return raw.strip()[:300] or None
        err = obj.get("error")
        if isinstance(err, dict):
            return err.get("message")
        if isinstance(err, str):
            return err
        return obj.get("message")

    @staticmethod
    def _parse(raw: str) -> dict | None:
        """服务端可能返回纯 JSON，也可能返回 SSE（每行 `data: ...`）。"""
        text = raw.strip()
        if not text:
            return None
        if not text.startswith(("data:", "event:")):
            return json.loads(text)

        payloads = []
        buf = []
        for line in text.splitlines():
            if line.startswith("data:"):
                buf.append(line[5:].lstrip())
            elif not line.strip():
                if buf:
                    payloads.append("\n".join(buf))
                    buf = []
        if buf:
            payloads.append("\n".join(buf))

        result = None
        for p in payloads:
            if not p.strip():
                continue
            try:
                obj = json.loads(p)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("id") is not None:
                result = obj
        return result

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        payload = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            payload["params"] = params
        obj = self._post(payload)
        if obj is None:
            raise MCPError(f"服务端对 {method} 返回了空响应")
        if "error" in obj and obj["error"]:
            err = obj["error"]
            if isinstance(err, dict):
                raise MCPError(err.get("message", "unknown"), code=err.get("code"), data=err.get("data"))
            raise MCPError(str(err))
        return obj.get("result", obj)

    def _notify(self, method: str, params: dict | None = None) -> None:
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        try:
            self._post(payload)
        except MCPError:
            pass

    # ---------------------------------------------------------------- 公开接口

    def initialize(self) -> dict:
        result = self._rpc(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": self.client_name, "version": self.client_version},
            },
        )
        self.server_info = result
        self._notify("notifications/initialized")
        self._ready = True
        return result

    @staticmethod
    def _logged_in() -> bool:
        """本机是否有可用凭据。企业版不读凭据，恒为 False。"""
        if not USE_LOCAL_TOKEN:
            return False
        try:
            from . import auth as _auth
            return bool(_auth.access_token())
        except Exception:
            return False

    @staticmethod
    def _allows_all() -> bool:
        """当前是否放开白名单：只有「个人版 + 已有凭据」才放开。"""
        return bool(RELAX_ALLOWLIST_WHEN_LOGGED_IN) and HaolaMCP._logged_in()

    def ensure_ready(self) -> None:
        if not self._ready:
            self.initialize()

    def tools_list(self) -> list[dict]:
        """列出工具。

        未放开白名单时只返回 ANONYMOUS_TOOLS 内的工具；个人版登录后返回全部。
        放不放开只看 _allows_all()，与这段文档说的是同一件事。
        """
        self.ensure_ready()
        tools = self._rpc("tools/list", {}).get("tools", [])
        if HaolaMCP._allows_all():
            return tools
        return [t for t in tools if t.get("name") in ANONYMOUS_TOOLS]

    def call(self, name: str, arguments: dict | None = None) -> dict:
        """调用工具，返回工具自己输出的 JSON（已解开 MCP 的 content 包装）。

        白名单外的工具只在 _allows_all() 为真时放行：个人版登录后可以，企业版永远不行。
        """
        if name not in ANONYMOUS_TOOLS and not HaolaMCP._allows_all():
            raise MCPError(
                f"`{name}` 不在本 skill 允许调用的范围内。",
                code="not_allowed",
            )
        self.ensure_ready()
        result = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})

        content = result.get("content") or []
        text = ""
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text += item.get("text", "")

        payload: dict | None = None
        if text:
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = None

        if result.get("isError"):
            msg = (payload or {}).get("message") if isinstance(payload, dict) else None
            raise MCPError(msg or text or f"{name} 调用失败")

        if isinstance(payload, dict) and payload.get("code") not in (None, 200):
            raise MCPError(
                payload.get("message", "业务错误"),
                code=payload.get("code"),
                data=payload.get("data"),
            )

        return payload if payload is not None else {"raw": text}

    def quote(self, budget: int, concerns: str, populations=("man", "lady", "girl"), tier: str = "员工档") -> dict:
        """企业团检报价（免登录）。

        只有 ENABLE_CORPORATE_QUOTE 为真的 skill（企业版）才提供这个方法；
        个人版调用会直接拒绝，避免把团检报价能力带进个人场景。
        """
        if not ENABLE_CORPORATE_QUOTE:
            raise MCPError(
                "个人版不做企业团检报价，请使用 corporate-checkup-quote 技能。",
                code="not_allowed",
            )
        return self.call(
            "plan_quotation",
            {"quotes": [{"tier": tier, "budget": budget,
                         "healthConcerns": concerns, "populations": list(populations)}]},
        )

    def __enter__(self) -> "HaolaMCP":
        self.ensure_ready()
        return self

    def __exit__(self, *exc) -> None:
        return None
