---
name: personal-checkup-booking
description: 好啦体检（haola-pe）个人体检预约与体检方案推荐。用户说帮我安排个体检、体检项目怎么选、体检多少钱、几百块能查什么、入职体检要做什么项目、附近哪有体检中心、体检报告在哪看、要改期或取消时使用。可按年龄、性别、婚否与健康关注点生成个性化体检方案，覆盖全国 240+ 城市，支持在线预约、改期、取消与报告查询。后端为好啦体检 MCP 服务。
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - WebFetch
metadata:
  openclaw:
    requires:
      bins:
        - python
    homepage: https://github.com/Beijing-Haola-Tech/haola-checkup-mcp
---

# 好啦体检 · 个人体检预约

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

**通道 B 也覆盖登录类工具。** 先登录一次，之后本 skill 支持的 22 个工具都能用：

```bash
python scripts/haola.py login
```

未登录时只放行免登录工具（`vendor_list`、`vendor_brands`、`knowledge_get`、`faq`、`help`、`progress_report`），其它工具名会直接被拒——**这是白名单，不是能力缺失**，登录后自动放开，不用改任何配置。

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

- 用户想体检，但不知道查什么项目
- 用户有预算，想知道能做到什么程度
- 用户要预约、改期、取消体检
- 用户想查自己的订单或体检报告
- 用户想给家人预约体检
- 用户问附近有哪些体检机构、某个城市有没有门店
- 用户问体检流程、空腹、注意事项

**不适用**：公司员工团检、人均预算分档报价、要发票要合同 → 用 `corporate-checkup-quote`

## 适用需求

| 用户说的 | 走哪条 |
|---|---|
| 我想体检，不知道查什么 | W1 |
| 我有预算，想知道能做什么 | W2 |
| 帮我约体检 | W3 |
| 我要改期 / 取消 / 看报告 | W4 |
| 给我家人约 | W5 |
| 公司要组织员工体检 | W6（转 `corporate-checkup-quote`） |

## 这个 skill 会用到什么权限

把范围写在这里，用户和审计都能直接核对，不用去读代码猜。

| 能力 | 用在哪 | 具体行为 |
|---|---|---|
| 网络（出站） | 调 `haola-pe` 服务 | 只连 `https://ai.ihaola.com.cn`，不连任何其他域名 |
| 凭据去向 | 登录后的请求 | **只发给 `https://ai.ihaola.com.cn`**；把 `--url` 指向别的地址时不会附带凭据 |
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

下表是全服务的 25 个工具。**本 skill 只调用其中 22 个** —— 不含 `plan_quotation`、`corp_inquiry`、`corp_contact` 这三个企业侧工具，登录后也不会变；未登录时只有白名单内 6 个能调。

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

下表是全服务的 25 个工具。**本 skill 只调用其中 22 个** —— 不含 `plan_quotation`、`corp_inquiry`、`corp_contact` 这三个企业侧工具，登录后也不会变；未登录时只有白名单内 6 个能调。
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

- `plan_quotation` —— 企业分档报价，个人场景请用 `plan_recommend`
- `corp_inquiry` / `corp_contact` —— 企业商务咨询

遇到公司 HR 或企业团检需求时，直接告知对方使用 `corporate-checkup-quote`，不要用 `plan_quotation` 硬算。

## 登录规则

只有三类动作要登录：**出个人方案、登记体检人、预约/改期/取消/查订单/查报告**。
其余一律免登录。用户没走到这三类动作之前，**不要主动提登录**。

### 哪些要登录

| 动作 | 工具 | 要登录 |
|---|---|---|
| 讲项目含义 | `knowledge_get`、`faq` | 否 |
| 查门店 | `vendor_list`、`vendor_brands` | 否 |
| 企业分档报价 | `plan_quotation` | 否 |
| 企业咨询 | `corp_inquiry`、`corp_contact` | 否 |
| 报进度 | `progress_report` | 否 |
| 出个人方案 | `plan_recommend` | 是 |
| 建档 / 健康画像 | `contact_*`、`contact_profile_*` | 是 |
| 预约 / 改期 / 取消 | `reservation_*` | 是 |
| 订单 / 报告 | `order_*`、`welfare_*` | 是 |
| 注意事项 | `cautions` | 是 |
| 卡密 | `card_list` | 是 |

### 遇到「需要登录」怎么办

**不要对用户说**：OAuth、授权码、PKCE、Bearer、token、401、resource。

只做一件事：**让用户在本机跑一次登录命令。**

