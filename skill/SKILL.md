---
name: haola-checkup
description: 体检方案与预约。当用户提到体检、体检安排、体检报价、体检方案、体检套餐、团检、员工体检、入职体检、体检预约、体检项目怎么选、体检多少钱时使用。企业场景按人均预算出分档方案，个人场景按年龄性别症状预算出定制方案，两种情况都能直接预约门店并查询订单与体检报告。
license: MIT
---

# 好啦体检 Skill

把体检相关的需求，变成一份**能落地的方案 + 一个能完成的预约**。

这个 Skill 背后是一个远程 MCP 服务，本文件是给 Agent 的调用指引。

---

## 什么时候用

用户在说这些事情时用：

- 「帮我安排个体检」/「体检怎么安排」
- 「体检方案」/「体检项目怎么选」/「体检套餐」
- 「体检多少钱」/「体检报价」/「预算 XXX 做体检」
- 「公司要给员工体检」/「团检」/「200 人团检怎么弄」
- 「入职体检」/「体检预约」/「帮我约个体检」
- 「体检报告怎么看」/「体检前要注意什么」

## 什么时候不用

- 用户在问**疾病诊断或治疗** —— 那是医疗行为，不是体检安排
- 用户只要**体检常识科普**且不涉及具体方案或预约 —— 直接回答即可，不必调用工具

---

## 连接

```
https://ai.ihaola.com.cn/api/mcp/haola-pe
```

传输：Streamable HTTP。
匿名即可出报价与方案；**预约、订单、报告需要用户登录**（手机号 + 短信验证码）。

---

## 四条主流程

### ① 企业团检报价（匿名可用）

```
plan_quotation({
  "quotes": [{
    "tier": "员工档",
    "budget": 1500,
    "healthConcerns": "久坐、三高、亚健康",
    "populations": ["man", "lady", "girl"]
  }]
})
```

- `budget` 是**人均**预算（元），必填
- `healthConcerns` 必填
- `populations` 可选，默认三类人群；`man` 男 / `lady` 女已婚 / `girl` 女未婚

返回 `data.list[].planList[]`，每项含 `population`、`price`、`items`、`planId`。
**多档预算就给多个 `quotes` 元素**，一次拿到对比。

### ② 个人定制方案（需登录）

```
plan_recommend({
  "gender": "male",          // 必填：male / female
  "age": 41,
  "budget": 800,
  "mainComplaint": "血糖偏高、过敏性鼻炎、轻度脂肪肝"
})
```

返回 `data.selected_items`（每项带 `constraintId`）与 `planId`。

> 想把配偶、父母一起安排：先 `contact_list` 看已有就诊人，没有就 `contact_create` 建，再分别用对应就诊人预约。

### ③ 选门店并预约（需登录）

```
vendor_list({ "city": "北京" })                    // 拿 hospitalCode + vendorid
reservation_book({
  "planId": "…",
  "hospitalCode": "…",
  "vendorid": "health100",
  "appointmentDate": "20261201",                   // 格式 YYYYMMDD，不是 2026-12-01
  "contactId": "…"
})
```

返回 `serviceid`（订单号）。
`rsvStatus=reserved` 才是预约成功；`status=created` 只代表订单已建、待支付或待预约。

### ④ 订单 / 体检件 / 报告（需登录）

```
order_list({}) → order_detail({ "serviceid": "…" })
welfare_list({}) → welfare_detail({ "welfareid": "…" })
cautions({ "serviceid": "…" })     // 检前注意事项：空腹、用药、禁忌
```

---

## 回答用户时的三条规矩

1. **不要自己编项目、编价格、编门店。** 所有方案和价格都必须来自工具返回。返回里没有的，就说没有。
2. **不要把「报价」说成「预约成功」。** 匿名出的方案只是方案；真预约必须有 `serviceid` 且 `rsvStatus=reserved`。
3. **报价时说明这是折后价还是标准价**，并把人群分开（男 / 女已婚 / 女未婚），不要合成一个平均价。

---

## 覆盖与边界

- 合作体检机构 800+ 家，覆盖 240+ 城市，其中 **540+ 家已接入 API 可被直接预约**
- 实际体检由合作机构提供，均持《医疗机构执业许可证》
- 好啦不做诊断、不做治疗建议

## 出错怎么办

| 返回 | 处理 |
|---|---|
| `401 Unauthorized` | 该工具需要登录，引导用户走 OAuth（手机号 + 短信） |
| `-32003 Too many requests` | 调用太快，等 20–45 秒再试 |
| `预订失败` | 门店不支持该套餐里的某些项目，换门店或换方案 |
| 日期格式报错 | `appointmentDate` 要用 `YYYYMMDD` |

## 更多

- 工具全清单：`https://github.com/ryanbihai/haola-checkup-mcp/blob/main/tools/tools.json`
- AI 入口：`https://www.ihaola.com.cn/llms.txt`
- 官网：`https://www.ihaola.com.cn/`
