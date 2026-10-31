# 在 Cursor 里接

Cursor 原生支持远程 MCP（Streamable HTTP），不需要转发。

---

## 方法一：配置文件

打开（或新建）：

- macOS / Linux：`~/.cursor/mcp.json`
- Windows：`%USERPROFILE%\.cursor\mcp.json`

写入：

```json
{
  "mcpServers": {
    "haola-checkup": {
      "url": "https://ai.ihaola.com.cn/api/mcp/haola-pe"
    }
  }
}
```

重启 Cursor，在 **Settings → MCP** 里应能看到 `haola-checkup`，绿灯即可用。

---

## 方法二：界面添加

1. `Cmd/Ctrl + Shift + J` 打开 Cursor Settings
2. 左侧选 **MCP**
3. **Add new global MCP server**
4. 类型选 `http`（或 `streamable-http`），URL 填 `https://ai.ihaola.com.cn/api/mcp/haola-pe`

---

## 试一句话

在 Chat 里输入：

> 帮我给一个 200 人的公司出体检方案，人均预算 1500，员工以久坐办公为主，在北京。

正常的话，Cursor 会自动调用 `plan_quotation`，并把每档方案（男 / 女已婚 / 女未婚）和逐项价格列出来。

---

## 遇到需要登录的动作

比如你说「帮我预约」时它调 `reservation_book`，会提示这一步要登录：

1. 打开登录页 `https://pe.ihaola.com.cn/auth/`
2. 填手机号 → 点「获取验证码」→ 填弹出的图形验证码 → 收短信 → 填短信验证码 → 登录
3. 回到 Cursor 继续

验证码只在网页里填，不用告诉 AI。

> 如果你的 Cursor 版本较旧、不支持远程 MCP，改用 `mcp-remote` 桥接，见 `examples/curl.md` 末尾。