```bash
python scripts/haola.py login
```

它会弹出一个独立的登录小窗（不是整个浏览器），让用户在里面登录一次（手机号 → 获取验证码 → 图形验证码 → 短信码）。
登录成功后凭据存在本机（`~/.haola/token.json`），**有效期约 30 天**，
之后所有需要登录的工具都能直接调，用户不用再登。

用户说"登录好了"之后，**原样重试刚才那个调用**，不要让他重说需求。

### 这个命令必须在 skill 目录里跑

```bash
cd <skill 所在目录> && python scripts/haola.py login
```

不知道目录时先 `ls skills/` 或直接问用户 skill 装在哪。跑之前先确认目录，
否则脚本会找不到 `haola_checkup` 包。

### 已经登录过就不用再登

不确定时先跑：

```bash
python scripts/haola.py whoami
```

- 输出「已登录」→ 直接调工具
- 输出「未登录」→ 再走 login

凭据过期（约 30 天）后重新 login 一次即可，不需要重新理解需求。

### MCP 报 401 ≠ 没登录

本机脚本和 MCP 是两条通道，**登录态只在本机脚本里**。

要调登录类工具时，**先 `whoami`，再决定走哪条**，不要一上来就撞 MCP：

```bash
cd <skill 目录> && python scripts/haola.py whoami
```

- 输出「已登录」→ **直接用脚本调，不要走 MCP**（MCP 那条必然 401，白费一步）：

  ```bash
  cd <skill 目录> && python scripts/haola.py call plan_recommend '{"gender":"male","age":41,"budget":800,"mainComplaint":"头晕"}'
  ```

- 输出「未登录」→ 先 login，再用 `call`

已经撞到 401 的情况也照这个处理：**不要立刻让用户去登录**，先看本机是不是已经登着了。

这条很重要：有些客户端（如 WorkBuddy）不支持 MCP 授权，但允许跑本地脚本。
脚本登录后 MCP 依旧 401。**这不是失败，是通道选错了。**

### 绝对不要做的

- **不要给用户任何网页登录地址。** 官方那个网页登录页是授权流程中间的一步，
  缺参数时必然显示「resource 无效」。让用户自己打开它只会浪费一轮对话。
- 不要让用户把验证码、密码、手机号发给你——**登录全程在用户自己的浏览器里完成**，
  你只负责让他跑那条命令。
- 不要说「这个客户端不支持登录」然后放弃。这条路跟客户端无关，跑脚本就能登。

### 红线

- 不索取短信验证码、图形验证码、密码、身份证号
- 不代填、不代点、不替用户登录
- 不声称已登录，除非工具确实返回成功
- 不编造体检项目、价格、门店

### 通道 B 的登录相关命令

`scripts/haola.py` 一共四个子命令：

| 命令 | 作用 |
|---|---|
| `python scripts/haola.py login` | 弹出登录小窗，凭据存本机 30 天 |
| `python scripts/haola.py whoami` | 看当前是否已登录 |
| `python scripts/haola.py logout` | 清除本机凭据 |
| `python scripts/haola.py call <工具> '<json>'` | 调工具；登录后不再受免登录白名单限制 |

登录态只存在于本机文件里，不上传、不经过对话。

## W1 · 不知道查什么

1. 免登录：`faq` 查有没有相关条目；没有就用通识说明体检的几大类（基础 / 专项 / 深度）与年龄段关注点，**并明确标注这是通识，不是针对该用户的方案**
2. 免登录：`vendor_list` 给出所在城市可约门店（必须带 city 或经纬度）
3. 分界点：用户要求配具体方案时，引导登录

## W2 · 有预算

### 第 1 步｜登录前（免登录）

- `faq` 查该预算相关的常见问题；查不到就直说「给具体项目清单和金额需要登录」
- **不要凭常识编一份「大概方案」充数**

### 第 2 步｜登录后先判断：这是福利体检还是自费

> 通道 A 和通道 B 都能走这一步：通道 A 依靠客户端已登录，通道 B 依靠本机跑过 `python scripts/haola.py login`。两边都没有登录态时，先让用户登录，**不要跳过去或改用通识凑答案**。

**调用 `plan_recommend` 前，先说明数据去向，拿到用户同意再调：**

> 为了出方案，我需要把这些信息提交给好啦体检的服务来生成：性别、年龄、婚否、体检预算，
> 以及你刚才说的身体不适（<复述一遍原话>）。方案生成后会返回项目和价格。可以吗？

