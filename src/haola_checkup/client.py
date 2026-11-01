"""好啦体检 MCP 的零依赖客户端（Python 标准库实现）。

只做一件事：把 MCP Streamable HTTP 的握手、会话、SSE 解析包起来，
让 Skill 的脚本可以直接调用远端工具，不需要客户预先配置 MCP。

能力边界由下面这些值决定，构建时按 skill 覆写：

    USE_LOCAL_TOKEN         是否读取本机凭据（~/.haola/token.json）并附在请求头
    ENABLE_CORPORATE_QUOTE  是否提供企业团检报价
    ANONYMOUS_TOOLS         未登录时可调的工具
    ALLOWED_TOOLS           本 skill 的能力上限

登录只解锁「需要登录」的那部分工具，**不会让 ALLOWED_TOOLS 变大**。
企业版不读凭据，ALLOWED_TOOLS 与 ANONYMOUS_TOOLS 相同（9 个），没有扩张路径。
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
    "ALLOWED_TOOLS",
    "DEFAULT_URL",
    "PROTOCOL_VERSION",
]

DEFAULT_URL = "https://ai.ihaola.com.cn/api/mcp/haola-pe"
PROTOCOL_VERSION = "2025-06-18"

#: 凭据只发给这个 origin。把客户端指向别的地址时一律不带 Authorization，
#: 避免本机保存的 token 被送到第三方服务上（审计就这一点提过风险）。
TOKEN_ORIGIN = "https://ai.ihaola.com.cn"

# ---------------------------------------------------------------------------
# 本 skill 的能力边界。下面的值由构建脚本按 skill 覆写（见 build.mjs），
# 运行时不改：它们是本 skill 对外的承诺，安全审计会逐项核对声明与实现是否一致。
# ---------------------------------------------------------------------------

#: 是否读取本机凭据（~/.haola/token.json）。
#: 个人版 True；企业版 False —— 企业链路既不读凭据，也不往请求里放 Authorization 头。
USE_LOCAL_TOKEN = True

#: 是否提供企业团检报价（plan_quotation）。
#: 企业版 True；个人版 False。
ENABLE_CORPORATE_QUOTE = True

#: 未登录时允许调用的工具（构建时按 skill 覆写）。
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

#: 本 skill 允许调用的全部工具（构建时按 skill 覆写）。
#: 这是**上限**，登录只是拿到调用其中「需登录」那部分的资格，
#: 不存在「登录后白名单被放开」这种路径 —— 审计关心的正是这个区别。
ALLOWED_TOOLS = frozenset(
    {
        "vendor_list", "vendor_brands", "plan_quotation", "knowledge_get", "help", "faq",
        "progress_report", "corp_inquiry", "corp_contact", "plan_recommend", "order_list",
        "order_detail", "welfare_list", "welfare_detail", "cautions", "contact_list",
        "contact_get", "contact_create", "contact_update", "contact_profile_get",
        "contact_profile_save", "reservation_book", "reservation_cancel",
        "reservation_modify", "card_list",
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
    """当前没有可用登录态，而该工具需要登录。

    不是「客户端不参与」：本客户端会带凭据调用需要登录的工具，
    凭据来自本机的 `python scripts/haola.py login`。
    """


class HaolaMCP:
    """好啦体检 MCP 的最小客户端。

    能调哪些工具由模块级 ALLOWED_TOOLS 决定（构建时按 skill 写入）：
    个人版包含需要登录的工具，登录后即可调用；企业版只有免登录的 9 个。

    :param url:     MCP 端点，默认 https://ai.ihaola.com.cn/api/mcp/haola-pe
                    **凭据只发给这个官方 origin**，换成别的地址不会附带 token
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
        if USE_LOCAL_TOKEN and self.url.startswith(TOKEN_ORIGIN + "/"):
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
    def _allowed(name: str) -> bool:
        """这个工具是否在本 skill 的能力范围内。登录与否都受 ALLOWED_TOOLS 约束。"""
        return name in ALLOWED_TOOLS

    def ensure_ready(self) -> None:
        if not self._ready:
            self.initialize()

    def tools_list(self) -> list[dict]:
        """列出工具。

        只返回 ALLOWED_TOOLS 内的 —— 这是本 skill 的能力上限，登录后也不会变宽。
        未登录时进一步收窄到 ANONYMOUS_TOOLS（需要登录的那些暂时不可调）。
        """
        self.ensure_ready()
        tools = self._rpc("tools/list", {}).get("tools", [])
        logged = self._logged_in()
        return [
            t
            for t in tools
            if t.get("name") in ALLOWED_TOOLS and (logged or t.get("name") in ANONYMOUS_TOOLS)
        ]

    def call(self, name: str, arguments: dict | None = None) -> dict:
        """调用工具，返回工具自己输出的 JSON（已解开 MCP 的 content 包装）。

        两道门：先看是否在本 skill 的能力上限 ALLOWED_TOOLS 内（登录也不会变宽），
        再看是否需要登录而当前没有凭据。
        """
        if name not in ALLOWED_TOOLS:
            raise MCPError(
                f"`{name}` 不在本 skill 允许调用的范围内。",
                code="not_allowed",
            )
        if name not in ANONYMOUS_TOOLS and not HaolaMCP._logged_in():
            raise LoginRequired(
                f"`{name}` 需要先登录。在本机跑 `python scripts/haola.py login` 一次即可。",
                code="login_required",
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
