---
name: haola-checkup
description: 体检方案与预约。当用户提到体检、体检安排、体检报价、体检方案、体检套餐、团检、员工体检、入职体检、体检预约、体检多少钱、体检项目怎么选时使用。企业场景按人均预算出分档方案，个人场景按年龄性别症状预算出定制方案，两种情况都能预约门店并查订单。
license: MIT
---

# 好啦体检 Skill

把体检需求变成一份**能落地的方案**，和**一个能完成的预约**。

本 Skill 自带一个零依赖的 Python 客户端，直接调用好啦体检的 MCP 服务（Streamable HTTP），不需要用户预先配置 MCP。

---

## 什么时候用

- 「帮我安排个体检」「体检怎么安排」
- 「体检方案」「体检项目怎么选」「体检套餐」
- 「体检多少钱」「预算 XXX 做体检」「体检报价」
- 「公司要给员工体检」「团检」「200 人团检怎么弄」
- 「入职体检」「帮我约个体检」
- 「体检前要注意什么」「体检报告怎么看」

## 什么时候不用

- 用户在问**疾病诊断或治疗** —— 那是医疗行为，不是体检安排
- 只是要**体检常识科普**、不涉及具体方案或预约 —— 直接回答，不必调用

---

## 怎么调

### 前提

- 有 Python 3.9+（不要装任何第三方包）
- 三种方式任选：
  1. 本仓库里直接跑：`python scripts/haola.py …`
  2. `pip install haola-checkup` 后跑：`haola-checkup …`
  3. 在自己的代码里 `from haola_checkup import HaolaMCP`

### 端点

```
https://ai.ihaola.com.cn/api/mcp/haola-pe
```

- 传输：Streamable HTTP
- **匿名即可出方案和报价**
- **预约、订单、报告需要用户令牌**（手机号 + 短信验证码）

### 命令速查

```bash
# 连通性
python scripts/haola.py ping

# 看有哪些工具
python scripts/haola.py tools

# 企业团检报价（匿名可用）
python scripts/haola.py quote --budget 1500 --concerns "久坐、三高、亚健康"

# 调用任意工具
python scripts/haola.py call vendor_list '{"city":"北京"}'

# 需要登录的工具：先拿到令牌再传
HAOLA_TOKEN=<token> python scripts/haola.py call plan_recommend '{"gender":"male","age":41,"budget":800}'
```

---

## 四条主流程

### ① 企业团检报价（匿名）

```bash
python scripts/haola.py quote --budget 1500 --concerns "久坐、三高、亚健康"
```

等价于调 `plan_quotation`：

```json
{"quotes": [{"tier": "员工档", "budget": 1500,
             "healthConcerns": "久坐、三高、亚健康",
             "populations": ["man", "lady", "girl"]}]}
```

- `budget` 是**人均**预算（元），必填
- `populations`：`man` 男 / `lady` 女已婚 / `girl` 女未婚
- 多档预算就给多个 `quotes` 元素，一次拿到对比

返回 `data.list[].planList[]`，每项含 `population`、`price`、`items`、`planId`。

### ② 个人定制方案（需令牌）

```bash
HAOLA_TOKEN=xxx python scripts/haola.py call plan_recommend \
  '{"gender":"male","age":41,"budget":800,"mainComplaint":"血糖偏高、过敏性鼻炎、轻度脂肪肝"}'
```

返回 `data.selected_items`（每项带 `constraintId`）与 `planId`。

> 要给家人安排：先 `contact_list` 看已有就诊人，没有就 `contact_create` 建。

### ③ 选门店并预约（需令牌）

```bash
HAOLA_TOKEN=xxx python scripts/haola.py call vendor_list '{"city":"北京"}'
HAOLA_TOKEN=xxx python scripts/haola.py call reservation_book \
  '{"planId":"…","hospitalCode":"…","vendorid":"health100","appointmentDate":"20261201","contactId":"…"}'
```

- `appointmentDate` 格式是 **`YYYYMMDD`**，不是 `2026-12-01`
- 返回 `serviceid` 是订单号
- **`rsvStatus=reserved` 才算预约成功**；`status=created` 只代表订单已建、待支付或待预约

### ④ 订单 / 体检件 / 注意事项（需令牌）

```bash
HAOLA_TOKEN=xxx python scripts/haola.py call order_list '{}'
HAOLA_TOKEN=xxx python scripts/haola.py call order_detail '{"serviceid":"…"}'
HAOLA_TOKEN=xxx python scripts/haola.py call cautions '{"serviceid":"…"}'
```

`cautions` 返回检前注意事项：空腹、用药、禁忌。

---

## 在代码里用

```python
from haola_checkup import HaolaMCP, AuthRequired

with HaolaMCP() as mcp:                      # 匿名
    result = mcp.quote(800, "久坐、三高")
    for p in result["data"]["list"][0]["planList"]:
        print(p["population"], p["price"], p["planId"])

try:                                          # 需要登录
    with HaolaMCP(token="…") as mcp:
        plan = mcp.recommend("male", age=41, budget=800, complaint="血糖偏高")
except AuthRequired as e:
    print("需要授权：", e.resource_metadata)
```

---

## 回答用户时的三条规矩

1. **不要自己编项目、编价格、编门店。** 所有方案和价格必须来自工具返回；返回里没有的就说没有。
2. **不要把「报价」说成「预约成功」。** 匿名出的只是方案；真预约必须有 `serviceid` 且 `rsvStatus=reserved`。
3. **报价要分人群说。** 男 / 女已婚 / 女未婚分开列，不要合成一个平均价。

---

## 出错对照

| 现象 | 原因与处理 |
|---|---|
| 退出码 `3`，提示需要登录 | 该工具要令牌。引导用户走 OAuth，或先拿到 token 放 `HAOLA_TOKEN` |
| `-32003 Too many requests` | 调用太快，等 20–45 秒再试 |
| `预订失败` | 门店不支持该方案里的部分项目，换门店或换方案 |
| 日期格式报错 | `appointmentDate` 要用 `YYYYMMDD` |
| 退出码 `4` | 业务错误，看输出的 `message` 字段 |

---

## 覆盖与边界

- 合作体检机构 800+ 家，覆盖 240+ 城市，其中 **540+ 家已接入 API 可被直接预约**
- 体检服务每年 10 万人次，健康测评累计 3500 万人次
- 实际体检由合作机构提供，均持《医疗机构执业许可证》
- 好啦**不做诊断、不做治疗建议**

## 更多

- 工具全清单：`tools/tools.json`（25 个）
- 接入示例：`examples/`
- 官网：https://www.ihaola.com.cn/
- AI 入口：https://www.ihaola.com.cn/llms.txt
