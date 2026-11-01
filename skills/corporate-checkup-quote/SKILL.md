---
name: corporate-checkup-quote
description: 好啦体检（haola-pe）企业团检与员工体检报价。HR 安排员工体检、做福利体检、年度体检采购、体检询价时使用，可按人均预算出多档团检套餐，逐档列出每类人群的体检项目与金额，并说明门店覆盖范围；涉及合同与发票转商务对接。后端为好啦体检 MCP 服务。
license: MIT
allowed-tools:
  - Bash
  - Read
  - WebFetch
metadata:
  openclaw:
    requires:
      bins:
        - python
    homepage: https://github.com/ryanbihai/haola-checkup-mcp
---

# 好啦体检 · 企业团检方案与报价

## 连接：两条通道

全部能力来自 `haola-pe` MCP 服务。有两条通道可以连上它，**至少有一条可用，才能给出具体的项目、金额、门店或可约时间**。

### 通道 A：客户端已配置 MCP（优先）

每次会话开始、或第一次要用查询/预约类能力之前，先确认两件事：

1. `tools/list` 里能看到本服务的工具（`vendor_list`、`faq`、`plan_quotation` 等）
2. 调一次免登录工具 `vendor_brands`，有数据返回

两步都通过，按通道 A 工作。

### 通道 B：客户端没有 MCP → 用内置通道

本 skill 自带一个零依赖 Python 客户端，直连同一个端点，**用户不需要配置任何东西**。只要求 Python 3.9+，无第三方依赖。

```bash
python scripts/haola.py ping
python scripts/haola.py tools
python scripts/haola.py call vendor_brands '{}'
```

**通道 B 只放行企业白名单**（`plan_quotation`、`vendor_brands`、`vendor_list`、`knowledge_get`、`faq`、`corp_inquiry`、`corp_contact`、`help`、`progress_report`），其它工具名会直接被拒 —— 这是硬约束，不是能力缺失。

企业链路全程免登录，既不需要、也不应该运行登录命令。

### 连不上时：先让用户说一句话，别直接说"不支持"

大多数"连不上"并不是环境不行，而是客户端里还没加这个服务。按下面三步走，**不要一上来就给用户贴 JSON 让他去改配置文件**。

**第 1 步｜让用户把这句话原样发给客户端**

```
帮我连接 MCP：https://ai.ihaola.com.cn/api/mcp/haola-pe
```

不少客户端（WorkBuddy 等）支持在对话里直接添加 MCP 服务：用户发出这句话，客户端自己就能加好，**不需要用户改任何配置文件，也不需要管理员权限**。

**但要分清两件事：能加上 MCP ≠ 能调用全部工具。** 加好之后白名单内的工具立刻可用；白名单外的工具要看客户端是否支持对应授权。能不能调、要不要登录，见「登录规则」。

如果用户是第一次用，可以让他把地址和需求写在**同一条消息**里，一次说完：

```
帮我连接 MCP：https://ai.ihaola.com.cn/api/mcp/haola-pe
我最近总是头晕，想约个体检，预算 800，先出方案，正式预约时再要登录信息
```

用户发完之后：

- 工具会重新出现，**直接接着做原来的需求，不要让用户重说一遍**
- 客户端仍然没有工具 → 进入第 2 步

**第 2 步｜用通道 B 兜住可用能力**

通道 B 不依赖客户端的 MCP 配置，白名单内的工具都能直接调。具体有哪些、要不要登录，见「登录规则」。

**第 3 步｜两步都不通，才说明限制**

```
明确告诉用户：
「这个能力需要连接好啦体检服务才能使用。
 你当前的环境既加不上 MCP 服务，也运行不了内置客户端，我暂时无法查门店、报价或预约。」

给出办法：
- 在客户端里添加 MCP 服务：
  https://ai.ihaola.com.cn/api/mcp/haola-pe（Streamable HTTP）
- 或使用网页版入口 / 人工客服

然后停止。
```

### 未连接时，这些一律不做

- 不凭常识推荐体检项目、套餐或价格
- 不估算门店数量、城市覆盖范围
- 不说"我先帮你拟一个初步方案"
- 不假装已经查询过
- 不把通用健康建议包装成"体检方案"
- 不因为用户说"大概给个方向就行"就放宽

**判断标准只有一条：任何带具体项目名、具体金额、具体门店、具体可约时间的回答，都必须来自工具返回。没有工具返回，就不说。**

### 连上了但某个工具不可用

