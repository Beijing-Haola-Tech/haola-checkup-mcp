"""好啦体检 MCP 的零依赖客户端（Python 标准库实现）。

只做一件事：把 MCP Streamable HTTP 的握手、会话、SSE 解析包起来，
让 Skill 的脚本可以直接调用远端工具，不需要客户预先配置 MCP。

用法::

    from haola_checkup import HaolaMCP

    mcp = HaolaMCP()
    plans = mcp.call("plan_quotation", {
        "quotes": [{"tier": "员工档", "budget": 800,
                    "healthConcerns": "久坐、三高"}]
    })

设计取舍：
    - 只用标准库（urllib / json），pip install 之后没有任何额外依赖
    - 需要登录的工具用 bearer token 透传；OAuth 授权交给用户的 MCP 客户端，
      或在环境变量 HAOLA_TOKEN 里放一个现成 token
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

__all__ = ["HaolaMCP", "MCPError", "AuthRequired", "DEFAULT_URL", "PROTOCOL_VERSION"]

DEFAULT_URL = "https://ai.ihaola.com.cn/api/mcp/haola-pe"
PROTOCOL_VERSION = "2025-06-18"


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


class AuthRequired(MCPError):
    """需要登录令牌。附带服务端给出的授权地址，便于引导用户。"""

    def __init__(self, message: str, resource_metadata: str | None = None, **kw):
        super().__init__(message, **kw)
        self.resource_metadata = resource_metadata


class HaolaMCP:
    """好啦体检 MCP 的最小客户端。

    :param url:   MCP 端点，默认 https://ai.ihaola.com.cn/api/mcp/haola-pe
    :param token: 用户令牌；优先级 参数 > 环境变量 HAOLA_TOKEN > 无（匿名）
    :param timeout: 单次请求超时秒数
    """

    def __init__(
        self,
        url: str = DEFAULT_URL,
        token: str | None = None,
        timeout: int = 60,
        client_name: str = "haola-checkup-skill",
        client_version: str = "0.1.0",
    ) -> None:
        self.url = url
        self.token = token or os.environ.get("HAOLA_TOKEN") or None
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
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
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
            www = e.headers.get("WWW-Authenticate") if e.headers else None
            msg = self._extract_error_message(raw) or e.reason or "request failed"
            if e.code == 401:
                raise AuthRequired(
                    f"该工具需要登录令牌。{msg}",
                    resource_metadata=self._resource_metadata(www),
                    status=401,
                ) from None
            raise MCPError(msg, status=e.code) from None

    @staticmethod
    def _resource_metadata(www_authenticate: str | None) -> str | None:
        if not www_authenticate:
            return None
        marker = 'resource_metadata="'
        i = www_authenticate.find(marker)
        if i < 0:
            return None
        start = i + len(marker)
        end = www_authenticate.find('"', start)
        return www_authenticate[start:end] if end > start else None

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
            # 通知是一等公民之外的礼貌动作，失败不该中断主流程
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

    def ensure_ready(self) -> None:
        if not self._ready:
            self.initialize()

    def tools_list(self) -> list[dict]:
        self.ensure_ready()
        return self._rpc("tools/list", {}).get("tools", [])

    def call(self, name: str, arguments: dict | None = None) -> dict:
        """调用一个工具，返回工具自己输出的 JSON（已解开 MCP 的 content 包装）。"""
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

    # 便捷方法：最容易用到的两条路径

    def quote(self, budget: int, concerns: str, populations=("man", "lady", "girl"), tier: str = "员工档") -> dict:
        """企业团检报价（匿名可用）。"""
        return self.call(
            "plan_quotation",
            {"quotes": [{"tier": tier, "budget": budget,
                         "healthConcerns": concerns, "populations": list(populations)}]},
        )

    def recommend(self, gender: str, age: int | None = None, budget: int | None = None,
                  complaint: str | None = None) -> dict:
        """个人定制方案（需要登录令牌）。"""
        args: dict = {"gender": gender}
        if age is not None:
            args["age"] = age
        if budget is not None:
            args["budget"] = budget
        if complaint:
            args["mainComplaint"] = complaint
        return self.call("plan_recommend", args)

    def __enter__(self) -> "HaolaMCP":
        self.ensure_ready()
        return self

    def __exit__(self, *exc) -> None:
        return None