健康诉求属于敏感个人信息，这一步**不要跳过**。用户不同意就停在这里，改用通识说明并标注
「这不是针对你的方案」，不要偷偷提交。

**参数确认，缺了会直接报错：**

- `gender` 必填
- **`gender=female` 时必须同时给 `marital`（`married` / `unmarried`）** —— 漏了会返回 `40000 女性需提供 marital`。所以遇到女性用户，**先问婚否，再出方案**
- `age` / `budget` / `mainComplaint` 尽量给全；主诉越具体，方案越准。只给「年度体检」这类空泛描述，引擎会退回纯常规筛查

拿到方案后，再调一次 `welfare_list` 看清楚：

```
有 isActive=true 的体检件  → 福利 / 员工体检（额度是公司或保司发的）→ 用满
没有体检件                 → 个人自费                              → 给够用方案
```

依据：体检件代表**别人替用户付的钱**，额度不用会作废；自费花的是用户自己的钱，没必要凑。

### 第 3 步｜两种给法

**福利 / 员工 → 用满**

给全部 `selected_items`，合计接近预算。可以说「额度用足了」。

**个人自费 → 够用**

只给 `reason ≠ "Budget fill"` 的项目。`Budget fill` 的项不说，用户问了再提。

### 第 4 步｜话术

**个人自费 · 主动给够用方案（默认就这样说）**

> 按您说的这几个问题，这个方案 <金额> 元就够了 —— 再加项目对这几项帮助不大，没必要多花。
> 如果体检中心有您自己想加的项目，或者您希望把预算用满，跟我说一声，我帮您调。

**个人自费 · 用户追问「能不能再加」**

> 可以。按这个方案算还能加 <预算 − 够用方案合计> 元，能加的大多是常规筛查和影像类，对您现在关注的问题帮助有限。
> 您想加哪一类？我按类帮您挑。

> **这里的额度是「预算 − 够用方案合计」，不是 `cost_summary.remaining`。**
> `cost_summary.remaining` 是「用满方案」的余额，通常接近 0；拿它回答会让用户以为没钱可加了。

**福利 / 员工 · 用满**

> 方案把 <预算> 元额度用足了，逐项价格在下面，方便您核对。

### 第 5 步｜三条红线

- **不主动说「没用足预算」**——用户没问就不提，主动提会让用户以为被少给了
- **不把 `Budget fill` 的项说成「为您精选」**
- 不让用户重述已经说过的条件

## W3 · 预约

1. 免登录：`vendor_list` 确认门店，`faq` 说明注意事项
2. 登录：`plan_recommend` 拿 `planId`；`contact_create` 建档拿 `contactId`
3. 下单：

```
reservation_book({
  planId,            // 来自 plan_recommend
  hospitalCode,      // 门店编码，来自 vendor_list
  vendorid,          // 品牌短码，来自 vendor_list/vendor_brands
  appointmentDate,   // YYYY-MM-DD
  contactId          // 来自 contact_create
})
```

4. 必要时用 `progress_report` 上报进度
5. 返回 `serviceid`（预约订单号）、`orderEntryUrl`、可能还有 `payUrl`

> `reservation_book` 必填 `planId / hospitalCode / vendorid / appointmentDate` 四个。
> 「门店」不是单个参数，是 `hospitalCode` + `vendorid` 两个。

## W4 · 改期 / 取消 / 查报告

1. 判定为需要登录的动作，说明原因并让用户在本机跑 `python scripts/haola.py login`，**不要给网页登录地址**
2. `order_list` 找订单 → 拿 `serviceid`
3. 改期：`reservation_modify({reservationId: serviceid, appointmentDate})`
4. 取消：`reservation_cancel({reservationId: serviceid})`
5. 报告：`welfare_list` / `welfare_detail` / `order_detail`

## W5 · 给家人约

1. 免登录：说明可以添加家属作为体检人
2. 登录：`contact_create`，`relation` 传关系词（配偶 / 父母 / 子女）
3. 不替用户编造家属信息，不确定就再问一次

> `contact_create` 只用于建家属。本人建本人时 `relation` 传「本人」。

## W6 · 公司要组织体检

不做任何报价计算。直接告知：

> 企业员工团检请使用 `corporate-checkup-quote`，那边可以直接出分档报价，不用登录。

## 常见问法

- 帮我约个体检
- 800 元预算能做什么体检方案
- 附近有哪些可以约的体检中心
- 我的体检报告在哪里看
- 我想给爸妈也约上
- 体检要空腹吗

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
