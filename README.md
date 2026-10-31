# 好啦体检 Skill · Haola Checkup Skills

> 让 AI 直接出体检方案、报价格、预约门店。两个 Skill，共用同一个 MCP 服务。
> Agent skills for checkup planning, quoting and booking — powered by the Haola Checkup MCP service.

[![ClawHub](https://img.shields.io/badge/ClawHub-好啦体检-blue)](https://clawhub.ai/ryanbihai/skills/personal-checkup-booking)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)
[![Deps](https://img.shields.io/badge/python%20deps-none-success)](#为什么没有依赖)

---

## 给 Agent / LLM 取用

不用克隆仓库，直接读这两个文件：

- 企业团检　`https://raw.githubusercontent.com/ryanbihai/haola-checkup-mcp/main/skills/corporate-checkup-quote/SKILL.md`
- 个人体检　`https://raw.githubusercontent.com/ryanbihai/haola-checkup-mcp/main/skills/personal-checkup-booking/SKILL.md`

`raw.githubusercontent.com` 取不到时，用 GitHub 页面：
`https://github.com/ryanbihai/haola-checkup-mcp/blob/main/skills/<slug>/SKILL.md`

每个 skill 目录都是**自包含**的——`SKILL.md` 加一份零依赖客户端，单独拷走也能跑。
更多见 [skills/README.md](skills/README.md)。

---

## 两个 Skill

同名服务，两种场景，各自独立安装：

| Skill | 面向 | 能做什么 | 安装 |
|---|---|---|---|
| **好啦体检 · 个人体检预约** | 个人 / 员工 / 代家人预约 | 按年龄、性别、婚否、预算出个性化方案；查门店；预约、改期、取消；查订单与报告 | `personal-checkup-booking` |
| **好啦体检 · 企业团检方案与报价** | HR / 行政 / 采购 | 按人均预算出多档团检方案，逐档逐人群列出项目与金额；查城市与门店覆盖；合同发票对接 | `corporate-checkup-quote` |

在 ClawHub 搜索「**好啦体检**」即可找到两个。

---

## 怎么接

两个 Skill 共用同一个 MCP 服务：

```
https://ai.ihaola.com.cn/api/mcp/haola-pe
```

| | |
|---|---|
| 传输 | Streamable HTTP |
| 协议版本 | `2025-06-18` |
| 免登录工具 | 9 个（个人版客户端只放行其中 6 个）|
| 需登录动作 | 个人方案、预约、订单、报告、体检人 |
| 覆盖 | 800+ 家体检机构 / 240+ 城市 / 其中 540+ 家可被 AI 直接预约 |

### 两条连接通道

**通道 A · 客户端已配置 MCP**（优先）

把上面的地址加进支持 MCP 的客户端即可。Claude Code 一行：

```bash
claude mcp add --transport http haola-checkup https://ai.ihaola.com.cn/api/mcp/haola-pe
```

**通道 B · 客户端没有 MCP** → 用 Skill 自带的客户端

零依赖 Python 客户端，直连同一个端点，用户不需要配置任何东西：

```bash
python scripts/haola.py ping
python scripts/haola.py quote --budget 800 --concerns "久坐、三高"
```

---

## 设计上的三条硬约束

这套东西最容易出问题的地方是「文档里写了限制，代码里没有」。所以三条约束都做进了代码：

**① 客户端不接受任何凭据**

没有 token 参数，不读环境变量，不发 `Authorization` 头。凭据不经过这个客户端。

**② 工具白名单是硬的**

每个 Skill 的白名单直接写进产物的 `client.py`：

| Skill | 白名单 |
|---|---|
| 个人版 | `vendor_list` `vendor_brands` `knowledge_get` `faq` `help` `progress_report` |
| 企业版 | 上面 6 个 + `plan_quotation` `corp_inquiry` `corp_contact` |

名单外的工具名会被直接拒绝，不是靠文档说“请不要调用”。

**③ 登录只在网页上发生**

需要登录的动作引导用户到网页完成，四步：

1. 填手机号
2. 点「获取验证码」→ 弹出图形验证码
3. 填图形验证码 → 此时才会收到短信
4. 填短信验证码 → 点「登录」

登录入口：`https://pe.ihaola.com.cn/auth/`

**验证码、密码、证件号一律不向用户索取，也不经对话传递。**

---

## 为什么没有依赖

客户端只用标准库（`urllib` / `json`）。原因：

1. Skill 要在陌生环境里跑，预装依赖是 Agent 场景最大的失败源
2. MCP Streamable HTTP 的握手很薄——initialize 一次、带 `mcp-session-id`、解析 SSE 的 `data:` 行
3. 审计面小，供应链风险为零

---

## 目录结构

```
.
├── skills/
│   ├── README.md                             # 索引：两个 skill 各是什么、怎么取
│   ├── personal-checkup-booking/             # 个人版（自包含，可单独拷走）
│   │   ├── SKILL.md                          #   给模型读的说明书
│   │   ├── mcp.json                          #   客户端配置片段
│   │   ├── scripts/haola.py                  #   免安装启动器
│   │   └── src/haola_checkup/                #   client.py / cli.py / __init__.py
│   └── corporate-checkup-quote/              # 企业版（同上，自包含）
├── src/haola_checkup/
│   ├── client.py                             # MCP 客户端（仅免登录）
│   └── cli.py                                # 命令行
├── scripts/haola.py                          # 免安装启动器
├── tools/tools.json                          # 25 个工具的定义
├── examples/                                 # curl / Cursor / Claude Desktop
├── llms.txt                                  # 给 LLM 的入口说明
└── pyproject.toml
```

`skills/<slug>/` 整个目录是发布到 ClawHub 的产物，由内部构建流水线生成后同步过来，
**不要在这里直接改**——改了会被下次同步覆盖。仓库根目录的 `src/`、`scripts/`、
`tools/` 是同一份客户端的手工维护版，给 pip 安装和示例用。

---

## 开发

```bash
pip install haola-checkup          # 或直接用 scripts/haola.py
haola-checkup ping
haola-checkup tools
haola-checkup quote --budget 800 --concerns "久坐、三高"
```

打包：

```bash
pip install build
python -m build
twine upload dist/*
```

---

## 相关

| | |
|---|---|
| 官网 | https://www.ihaola.com.cn/ |
| AI / agent 入口 | https://www.ihaola.com.cn/llms.txt |
| 完整能力说明 | https://www.ihaola.com.cn/llms-full.txt |
| OpenAPI | https://www.ihaola.com.cn/openapi.json |
| 企业团检落地页 | https://www.ihaola.com.cn/html/mcp-quote.html |

---

## 边界与合规

- 好啦科技**不做保险产品、不做医疗服务**，是体检服务的方案与预约层；实际体检由合作机构提供，均持《医疗机构执业许可证》
- 体检报告以结构化方式交付，**企业侧只能看到授权后的脱敏汇总，看不到任何个人体检结果**
- 国家等保三级 · ISO 27001 · ISO 9001 · 国家高新技术企业 · 北京市专精特新
- 本仓库是**客户端与 Skill 定义**，不含用户数据，也不含服务端源码

---

## License

[MIT](LICENSE) — 覆盖本仓库的客户端代码、文档与示例。托管服务本身由北京好啦科技有限公司依单独的服务条款运营。

> **关于 ClawHub 上的 License 显示**：ClawHub 的 Skill 条目统一显示 `MIT-0`，这是平台对 Skill 列表的固定展示，不读取 `SKILL.md` frontmatter 里的 `license` 字段（`clawhub publish` 也没有对应参数）。`MIT-0` 比 MIT 更宽松——不要求署名，不影响任何人使用。本仓库的代码仍是 MIT。

北京好啦科技有限公司 · Haola Tech · contacts@haola.com
