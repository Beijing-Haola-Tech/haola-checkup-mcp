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
        print(f"  模式         仅免登录工具（{len(ANONYMOUS_TOOLS)} 个）")
    return 0


def cmd_tools(args) -> int:
    with HaolaMCP(url=args.url) as mcp:
        tools = mcp.tools_list()
    print(f"可调用 {len(tools)} 个免登录工具\n")
    for t in tools:
        print(f"  {t['name']:<24}{_first_line(t.get('description', ''))}")
    print("\n需要登录的动作（个人方案 / 预约 / 订单 / 报告）请在网页完成：")
    print("  https://pe.ihaola.com.cn/auth/")
    return 0


def cmd_call(args) -> int:
    if args.name not in ANONYMOUS_TOOLS:
        print(f"`{args.name}` 不在允许范围内。", file=sys.stderr)
        print("这个动作需要在网页上登录后完成：https://pe.ihaola.com.cn/auth/", file=sys.stderr)
        print("可调用的工具：" + "、".join(sorted(ANONYMOUS_TOOLS)), file=sys.stderr)
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
        print("请在网页上登录后完成：https://pe.ihaola.com.cn/auth/", file=sys.stderr)
        return 3
    except MCPError as e:
        print(f"调用失败：{e}", file=sys.stderr)
        return 4


def cmd_quote(args) -> int:
    with HaolaMCP(url=args.url) as mcp:
        _dump(mcp.quote(args.budget, args.concerns, args.populations, args.tier))
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
