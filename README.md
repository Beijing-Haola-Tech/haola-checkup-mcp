# 好啦体检 MCP · Haola Checkup MCP

> **Tell your agent a budget and a health concern — get a checkup plan and a booking, in one conversation.**
> 跟你的 AI 说清预算和身体状况，直接出体检方案并完成预约。

[![MCP](https://img.shields.io/badge/MCP-Streamable%20HTTP-blue)](https://modelcontextprotocol.io)
[![Tools](https://img.shields.io/badge/tools-25-green)](#tools)
[![Auth](https://img.shields.io/badge/auth-OAuth%202.1%20%2B%20PKCE-orange)](#authentication)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

---

## What this is

A **remote MCP server** operated by 北京好啦科技有限公司 (Haola Tech). It lets an AI agent:

- **企业场景** — 给一个人均预算，出全公司分档体检方案（男 / 女已婚 / 女未婚分开列，价格到单项），返回 `planId`
- **个人场景** — 给年龄、性别、症状、预算，出定制方案，返回 `planId`
- **两个场景都能直接预约** — 把 `planId` 交给 `reservation_book`，在 240+ 城市的 540+ 家已接入门店下单
- **查订单、查体检件、查报告、查检前注意事项**

体检服务每年 10 万人次，健康测评累计 3500 万人次，合作体检机构 800+ 家（其中 540+ 家已接入 API 可被 AI 直接预约）。

> **This is a hosted service, not a local one.** The MCP server runs at `ai.ihaola.com.cn`; you do not host or build anything. There is no bundled data and no local install. Clients that only speak stdio can bridge to it with [`mcp-remote`](#clients-that-only-support-stdio).

---

## Endpoint

```
https://ai.ihaola.com.cn/api/mcp/haola-pe
```

| | |
|---|---|
| Transport | Streamable HTTP |
| Protocol version | `2025-06-18` |
| Auth (anonymous) | 9 tools work with no credentials |
| Auth (private) | OAuth 2.1 + PKCE, dynamic client registration (RFC 7591) |
| Discovery | `401` returns `WWW-Authenticate: Bearer resource_metadata="…/.well-known/oauth-protected-resource/api/mcp/haola-pe"` |

---

## Quick start

### Claude Code / Cursor / any client with remote HTTP support

```bash
claude mcp add --transport http haola-checkup https://ai.ihaola.com.cn/api/mcp/haola-pe
```

### Claude Desktop (config file)

See [`examples/claude-desktop.json`](examples/claude-desktop.json).

### Clients that only support stdio

Use [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) as a bridge:

```json
{
  "mcpServers": {
    "haola-checkup": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://ai.ihaola.com.cn/api/mcp/haola-pe"]
    }
  }
}
```

### No install at all

```bash
curl -s https://ai.ihaola.com.cn/api/mcp/haola-pe \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'
```

More: [`examples/cursor.md`](examples/cursor.md) · [`examples/curl.md`](examples/curl.md)

---

## Two real flows

### Enterprise: budget in, tiered plan out

```
plan_quotation({
  "quotes": [{
    "tier": "员工档",
    "budget": 800,
    "healthConcerns": "久坐、三高、亚健康",
    "populations": ["man", "lady", "girl"]
  }]
})
```

Returns `data.list[].planList[]`, each with `population`, `price`, `items` and `planId`.

### Personal: profile in, booking out

```
plan_recommend({ "gender": "male", "age": 41, "budget": 800,
                 "mainComplaint": "血糖偏高、过敏性鼻炎、轻度脂肪肝" })   → planId
vendor_list({ "city": "北京" })                                        → hospitalCode, vendorid
reservation_book({ "planId": "…", "hospitalCode": "…", "vendorid": "health100",
                   "appointmentDate": "20261201", "contactId": "…" })  → serviceid
```

`appointmentDate` is `YYYYMMDD`.

---

## Tools

25 tools. 9 need no credentials; 16 require a user token (the description of each tool is prefixed `[匿名可调用]` or `[需要登录]`).

Machine-readable definitions: [`tools/tools.json`](tools/tools.json).

### Anonymous — no credentials

| Tool | Purpose |
|---|---|
| `plan_quotation` | 企业团检分档报价：按人均预算和健康关注生成方案，返回每档每人群的项目、价格和 `planId` |
| `vendor_brands` | 可选体检品牌、覆盖城市数、门店数 |
| `vendor_list` | 按城市 / 区县 / 品牌 / 医院编码查门店地址与预约信息 |
| `knowledge_get` | 领域知识（输出规范、状态码等） |
| `faq` | 体检常见问题 |
| `help` | 查看当前可用工具与参数 |
| `corp_inquiry` | 提交企业合作咨询 |
| `corp_contact` | 获取商务对接人信息 |
| `progress_report` | 长耗时任务进度上报 |

### Requires a user token

| Tool | Purpose |
|---|---|
| `plan_recommend` | 个人定制方案：按性别、年龄、症状、预算推荐项目，返回 `planId` |
| `reservation_book` | 按 `planId` 预约下单，返回 `serviceid` |
| `reservation_modify` | 改期 |
| `reservation_cancel` | 取消（已支付会同时退款） |
| `order_list` / `order_detail` | 订单查询 |
| `welfare_list` / `welfare_detail` | 体检件查询 |
| `contact_list` / `contact_get` / `contact_create` / `contact_update` | 就诊人管理 |
| `contact_profile_get` / `contact_profile_save` | 结构化健康画像读写 |
| `cautions` | 检前注意事项（饮食、用药、禁忌） |
| `card_list` | 卡密与兑换情况 |

---

## Authentication

Anonymous tools work with **no** `Authorization` header. Everything else needs a user token.

The server implements standard MCP authorization:

1. Calling a private tool without a token returns `401` with
   `WWW-Authenticate: Bearer resource_metadata="https://ai.ihaola.com.cn/.well-known/oauth-protected-resource/api/mcp/haola-pe"`
2. The client reads the protected-resource metadata (RFC 9728) and discovers the authorization server
3. The client registers itself via **dynamic client registration** (RFC 7591) — no manual app registration
4. Authorization Code + **PKCE (S256)**
5. The access token is sent as `Authorization: Bearer …`

Login is by **mobile number + SMS code**.

> **Note for automated agents:** the final step needs a human to receive an SMS. Anonymous quoting works end-to-end without any human in the loop; booking does not.

---

## Coverage

| | |
|---|---|
| 合作体检机构 | 800+ 家 |
| 其中已接入 API、可被 AI 直接预约 | **540+ 家**（实测 `vendor_brands`：美年大健康/慈铭 471 + 瑞慈 72 = 543） |
| 覆盖城市 | 240+ |
| 体检服务人次 | 10 万+/年 |
| 健康测评人次 | 3500 万+（累计） |
| 服务保险公司 | 体检业务 10+ 家 · 健康测评业务 50+ 家 |

---

## Related

| | |
|---|---|
| 官网 | https://www.ihaola.com.cn/ |
| AI / agent 入口 | https://www.ihaola.com.cn/llms.txt |
| 完整能力说明 | https://www.ihaola.com.cn/llms-full.txt |
| OpenAPI | https://www.ihaola.com.cn/openapi.json |
| 开发者文档 | https://www.ihaola.com.cn/developer/ |
| 企业团检落地页 | https://www.ihaola.com.cn/html/mcp-quote.html |
| Agent Skill | [`skill/SKILL.md`](skill/SKILL.md) |

---

## Scope and compliance

- 好啦科技 **不做保险产品、不做医疗服务**，是体检服务的方案与预约层；实际体检由合作机构提供，合作门店均持《医疗机构执业许可证》
- 体检报告以结构化方式交付，**企业侧只能看到授权后的脱敏汇总，看不到任何个人体检结果**
- 国家等保三级 · ISO 27001 · ISO 9001 · 国家高新技术企业 · 北京市专精特新
- 本仓库是**接口文档与接入示例**，不含用户数据，也不含服务端源码

---

## License

[MIT](LICENSE) — applies to the documentation and examples in this repository. The hosted service itself is operated by 北京好啦科技有限公司 under separate terms.

---

北京好啦科技有限公司 · Haola Tech · contacts@haola.com
