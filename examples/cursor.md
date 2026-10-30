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

## 如果在 Cursor 里第一次调用需要登录的工具

比如你说「帮我预约」时它调 `reservation_book`，会触发 OAuth：

1. Cursor 弹出一个授权窗口
2. 跳转到 `www.ihaola.com.cn` 的授权页
3. **手机号 + 短信验证码**登录
4. 同意授权后自动回到 Cursor

授权一次，后续同等权限的调用不再重复登录。

> 如果 Cursor 没有弹出授权窗口，多半是它版本偏旧、不认识 `resource_metadata`。先用 `examples/curl.md` 里的 `mcp-remote` 桥接方式顶上。