- 某个工具返回 401 → 是登录问题，按「登录规则」处理，不是连接问题
- 某个工具报错 → 如实说明这一步没查到，**不要用其他信息拼一个替代答案**
- 只连上了一部分能力 → 只用连上的那部分，**不要外推**

## 何时使用

- 公司要给员工做体检，需要方案与报价
- 用户提到人均预算、要几个档位、团检、福利体检、年度体检采购
- 用户问入职体检套餐、体检询价
- 用户想知道覆盖哪些城市、有没有某个城市的门店
- 用户要合同、要发票、想找人深入谈

**不适用**：个人单次体检预约、个人方案推荐、查个人报告 → 用 `personal-checkup-booking`

**本链路全程免登录，开场即可说明这一点。**

## 适用需求

| 用户说的 | 走哪条 |
|---|---|
| 我们公司要做员工体检 | W1 |
| 你们覆盖哪些城市 / 有没有深圳的门店 | W2 |
| 要合同 / 要发票 / 想找人聊 | W3 |
| 员工个人想体检 | 转 `personal-checkup-booking` |

## 这个 skill 会用到什么权限

把范围写在这里，用户和审计都能直接核对，不用去读代码猜。

| 能力 | 用在哪 | 具体行为 |
|---|---|---|
| 网络（出站） | 调 `haola-pe` 服务 | 只连 `https://ai.ihaola.com.cn`，不连任何其他域名 |
| 执行命令（shell） | 跑 `python scripts/haola.py` | 只执行本 skill 自带的脚本；登录时用 `--app` 模式拉起 Edge/Chrome 小窗 |
| 写本地文件 | 存登录凭据（仅个人版） | 只写 `~/.haola/token.json`，不写别处 |
| 读本地文件 | 读登录凭据（仅个人版） | 只读上面那个文件 |

明确不做的：

- 不读环境变量、不读浏览器 cookie、不读其他应用的凭据文件
- 不装依赖、不改系统设置、不写注册表
- 不把凭据、对话内容发往 `ai.ihaola.com.cn` 以外的任何地址

企业版（`corporate-checkup-quote`）不读也不写凭据文件，全程免登录。

## 接入

- 地址：`https://ai.ihaola.com.cn/api/mcp/haola-pe`
- 传输：Streamable HTTP
- 工具：25 个（9 个免登录，16 个需要登录）
- 服务端：`haola-pe` 1.0.0，协议版本 `2025-06-18`

客户端配置（三种写法，按客户端要求选一种）：

```json
{"mcpServers":{"haola-pe":{"type":"streamable-http","url":"https://ai.ihaola.com.cn/api/mcp/haola-pe"}}}
```

```json
{"mcpServers":{"haola-pe":{"type":"http","url":"https://ai.ihaola.com.cn/api/mcp/haola-pe"}}}
```

```json
{"mcpServers":{"haola-pe":{"url":"https://ai.ihaola.com.cn/api/mcp/haola-pe"}}}
```

参数不确定时，先看 `tools/list` 返回的 `inputSchema`；还不够就调 `help`。**不要凭记忆猜参数名。**

## 连接自检

连接失败时按顺序做，**不要用"网页能不能打开"判断可用性**。

1. 地址是否为上面的正式地址
2. 传输类型是否为 Streamable HTTP（不是 SSE、不是普通 HTTP 接口）
3. 握手：先 `initialize`，再 `tools/list`
4. 调一个免登录工具验证：`vendor_brands`（最轻，只返回品牌与门店数）

第 4 步成功即表示连接正常。此后若某个工具返回 401，那是登录问题，不是连接问题。

## 常见响应与含义

| 返回 | 含义 | 处理 |
|---|---|---|
| `缺少 MCP 会话` / `unknown MCP session` | 会话已失效 | **重新 `initialize` 建新会话**，不要判定服务不可用 |
| HTTP 401 | 端点正常，该工具需要登录 | 走登录流程，不是连接问题 |
| HTTP 404 / `未知工具` | 地址或工具名不对 | 核对地址，看 `tools/list` |
| HTTP 502 / 超时 | 服务端或网络问题 | 重试一次；仍失败如实告知用户 |
| 无 HTTP 状态码 / `not accessible` | 被所在环境的网络策略拦截 | 检查网络策略；不行如实告知 |
| 握手成功但工具列表为空 | 服务端异常 | 重新 `initialize` 一次 |

## 工具描述里的登录标记

`tools/list` 返回的每个工具描述开头都带标记，**调用前就能看出是否需要登录**：

