# 好啦体检 Skill · Haola Checkup Skill

> **跟 AI 说清预算和身体状况，直接出体检方案并完成预约。**
> Tell your agent a budget and a health concern — get a checkup plan and a booking.

[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](pyproject.toml)
[![Deps](https://img.shields.io/badge/dependencies-none-success)](#为什么没有依赖)
[![Tools](https://img.shields.io/badge/tools-25-green)](tools/tools.json)

---

## 这是什么

一个 **Agent Skill**：让 AI 能出体检方案、报价格、预约门店。

- **企业场景** —— 给一个人均预算，出全公司分档方案（男 / 女已婚 / 女未婚分开，价格到单项），返回 `planId`
- **个人场景** —— 给年龄、性别、症状、预算，出定制方案，返回 `planId`
- **两种都能直接预约** —— 把 `planId` 交给预约工具，在 240+ 城市、540+ 家已接入门店下单
- **还能查** 订单、体检件、检前注意事项

Skill 自带一个零依赖的 Python 客户端，运行时调用好啦体检的 MCP 服务（Streamable HTTP）。**用户不需要预先配置 MCP**，装好这个 Skill 就能用。

> 体检服务每年 10 万人次，健康测评累计 3500 万人次。合作体检机构 800+ 家，其中 540+ 家已接入 API 可被 AI 直接预约。

---

## 快速开始

```bash
# 1. 不用装，直接跑
python scripts/haola.py ping
python scripts/haola.py quote --budget 800 --concerns "久坐、三高、亚健康"

# 2. 或者装成包
pip install haola-checkup
haola-checkup tools
```

三行就能看到真实返回：

```
连接成功：https://ai.ihaola.com.cn/api/mcp/haola-pe
  session      0fe480f6-8622-45ff-8da5-8ba9deeeddba
  server       haola-pe 1.0.0
  protocol     2025-06-18
  鉴权         匿名
```

```bash
$ python scripts/haola.py quote --budget 800 --concerns "久坐、三高"
  man      798.36 元  20 项
  lady     779.93 元  19 项
  girl     798.35 元  19 项
```

---

## Agent 怎么用它

给 Agent 的完整契约在 **[`SKILL.md`](SKILL.md)** —— 什么情况下该用、什么时候不该用、四条主流程、三条回答规矩、错误对照表。

装进 Claude Code / Cursor / 其他支持 Agent Skills 的客户端时，把 `SKILL.md` 放在 skill 目录根部即可。

在代码里：

```python
from haola_checkup import HaolaMCP, AuthRequired

with HaolaMCP() as mcp:                      # 匿名
    result = mcp.quote(800, "久坐、三高")
    for p in result["data"]["list"][0]["planList"]:
        print(p["population"], p["price"], p["planId"])
```

---

## 端点与鉴权

```
https://ai.ihaola.com.cn/api/mcp/haola-pe
```

| | |
|---|---|
| 传输 | Streamable HTTP |
| 协议版本 | `2025-06-18` |
| 匿名可用 | 9 个工具 |
| 需登录 | 16 个工具（预约、订单、体检件、就诊人） |
| 鉴权方式 | OAuth 2.1 + PKCE，动态客户端注册（RFC 7591） |
| 发现机制 | `401` 带 `WWW-Authenticate`，指向受保护资源元数据（RFC 9728） |

本 Skill 的客户端**支持令牌透传**：拿到 token 后用 `HAOLA_TOKEN` 环境变量传入，或 `HaolaMCP(token=...)`。

OAuth 授权需要**手机号 + 短信验证码**，所以登录这一步必须有人参与。**匿名出方案和报价全程无需人工。**

遇到需要登录时，客户端抛 `AuthRequired`，并带上服务端给出的授权地址：

```
需要登录：HTTP 401: 该工具需要登录令牌。Unauthorized: authorization required
授权信息：https://ai.ihaola.com.cn/.well-known/oauth-protected-resource/api/mcp/haola-pe
```

---

## 工具

25 个。每个工具的描述都以 `[匿名可调用]` 或 `[需要登录]` 开头。

机器可读定义：[`tools/tools.json`](tools/tools.json)

| 分组 | 工具 |
|---|---|
| 方案与报价 | `plan_quotation`（企业，匿名）· `plan_recommend`（个人，需登录） |
| 门店 | `vendor_brands` · `vendor_list`（匿名） |
| 预约 | `reservation_book` · `reservation_modify` · `reservation_cancel` |
| 订单 | `order_list` · `order_detail` |
| 体检件 | `welfare_list` · `welfare_detail` |
| 就诊人 | `contact_list` · `contact_get` · `contact_create` · `contact_update` |
| 健康画像 | `contact_profile_get` · `contact_profile_save` |
| 其他 | `cautions` · `card_list` · `faq` · `knowledge_get` · `help` · `corp_inquiry` · `corp_contact` · `progress_report` |

---

## 为什么没有依赖

客户端只用标准库（`urllib` / `json`），原因：

1. **Skill 要在陌生环境里跑** —— 预装依赖是 Agent 场景最大的失败源
2. **MCP Streamable HTTP 的握手很薄** —— init 一次、带 `mcp-session-id`、解析 SSE 的 `data:` 行，就这些
3. **审计面小** —— 供应链风险为零，企业客户容易过审

---

## 目录结构

```
.
├── SKILL.md              # Agent 的契约（放 skill 目录根部）
├── README.md             # 本文件
├── pyproject.toml
├── scripts/
│   └── haola.py          # 免安装启动器
├── src/haola_checkup/
│   ├── client.py         # MCP Streamable HTTP 客户端
│   └── cli.py            # 命令行
├── tools/tools.json      # 25 个工具的定义
├── examples/             # curl / Cursor / Claude Desktop
└── llms.txt
```

---

## 开发

```bash
# 免安装直接跑
$env:PYTHONPATH="src"; python -m haola_checkup.cli tools

# 或
python scripts/haola.py quote --budget 800 --concerns "久坐"

# 打包（发 PyPI 前）
pip install build
python -m build
twine upload dist/*
```

---

## 相关

| | |
|---|---|
| 官网 | https://www.ihaola.com.cn/ |
| AI 入口 | https://www.ihaola.com.cn/llms.txt |
| 完整能力说明 | https://www.ihaola.com.cn/llms-full.txt |
| OpenAPI | https://www.ihaola.com.cn/openapi.json |
| 企业团检落地页 | https://www.ihaola.com.cn/html/mcp-quote.html |

---

## 边界与合规

- 好啦科技**不做保险产品、不做医疗服务**，是体检服务的方案与预约层；实际体检由合作机构提供，均持《医疗机构执业许可证》
- 体检报告以结构化方式交付，**企业侧只能看到授权后的脱敏汇总，看不到任何个人体检结果**
- 国家等保三级 · ISO 27001 · ISO 9001 · 国家高新技术企业 · 北京市专精特新
- 本仓库是**客户端与文档**，不含用户数据，也不含服务端源码

---

## License

[MIT](LICENSE) — 覆盖本仓库的客户端代码、文档与示例。托管服务本身由北京好啦科技有限公司依单独的服务条款运营。

北京好啦科技有限公司 · Haola Tech · contacts@haola.com
