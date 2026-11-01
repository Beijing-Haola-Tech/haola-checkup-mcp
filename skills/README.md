# Skills

两个 Skill，共用同一个 MCP 服务。每个目录都是一个**自包含的 skill 包**：`SKILL.md` 是给
模型读的说明书，`scripts/` + `src/` 是零依赖 Python 客户端（客户端不支持 MCP 时用它直连），
`mcp.json` 是客户端配置片段。装到哪都能单独跑，不需要仓库里别的东西。

| 目录 | 显示名 | 面向 | 干什么 |
|---|---|---|---|
| [`corporate-checkup-quote/`](corporate-checkup-quote/SKILL.md) | 好啦体检 · 企业团检方案与报价 | HR / 行政 / 采购 | 按人均预算出多档团检方案，逐档逐人群列项目与折后价；查城市与门店覆盖；合同发票转商务 |
| [`personal-checkup-booking/`](personal-checkup-booking/SKILL.md) | 好啦体检 · 个人体检预约 | 个人 / 员工 / 代家人 | 按年龄、性别、婚否、预算出个性化方案；选门店、预约、改期、取消；查订单与报告 |

## 给 Agent / LLM 直接取

不需要克隆仓库，读这两个文件即可：

- 企业团检　<https://raw.githubusercontent.com/Beijing-Haola-Tech/haola-checkup-mcp/main/skills/corporate-checkup-quote/SKILL.md>
- 个人体检　<https://raw.githubusercontent.com/Beijing-Haola-Tech/haola-checkup-mcp/main/skills/personal-checkup-booking/SKILL.md>

`raw.githubusercontent.com` 取不到时，用 GitHub 页面地址：

- <https://github.com/Beijing-Haola-Tech/haola-checkup-mcp/blob/main/skills/corporate-checkup-quote/SKILL.md>
- <https://github.com/Beijing-Haola-Tech/haola-checkup-mcp/blob/main/skills/personal-checkup-booking/SKILL.md>

## 安装

在 [ClawHub](https://clawhub.ai) 搜「好啦体检」，两个都在：

- <https://clawhub.ai/ryanbihai/skills/corporate-checkup-quote>
- <https://clawhub.ai/ryanbihai/skills/personal-checkup-booking>

## 别在这里改

这两个目录是构建产物，由内部流水线生成后同步过来。直接改会被下次同步覆盖——
要改措辞去改源文件，改完重新构建再同步。