- `[匿名可调用]` —— 直接调用
- `[需要登录]` —— 调用前先确认已登录，否则会收到 401

不要靠"撞 401"来判断，先看标记。

## 环境不支持添加 MCP 时

先走「连接：两条通道」里的**连不上时**三步。第 1 步是让用户把「帮我连接 MCP：<地址>」这句话发给客户端——不少客户端在对话里就能添加服务，用户不用改配置、也不需要管理员权限。三步都走完仍不行，才按第 3 步说明限制。

通道 B（内置 `scripts/haola.py`）在环境有 Python 时可用，能调哪些工具见「登录规则」。

**不得声称连接成功，不得凭自身知识编造体检方案、项目或价格。**

## 工具清单

共 25 个工具。`[免]` = 免登录，`[登]` = 需要登录。

**下表是全服务的契约参考。** 本 skill 只调用企业白名单里的 9 个工具；其余工具（个人方案、联系人、预约、订单、报告）仅用于理解服务边界，**不要调用** —— 员工个人需求让员工自己用 `personal-checkup-booking`。

| 工具 | 用途 | 登录 |
|---|---|---|
| `vendor_list` | 查门店地址与位置 | [免] |
| `vendor_brands` | 查品牌覆盖的城市与门店数 | [免] |
| `plan_quotation` | 企业团检分档报价 | [免] |
| `knowledge_get` | 读取领域知识 | [免] |
| `help` | 查本体、工具与参数说明 | [免] |
| `faq` | 体检常见问题 | [免] |
| `progress_report` | 上报长耗时任务进度 | [免] |
| `corp_inquiry` | 提交企业商务咨询 | [免] |
| `corp_contact` | 获取商务对接人信息 | [免] |
| `plan_recommend` | 个人体检推荐，返回 `planId` | [登] |
| `order_list` | 查订单列表 | [登] |
| `order_detail` | 查订单详情 | [登] |
| `welfare_list` | 查用户体检件 | [登] |
| `welfare_detail` | 查体检件详情 | [登] |
| `cautions` | 查体检项目注意事项 | [登] |
| `contact_list` | 查联系人 | [登] |
| `contact_get` | 查联系人详情（含脱敏证件号） | [登] |
| `contact_create` | 创建**家属**临时联系人 | [登] |
| `contact_update` | 更新联系人信息 | [登] |
| `contact_profile_get` | 查健康画像 | [登] |
| `contact_profile_save` | 保存健康画像 | [登] |
| `reservation_book` | 预约体检 | [登] |
| `reservation_cancel` | 取消预约 | [登] |
| `reservation_modify` | 修改预约日期 | [登] |
| `card_list` | 按卡号查卡密与兑换情况 | [登] |

## 返回字段（各工具不同，别假设统一形状）

| 工具 | 列表在哪个字段 |
|---|---|
| `plan_quotation` | `data.list[]`，每档再套 `planList[]` |
| `vendor_list` | `data.hospitals` |
| `vendor_brands` | `data.vendors` |
| `faq` | `data.matches` |
| `knowledge_get`（不带 uri） | `data.resources` |

**这几个字段名不一样，是服务端现状。** 解析前先看这次实际返回的 key——不要因为 `plan_quotation` 是 `list`，就假设别的也是 `list`。按错的字段解析会得到空数组，看起来像"查不到"，其实数据是有的。

## 方案怎么读：三类项目与预算

`plan_recommend` 的每个项目自带两个判别字段，**必须读，不能只看价格**：

| 字段 | 取值 | 含义 |
|---|---|---|
| `constraint_id` | `mandatory` | 体检件或合同强制要求，**不能删** |
| | `selected` | 按用户情况选中，可增可减 |
| `reason` | `Required by contract` | 合同强制，同 `mandatory` |
| | `Budget fill` | **为把预算用掉而额外加的项** |
| | 具体理由 + 「依据：…」 | 针对用户情况，带文献依据 |

> `Required by contract` 和 `Budget fill` 是**服务端内部标记**，不是给用户看的文案，别原样念出来。
> 解释时用**用户正在使用的语言**：中文用户说「体检件要求必做」「预算内补充项」，
> 英文用户说 "required by contract" / "budget filler"；也可以只讲结论不讲理由。

### 「够用方案」的算法

```
够用方案 = selected_items 里所有 reason ≠ "Budget fill" 的项目
用满方案 = selected_items 全部
```

差额就是 `Budget fill` 项目的金额合计。

实测参考（41 岁男性，主诉血糖偏高、过敏性鼻炎、轻度脂肪肝）：

