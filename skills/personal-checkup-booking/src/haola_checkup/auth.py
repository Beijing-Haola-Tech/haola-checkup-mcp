# -*- coding: utf-8 -*-
"""好啦体检 OAuth 登录：在本机完成一遍标准授权，把 token 存到本地。

为什么需要它：
    MCP 客户端（如 WorkBuddy）对「用户自己加的 MCP」不提供授权入口，
    收到 401 只会把错误抛回来。所以登录不能指望客户端，得由本脚本自己做：

    1. 起一个本地回调服务（127.0.0.1 随机端口）
    2. 动态注册一个 public client（redirect_uri 指向本机）
    3. 用浏览器打开**带完整参数的** authorize 地址
    4. 用户登录 → 浏览器跳回本机 → 拿到 code
    5. 换 access_token → 存 ~/.haola/token.json

之后 client 每次请求自动带 Authorization: Bearer。
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ISSUER = "https://ai.ihaola.com.cn"
RESOURCE = "https://ai.ihaola.com.cn/api/mcp/haola-pe"
SCOPE = "haola-pe"
# 动态注册时上报的客户端名。授权页「申请接入方」显示的就是它。
# 构建时按 skill 覆写（见 build.mjs），不要在运行时改。
CLIENT_NAME = "好啦体检 · 个人体检预约"
TOKEN_DIR = os.path.join(os.path.expanduser("~"), ".haola")
TOKEN_PATH = os.path.join(TOKEN_DIR, "token.json")

__all__ = ["login", "load_token", "logout", "TOKEN_PATH"]


def _post_json(url: str, payload: dict, timeout: int = 30) -> tuple[int, dict]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw}


def _post_form(url: str, payload: dict, timeout: int = 30) -> tuple[int, dict]:
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw}


def load_token() -> dict | None:
    """读本地 token。顺带做过期判断，过期返回 None。"""
    try:
        with open(TOKEN_PATH, encoding="utf-8") as f:
            t = json.load(f)
    except Exception:
        return None
    exp = t.get("expires_at")
    if exp and time.time() > float(exp) - 30:
        return None
    return t or None


def access_token() -> str | None:
    t = load_token()
    return t.get("access_token") if t else None


def logout() -> bool:
    try:
        os.remove(TOKEN_PATH)
        return True
    except FileNotFoundError:
        return False


def _pkce() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    result: dict = {}

    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        _CallbackHandler.result = {k: v[0] for k, v in qs.items()}
        ok = "code" in _CallbackHandler.result
        body = (
            "<!doctype html><meta charset='utf-8'>"
            "<div style='font-family:system-ui;padding:48px;text-align:center'>"
            + ("<h2>✅ 登录成功</h2><p>可以关掉这个页面，回到对话里继续。</p>"
               if ok else "<h2>❌ 登录失败</h2><p>没有拿到授权码，请重试。</p>")
            + "</div>"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass



def _open_small_window(url: str, width: int = 520, height: int = 840) -> bool:
    """用 Edge/Chrome 的 app 模式开一个小窗，别占满整个屏幕。

    url 只由本模块用 ISSUER 拼出来，不接受外部输入；这里再校验一次 origin，
    防止以后有人把用户输入拼进这个函数。
    subprocess 用参数列表调用（shell=False），不经过 shell 解释，没有命令注入面。
    找不到浏览器时退回系统默认方式（会是普通标签页）。
    """
    if not url.startswith(ISSUER + "/"):
        raise RuntimeError("拒绝打开不是本服务签发的地址")
    candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for exe in candidates:
        if exe and os.path.isfile(exe):
            try:
                subprocess.Popen(
                    [exe, "--app=" + url,
                     "--window-size=%d,%d" % (width, height),
                     "--window-position=200,80"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return True
            except Exception:
                continue
    try:
        import webbrowser
        webbrowser.open(url)
        return True
    except Exception:
        return False


def login(timeout: int = 300, open_browser: bool = True, quiet: bool = False) -> dict:
    """走一遍 OAuth，成功后把 token 写进 ~/.haola/token.json。"""
    port = _free_port()
    redirect_uri = f"http://127.0.0.1:{port}/callback"

    st, reg = _post_json(ISSUER + "/api/auth/oauth/register", {
        "client_name": CLIENT_NAME,
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    })
    if st not in (200, 201) or not reg.get("client_id"):
        raise RuntimeError(f"注册客户端失败：HTTP {st} {reg}")
    client_id = reg["client_id"]

    verifier, challenge = _pkce()
    state = secrets.token_urlsafe(16)
    auth_url = ISSUER + "/api/auth/oauth/authorize?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPE,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "resource": RESOURCE,
    })

    _CallbackHandler.result = {}
    srv = http.server.HTTPServer(("127.0.0.1", port), _CallbackHandler)
    # 必须持续监听：浏览器常会先请求 /favicon.ico，只处理一次会被它消耗掉，
    # 真正的 /callback 就会 connection refused。
    srv.timeout = 1
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()

    if not quiet:
        print("请在浏览器里完成登录（这个页面是能用的授权页，不是会报 resource 无效的那个）：")
        print(auth_url)
    if open_browser:
        _open_small_window(auth_url)

    deadline = time.time() + timeout
    while time.time() < deadline and not _CallbackHandler.result.get("code"):
        time.sleep(0.2)
    srv.shutdown()
    srv.server_close()
    got = _CallbackHandler.result
    if not got.get("code"):
        raise RuntimeError("没有拿到授权码：可能是超时，或授权页里没有完成登录。")
    if got.get("state") and got["state"] != state:
        raise RuntimeError("state 不匹配，可能被篡改，已中止。")

    token_payload = {
        "grant_type": "authorization_code",
        "code": got["code"],
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": verifier,
        # MCP 的 OAuth 实现通常要求 RFC 8707 资源指示符，换 token 时也要带
        "resource": RESOURCE,
    }
    st, tok = _post_form(ISSUER + "/api/auth/oauth/token", token_payload)
    if st != 200 or not tok.get("access_token"):
        raise RuntimeError("换 token 失败：HTTP %s %s\n请求参数（不含 code/verifier）：%s"
                         % (st, tok, {k: v for k, v in token_payload.items() if k not in ("code", "code_verifier")}))

    expires_in = tok.get("expires_in")
    out = {
        "access_token": tok["access_token"],
        "refresh_token": tok.get("refresh_token"),
        "token_type": tok.get("token_type", "Bearer"),
        "expires_at": int(time.time()) + int(expires_in) if expires_in else None,
        "client_id": client_id,
        "obtained_at": int(time.time()),
    }
    os.makedirs(TOKEN_DIR, exist_ok=True)
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out
