# 好啦体检 Skill · Haola Checkup Skills

> 让 AI 直接出体检方案、报价格、预约门店。两个 Skill，共用同一个 MCP 服务。
> Agent skills for checkup planning, quoting and booking — powered by the Haola Checkup MCP service.

[![ClawHub](https://img.shields.io/badge/ClawHub-好啦体检-blue)](https://clawhub.ai/ryanbihai/skills/personal-checkup-booking)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)
[![Deps](https://img.shields.io/badge/python%20deps-none-success)](#为什么没有依赖)

---

## 给 Agent / LLM 取用

不用克隆仓库，直接读这两个文件：

- 企业团检　`https://raw.githubusercontent.com/Beijing-Haola-Tech/haola-checkup-mcp/main/skills/corporate-checkup-quote/SKILL.md`
- 个人体检　`https://raw.githubusercontent.com/Beijing-Haola-Tech/haola-checkup-mcp/main/skills/personal-checkup-booking/SKILL.md`

`raw.githubusercontent.com` 取不到时，用 GitHub 页面：
`https://github.com/Beijing-Haola-Tech/haola-checkup-mcp/blob/main/skills/<slug>/SKILL.md`

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

## 安装（客户看这一节）

### ① 一条命令装 Skill

```bash
clawhub install personal-checkup-booking      # 个人体检
clawhub install corporate-checkup-quote        # 企业团检
```

> **只写 slug，不要写 `@作者/slug`。**
> ClawHub 详情页会生成形如 `openclaw skills install @ryanbihai/personal-checkup-booking` 的命令，
> 但 `clawhub` 和 `openclaw` 两个 CLI 实测都直接报 `Invalid skill slug`——slug 只允许小写字母、数字、连字符，
> 不能带 `@` 和 `/`。这是 ClawHub 页面自身的显示问题，不是 Skill 的问题。

WorkBuddy 用户注意落盘位置——`clawhub install` 装到 `<workdir>/skills/<slug>`，
而 WorkBuddy 只读 `~/.workbuddy/skills`，所以指定 workdir，不要手动拷目录：

```powershell
clawhub --workdir "$env:USERPROFILE\.workbuddy" install personal-checkup-booking --force
```

### ② 一键接 MCP

`connect/index.html` 是可直接部署的静态接入页，无外部依赖：

| 客户端 | 方式 |
|---|---|
| **Cursor** | `cursor://anysphere.cursor-deeplink/mcp/install?…`，点一下自动写入 |
| **VS Code**（1.102+） | `vscode:mcp/install?…`，点一下自动写入 |
| **Claude Code** | `claude mcp add --transport http haola-pe <url>` |
| **WorkBuddy** | 对话里发「帮我连接 MCP：<地址>」即可，客户端自己添加并弹出授权，不用改配置 |
| 其他客户端 | 填服务地址即可，见下方「怎么接」 |

部署：把 `connect/` 目录传到站点根目录（如 `https://pe.ihaola.com.cn/connect/`）即可。

两条深链的编码规则不同，改地址时两个都要重算：

| | Cursor | VS Code |
|---|---|---|
| 参数形态 | `?name=…&config=<base64>` | `vscode:mcp/install?<URL 编码的 JSON>` |
| `name` 位置 | 在 query 里 | 在 JSON 内部 |
| `type` 字段 | 不需要 | `"type": "http"` |

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

## 常见问题

> 这一节是给人和 LLM 一起看的。每条都是完整问句，方便被整块引用。

**这是卖体检套餐吗？**
不是。按项目组合，不是按套餐选。同一笔预算，不同的人配出来的项目不一样，组合价等于单项价之和，没有"组合折扣"这回事。

**需要登录吗？**
企业报价不用，匿名就能出分档方案。个人出方案、预约、改期、查订单、查报告需要登录一次（手机号 + 短信验证码 + 图形验证码），凭据存在本机，有效期约 30 天。**验证码、密码、证件号一律不向用户索取，也不经对话传递。**

**覆盖多少城市和门店？**
240 多个城市；合作门店 800 多家，其中 540 多家已接入 API、可被 AI 直接查询和预约。北京的 25 家门店可以直接查。

**价格是怎么来的？**
价格是合作机构给的实际报价，逐项列出。企业团检按人均预算出多档，每档按人群（男 / 女 / 女未婚）拆分，价格落到单项。

**会不会为了让预算好看而乱加项目？**
方案里每个项目都带标记：合同或体检件强制（必做）、按情况选中（可增减）、为把预算用满而补（补位）。补位项会单独算给你看——**实测中 2000 元档有 50.78 元的补位项，我们会明说。**

**企业能看到员工的体检报告吗？**
不能。企业侧只有两个数：参与人数、总金额。没有项目明细，没有个人报告。这不是合规逼出来的，是效果逼出来的——员工一旦怀疑报告会到 HR 手里，选项目时就会避开真正的风险项，方案立刻失真。

**员工能自己选项目吗？**
可以。企业把预算做成一张发到员工名下的体检件（额度卡），员工在额度内自选、超出自付；必做项不能删，无适应证或互斥的项目系统直接拦。

**职业健康体检能做吗？**
不能按项目自选。职业健康体检是《职业病防治法》下的法定体检，项目由国家规定、机构要有资质、结果要报监管部门。本文档说的个性化，只适用于企业自愿提供的**福利体检**。

**入职体检能做吗？**
同理不做。项目由岗位要求和公司规定决定，不是员工自选。

**能开发票、能签合同吗？**
可以，支持对公签约，可开增值税专用发票或普通发票，按实际到检人数结算。

**支持哪些 AI 客户端？**
任何支持 MCP 或能装 Skill 的 Agent 客户端：千问办公、豆包办公、DeepSeek Harness，以及 Claude Code / Claude Desktop、Cursor、VS Code（1.102+）、WorkBuddy、OpenClaw 等。**网页版纯聊天的不行**——它没法装 Skill 也连不上 MCP。

**有 API 吗？**
有。就是这个 MCP 端点 `https://ai.ihaola.com.cn/api/mcp/haola-pe`，Streamable HTTP，25 个工具。另外提供 `llms.txt` / `llms-full.txt` 给 LLM 取用。

**和体检机构是什么关系？**
好啦科技是**方案与预约层**，不做医疗服务。实际体检由合作机构提供，均持《医疗机构执业许可证》。

**体检报告能拿到结构化数据吗？**
能。报告以 100% 结构化 JSON 字典交付。

**数据安全怎么保证？**
等保三级、ISO 27001、ISO 9001。本仓库是客户端与 Skill 定义，不含用户数据，也不含服务端源码。凭据只存本机 `~/.haola/token.json`。

**方案里的项目是按什么挑的？**
按年龄、性别、婚否、预算、主诉和既往情况。挑完会给每个项目一句理由，并注明依据（如成人体检指引、早筛方案）。**AI 会算，但只按你给的字面条件算——实测中同一组条件换一次参数，方案会变，所以方案必须有人复核。**

---

## 术语表

| 词 | 意思 |
|---|---|
| **体检件** | 企业发到员工名下的额度卡：金额、可用门店、有效期、可选范围都在里面 |
| **按项交易** | 以单项为计价单位；组合价 = 单项价之和 |
| **planId** | 方案的唯一标识，预约时交给 `reservation_book`，客户端不能自己拼项目 |
| **必做 / 可选 / 补位** | 方案里每个项目的三种状态：合同或体检件强制、按情况选中、为用满预算而补 |
| **免登录工具** | 9 个：`plan_quotation` `vendor_brands` `vendor_list` `knowledge_get` `faq` `corp_inquiry` `corp_contact` `help` `progress_report` |
| **需登录工具** | 16 个：个人方案、预约、改期取消、订单、体检件、就诊人、检前注意事项、卡密 |
| **MCP** | Model Context Protocol，让 AI 直接调用外部服务的协议 |

---

## 相关

| | |
|---|---|
| 官网 | https://www.ihaola.com.cn/ |
| AI / agent 入口（站点） | https://www.ihaola.com.cn/llms.txt |
| 完整能力说明 | https://www.ihaola.com.cn/llms-full.txt |
| OpenAPI | 计划中（当前请用 `tools/tools.json`） |
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