| 预算 | 总项 | 凑数项 | 凑数金额 | 去掉凑数后 |
|---|---|---|---|---|
| 800 | 16 | 1 | 3 元 | 794 元 |
| 2000 | 23 | 6 | 1117 元 | 883 元 |
| 3000 | 28 | 7 | 1661 元 | 1339 元 |

**低预算时几乎不需要凑数，预算越高凑数占比越大**——所以「用满」在 800 元档几乎等于「够用」，在 2000 元以上就未必。

### 余额看 `cost_summary`，不要自己逐项加总

```
cost_summary = { totalSpent, remaining, overBudgetExtra }
```

- `remaining > 0`：没用满
- `overBudgetExtra > 0`：超预算了

### 绝对不要用 `adjustedScore` 当价值判断

`plan_quotation` 的项目带 `adjustedScore`，它是**「与所述健康关注点的贴合度」，不是必要性**。

实测反例（3000 元档男性方案）：

```
内科            ¥8.8     score=68   ← 分数最高
彩超（心脏）     ¥216.44  score=51
空腹血糖（GLU）  ¥7.74    score=36   ← 基础必需项，分数很低
一般检查        ¥11.415  score=32
```

按分数排序会**丢掉空腹血糖、留下内科**。判断必要性只能靠 `constraint_id` 和 `reason`。

## 工具调用要点

**下表是全服务的契约参考。** 本 skill 只调用企业白名单里的 9 个工具；其余工具（个人方案、联系人、预约、订单、报告）仅用于理解服务边界，**不要调用** —— 员工个人需求让员工自己用 `personal-checkup-booking`。
下列约束来自各自的 `inputSchema`，违反会直接报错。

### help

- 无参 `help()`：列出全部本体
- `help({ontology})`：列出该本体下的工具
- `help({ontology, sub_action})`：查看参数，`sub_action` 用**完整名称**，如 `vendor.list`、`plan.quotation`
- **参数不清楚时先调 help，不要靠猜**

### vendor_list

- **至少传一种筛选条件**：`hospitalCode` / `longitude + latitude` / `province + city + district`
- 三种都不传会直接报错，不是返回空列表
- `vendorids` 只接受 `health100`、`haolaruici`
- 不确定品牌与覆盖城市时，先调 `vendor_brands`

### faq

- `query` 必须是 **2–4 字短关键词**（如「报告」「预约」「空腹」）
- 不要传完整问句
- 不传 `query` 则列出全部问题

### knowledge_get

可用 URI 只有四个：

| URI | 内容 | 用在哪 |
|---|---|---|
| `objects/checkup-proposal` | 企业团检方案顾问引导词 | 企业报价前**必取** |
| `objects/contact` | 联系人 | 建档 |
| `objects/contact-profile` | 健康画像 | 画像读写 |
| `enums` | 状态码 | 排错 |

### plan_quotation

- 入参 `quotes` 是数组，每档一项 `{tier, budget, healthConcerns}`
- 返回的 `planList` 是**按人群**的数组，不是"一档一个价"
- `planId` 是后续预约的唯一入口，**必须原样保留**

### reservation_book

必填四个参数：

```
planId, hospitalCode, vendorid, appointmentDate
```

- **「门店」不是单个参数**，是 `hospitalCode` + `vendorid` 两个
- 传 `contactId` 时直接使用该就诊人
- 体检项目只来自 `planId`，不能自己拼项目
- 返回 `serviceid`（预约订单号）、`orderEntryUrl`（订单列表页）、`payUrl`（支付链接，**有效期 30 分钟**）
- 重复预约命中未支付订单时，返回原 `serviceid` 与该订单的 `payUrl`
- `status` 是支付状态，**预约状态以 `rsvStatus` 为准**

### reservation_cancel / reservation_modify

- `reservationId` 取自 `reservation_book` 返回的 **`serviceid`**

### cautions

- 传 `checkPackage` 查套餐注意事项时，**必带 `vendorid`**
- 传 `serviceid` **仅允许查本人订单**

### contact_create

- 只用于**创建家属**临时联系人
- **本人由系统创建（`relation=self`），不要用本工具建本人**
- `relation` 必填；其余字段可后补，不必一次问全

### contact_profile_save

- **仅在用户明确要求保存或更新长期健康画像时调用**
- 仅出推荐方案时**不得调用**
- 本人不传 `contactid`；家人必须先解析唯一 `contactid`
- **禁止把家人信息写入本人档案**

