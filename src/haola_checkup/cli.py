"""命令行入口：haola-checkup <子命令>

只提供免登录能力：报价、门店、FAQ、领域知识、企业咨询。
需要登录的动作（个人方案、预约、订单、报告）请在网页上完成。
"""

from __future__ import annotations

import argparse
import json
import sys

from .client import ANONYMOUS_TOOLS, DEFAULT_URL, HaolaMCP, LoginRequired, MCPError


def _force_utf8() -> None:
    """Windows 控制台默认 cp936，中文会乱码。统一改成 UTF-8。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def _dump(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _first_line(text: str, limit: int = 70) -> str:
    text = (text or "").strip().replace("\n", " ")
    cut = text.split("。")[0]
    if len(cut) > limit:
        cut = cut[:limit] + "…"
    return cut


def cmd_ping(args) -> int:
    with HaolaMCP(url=args.url) as mcp:
        info = mcp.server_info or {}
        server = info.get("serverInfo", {})
        print(f"连接成功：{args.url}")
        print(f"  session      {mcp.session_id}")
        print(f"  server       {server.get('name', '?')} {server.get('version', '')}".rstrip())
        print(f"  protocol     {info.get('protocolVersion', '?')}")
        from . import auth as _auth
        if _auth.access_token():
            print("  模式         已登录（白名单已放开，全部工具可调）")
        else:
            print(f"  模式         未登录，仅免登录工具（{len(ANONYMOUS_TOOLS)} 个）")
    return 0


def cmd_tools(args) -> int:
    from . import auth as _auth

    with HaolaMCP(url=args.url) as mcp:
        tools = mcp.tools_list()
    logged = bool(_auth.access_token())
    print(f"可调用 {len(tools)} 个工具" + ("" if logged else "（未登录，只剩免登录工具）") + "\n")
    for t in tools:
        print(f"  {t['name']:<24}{_first_line(t.get('description', ''))}")
    if logged:
        print("\n已登录：个人方案、预约、订单、报告都可以直接调用。")
    else:
        print("\n需要登录的动作（个人方案 / 预约 / 订单 / 报告）：先跑 python scripts/haola.py login")
    return 0


def cmd_call(args) -> int:
    from . import auth as _auth

    logged_in = bool(_auth.access_token())
    if args.name not in ANONYMOUS_TOOLS and not logged_in:
        print(f"`{args.name}` 需要先登录。", file=sys.stderr)
        print("在这个目录下跑一次：python scripts/haola.py login", file=sys.stderr)
        print("可免登录调用的工具：" + "、".join(sorted(ANONYMOUS_TOOLS)), file=sys.stderr)
        return 5

    try:
        arguments = json.loads(args.json) if args.json else {}
    except json.JSONDecodeError as e:
        print(f"参数不是合法 JSON：{e}", file=sys.stderr)
        return 2

    try:
        with HaolaMCP(url=args.url) as mcp:
            _dump(mcp.call(args.name, arguments))
        return 0
    except LoginRequired as e:
        print(f"{e}", file=sys.stderr)
        print("在这台机器上跑一次：python scripts/haola.py login", file=sys.stderr)
        return 3
    except MCPError as e:
        print(f"调用失败：{e}", file=sys.stderr)
        return 4


def cmd_quote(args) -> int:
    with HaolaMCP(url=args.url) as mcp:
        _dump(mcp.quote(args.budget, args.concerns, args.populations, args.tier))
    return 0


def cmd_login(args) -> int:
    import time
    from . import auth

    try:
        tok = auth.login(timeout=args.timeout, open_browser=not args.no_browser)
    except Exception as e:
        print("登录失败：" + str(e))
        return 1

    print("登录成功，凭据已存到 " + auth.TOKEN_PATH)
    exp = tok.get("expires_at")
    if exp:
        left = max(0, int(exp - time.time()))
        if left >= 86400:
            span = "%d 天" % (left // 86400)
        elif left >= 3600:
            span = "%d 小时" % (left // 3600)
        else:
            span = "%d 分钟" % max(1, left // 60)
        print("  有效期约 %s，过期后重新跑一次 login 即可" % span)
    return 0


def cmd_logout(args) -> int:
    from . import auth
    print("已清除本地凭据" if auth.logout() else "本地没有凭据")
    return 0


def cmd_whoami(args) -> int:
    from . import auth
    t = auth.load_token()
    if not t:
        print("未登录")
        return 1
    print("已登录，凭据文件：", auth.TOKEN_PATH)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="haola-checkup",
        description="好啦体检 MCP 命令行（仅免登录工具：报价、门店、FAQ、知识、企业咨询）",
    )
    p.add_argument("--url", default=DEFAULT_URL, help=f"MCP 端点，默认 {DEFAULT_URL}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("ping", help="测试连通性")
    sp.set_defaults(func=cmd_ping)

    sp = sub.add_parser("tools", help="列出可调用的免登录工具")
    sp.set_defaults(func=cmd_tools)

    sp = sub.add_parser("call", help="调用一个免登录工具")
    sp.add_argument("name", help="工具名，须在白名单内")
    sp.add_argument("json", nargs="?", default="", help='参数 JSON，如 \'{"city":"北京"}\'')
    sp.set_defaults(func=cmd_call)

    sp = sub.add_parser("login", help="打开浏览器登录一次，之后自动带凭据")
    sp.add_argument("--timeout", type=int, default=300)
    sp.add_argument("--no-browser", action="store_true", help="只打印链接，不自动打开")
    sp.set_defaults(func=cmd_login)

    sp = sub.add_parser("logout", help="清除本地凭据")
    sp.set_defaults(func=cmd_logout)

    sp = sub.add_parser("whoami", help="查看是否已登录")
    sp.set_defaults(func=cmd_whoami)

    # 只有白名单里包含 plan_quotation 的场景（企业版）才注册这个子命令
    if "plan_quotation" in ANONYMOUS_TOOLS:
        sp = sub.add_parser("quote", help="企业团检报价")
        sp.add_argument("--budget", type=int, required=True, help="人均预算，元")
        sp.add_argument("--concerns", required=True, help="健康关注，如 久坐、三高")
        sp.add_argument("--tier", default="员工档")
        sp.add_argument("--populations", nargs="+", default=["man", "lady", "girl"])
        sp.set_defaults(func=cmd_quote)

    return p


def main(argv: list[str] | None = None) -> int:
    _force_utf8()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
