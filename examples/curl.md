# 直接用 curl 调

不需要任何客户端，三步就能看到真实返回。

---

## 1. 初始化会话

```bash
curl -s -D /tmp/h.txt https://ai.ihaola.com.cn/api/mcp/haola-pe \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'

SID=$(grep -i '^mcp-session-id:' /tmp/h.txt | tr -d '\r' | awk '{print $2}')
echo "session=$SID"
```

顺手通知服务端初始化完成：

```bash
curl -s https://ai.ihaola.com.cn/api/mcp/haola-pe \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "mcp-session-id: $SID" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'
```

---

## 2. 看有哪些工具

```bash
curl -s https://ai.ihaola.com.cn/api/mcp/haola-pe \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "mcp-session-id: $SID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

---

## 3. 匿名出一个团检方案

匿名可用，不需要任何 token：

```bash
curl -s https://ai.ihaola.com.cn/api/mcp/haola-pe \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "mcp-session-id: $SID" \
  -d '{
    "jsonrpc":"2.0","id":3,"method":"tools/call",
    "params":{
      "name":"plan_quotation",
      "arguments":{
        "quotes":[{
          "tier":"员工档",
          "budget":800,
          "healthConcerns":"久坐、三高、亚健康",
          "populations":["man","lady","girl"]
        }]
      }
    }
  }'
```

返回里重点看 `data.list[].planList[]`，每项包含 `population`、`price`、`items`、`planId`。

---

## 4. 看门店

```bash
curl -s https://ai.ihaola.com.cn/api/mcp/haola-pe \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "mcp-session-id: $SID" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"vendor_brands","arguments":{}}}'
```

---

## 5. 试着调一个需要登录的动作

会返回 `401`。这只说明「这一步要登录」，不是服务不可用：

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://ai.ihaola.com.cn/api/mcp/haola-pe \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "mcp-session-id: $SID" \
  -d '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"plan_recommend","arguments":{"gender":"male","age":41,"budget":800}}}'
```

期望输出 `401`。这类动作要引导用户到网页完成登录：

```
https://pe.ihaola.com.cn/auth/
```

填手机号 → 获取验证码 → 填图形验证码 → 收短信 → 填短信验证码 → 登录。
验证码只在网页上填，不经过对话，也不需要提供给任何客户端。

---

## 常见坑

| 现象 | 原因 |
|---|---|
| `406 Not Acceptable` | 少了 `Accept: application/json, text/event-stream` |
| 每一步都返回新 session | 没带 `mcp-session-id` 请求头 |
| 返回体以 `data:` 开头 | 正常，是 SSE 格式，把 `data: ` 前缀去掉再解析 JSON |
| `-32003 Too many requests` | 连续调用太快，间隔 20–45 秒再试 |