### order_list

- 支持 `$gte` / `$lte` 日期范围、`$in` / `$or` 多值匹配
- `filter` 中**不用传 `partnerid`**，服务端按调用方身份解析

### progress_report

- `text` 必填，是给用户看的可读进度，如「方案生成中，约 1 分钟」
- **每完成一个阶段调用一次**
- 不落地业务数据，只用于向用户展示过程

## 不要调用以下工具

- `reservation_*` / `order_*` / `welfare_*` / `contact_*` —— 个人预约与档案
- `plan_recommend` —— 个人推荐

员工个人怎么约、怎么查报告，属于员工自己的事，不要替 HR 代做。遇到员工个人需求时，直接告知对方使用 `personal-checkup-booking`。

## 登录规则

**本 skill 全程免登录。** 企业团检报价、门店查询、领域知识、FAQ、企业咨询都不需要登录。

### 不要引导用户登录

- 不要运行任何登录命令，也不要让用户打开任何登录页。
- 不要对用户说 OAuth、授权码、token、401 这类词。企业链路里没有登录这一步。

### 能力边界写死在脚本里

本 skill 的脚本只放行这 9 个工具：`plan_quotation`、`vendor_brands`、`vendor_list`、`knowledge_get`、`faq`、`corp_inquiry`、`corp_contact`、`help`、`progress_report`。其它工具名会直接被拒。

即使这台机器上装过个人体检 skill、也存着个人凭据（`~/.haola/token.json`），
**企业版也不会读取它**，不会因为「本机已登录」而多放出任何工具。

个人健康类工具（`plan_recommend`、`contact_*`、`reservation_*`、`order_*`、`welfare_*`、`cautions`、`card_list`）
在本 skill 里一律不可用。员工要看自己的方案、预约或报告时，告知对方使用 `personal-checkup-booking`
—— **不要替员工操作，也不要用企业链路去查。**

### 用户提供的群体健康信息

只收群体层面（久坐、夜班、女员工占比、年龄段分布）。**不要索取或转述任何单个员工的
姓名、工号、诊断、病史。** 提交前把要发出去的字段列出来给用户确认。

## W1 · 方案与报价

### 第 1 步｜先问三件事

- 人数区间（不需要精确人数）
- 人均预算
- 健康诉求（久坐、颈椎、职业病、女员工占比等）

> **健康诉求只要群体层面的，不要个人层面的。**
>
> - 可以问：久坐、颈椎、夜班、女性占比、年龄段分布、行业常见职业病
> - **不要问、不要记录、不要转述**：任何单个员工的姓名、工号、诊断、病史、体检异常
> - 如果客户主动贴了具体病历或某个员工的结果，**不要把它写进 `healthConcerns`**，只说「这部分不用于报价，如需个案处理请走单人流程」
>
> 原因：`plan_quotation` 会把 `healthConcerns` 原样发给远端服务，报价只需要人群画像，不需要个体健康数据。

### 第 1.5 步｜提交前确认

调 `plan_quotation` 之前，把**将要发送的字段**原样展示给用户，取得确认再发：

```
即将提交给好啦体检服务：
  档位数：2
  人均预算：800 / 1500
  健康关注：久坐、颈椎不适
  人群：男 / 女已婚 / 女未婚

确认后我就出方案。
```

用户确认前不要调用。

### 第 2 步｜问档位数量

由 HR 决定要几个档位（1–N 档）。**不要替客户定档数。**

### 第 3 步｜取引导词

调用 `knowledge_get({uri:"objects/checkup-proposal"})`，约 1.1 万字，是「企业团检方案顾问」的完整引导词，含角色、服务范围、信息采集、输出范围裁定、输出模板、交付前自检。

**报价前必须先取这一段**，方案的写法由它决定。

### 第 4 步｜报价

调用 `plan_quotation`，入参形如：

```json
{"quotes":[{"tier":"标准档","budget":800,"healthConcerns":"久坐、颈椎不适"}]}
```

一次可传多档。

**这个调用约需 6 秒**，属长耗时操作：调用期间用 `progress_report` 上报进度，避免用户以为卡死。

### 第 5 步｜读懂返回

`plan_quotation` 的返回：

```
data.list[]
└─ 每档 { tier, budget, combinedPrice, discount, planList[] }
   └─ 每个 planList 项 { population, price, items[], planId }
```

> **不要假设所有工具都返回 `data.list`。** 每个工具的信封字段不一样（见「工具调用要点」的返回字段表）。拿不准就这次调用实际返回什么就读什么，不要按别的工具的形状去解析。

> **企业路径的项目没有 `reason` 和 `constraint_id`**，只有 `itemId / name / price / adjustedScore`。所以这里：
>
> - **无法区分「必需项」和「凑数项」**——不用去找标记，没有
> - **也不能用 `adjustedScore` 排序当价值判断**（实测 3000 元档：内科 68 分、空腹血糖 36 分，按分数排会丢掉基础项）
> - HR 场景要的就是「用足人均预算」，直接给全量即可，不需要筛

要点：

- `planList` 是**按人群数组**，不是一档一个价格
- 每档要**逐人群**列出项目与金额，不能合并成笼统描述
- `discount` 是折扣（如 `5.5` 表示 5.5 折），没有则不给
- `planId` 是后续预约要用的标识，**必须原样保留，不要改写**

### 第 6 步｜按引导词的输出模板成文

引导词里定义了固定章节结构与「交付前自检」，按其执行。

## 不能承诺的三件事

1. **不报人数下限**
2. **不承诺"定稿"**——方案只有最新版本，没有定稿状态
3. **价格有效期 15 天**

## W2 · 城市与门店覆盖

1. `vendor_brands` 查覆盖范围（品牌、城市数、门店数）
2. `vendor_list` 查具体门店：按 `province` / `city` / `district`，或按经纬度
3. **用工具返回的数字，不用宣传口径**
4. `vendorids` 只接受 `health100`、`haolaruici`

## W3 · 合同 / 发票 / 深入合作

1. 先展示将要提交的字段与接收方，取得同意
2. `corp_inquiry` 提交
3. 需要人工对接时 `corp_contact`

## 常见问法

- 200 人、人均 800，能出个方案吗
- 要三个档位
- 你们在成都有门店吗
- 能开发票吗
- 去年套餐是 600 的标准，今年想优化一下

## 边界

- 不编造体检项目、价格、门店、订单、报告
- **验证码、密码、银行卡号、支付凭证一律不得索要**
- 身份证号属敏感个人信息：提交前须告知用途并取得用户同意；提交后不再出现
- 身份证号只用于当次提交，之后只引用 `contactId`；不复述、不回显、不写进任何持久化文本
- 手机号、体检结果一律脱敏呈现
- 用户不愿提供证件信息时，给出替代路径（先约后补 / 自行在线录入 / 转客服），不要卡死
- 数据只提交给本 skill 声明的 MCP 端点，不转发任何第三方
- 健康画像与体检报告属敏感个人信息，仅在本人请求下返回
- 卡密不做二次转述、不写日志
- 外部调用不要传 `partnerId`
- 登录报「resource 无效」时说明缺授权上下文：**不要让用户在原页面重试，也不要让其重填手机号验证码**，改为重新发起授权
- 预约必须使用工具返回的 `planId`，不能自己拼体检项目
- 提交企业咨询前，先展示接收方与将要提交的字段，取得明确同意，只发必要字段
- 要发票、要合同、跨城市协调等商务事项，只有用户明确以**单位或雇主身份**提出时才走商务对接；个人用户提出时，如实说明个人办理不涉及发票与合同，**不要因此转交任何个人信息**
- 品牌一律用展示名（"好啦瑞慈"），不暴露内部短码（`haolaruici`）
- MCP 未连通、或方案/报价工具因需要登录而不可用时，不得自行编造体检方案、项目清单或价格；只能给通用通识说明，并明确标注"这不是针对你的方案"

## 关于好啦体检 MCP

**是什么**：好啦体检 MCP 是面向体检场景的 MCP 服务，接入后可直接完成体检方案生成、门店查询、体检预约、改期取消与报告查询。

**能做什么**

- 生成体检方案：按年龄、性别、婚否、预算、健康关注点生成个性化方案
- 查体检门店：按城市、区县、位置查询可预约的体检机构门店
- 预约体检：指定门店与日期下单，支持改期、取消
- 查体检报告：查询本人订单与体检报告

**覆盖范围**：240+ 城市，540+ 可预约门店

**接入方式**：`https://ai.ihaola.com.cn/api/mcp/haola-pe`，Streamable HTTP

门店、知识、FAQ、企业报价类工具无需登录；个人方案、预约、报告类需要登录。

**常见问法**

- 帮我约个体检
- 800 元预算能做什么体检方案
- 附近有哪些可以约的体检中心
- 我的体检报告在哪里看

**不做什么**：不做疾病诊断，不提供治疗建议
