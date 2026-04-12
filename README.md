# 🔥 GitHub Trending 飞书日报机器人

每天自动抓取 GitHub Trending 热门项目，通过 Coze AI 生成日报，推送到飞书群。

## ✨ 功能特性

- 🤖 自动抓取 GitHub 每日热门项目
- 🧠 调用 Coze AI 生成技术日报
- 📱 推送到飞书群机器人（富文本卡片）
- ⏰ GitHub Actions 定时自动执行（每晚 10 点）
- 🔄 支持手动触发
- 🛡️ 内置兜底报告（Coze 失败时自动生成基础报告）
- 🔍 内置诊断脚本，可检查 Coze Chat 全链路
- 🎨 自动去重正文标题，避免卡片头部和正文重复
- 🏅 自动规范项目格式，统一显示排名、Stars、Forks、简介和完整链接

## 📁 项目结构

```text
github-trending-feishu-bot/
├── .github/
│   └── workflows/
│       └── daily.yml         # GitHub Actions 配置
├── diagnose_coze.py          # Coze API 诊断脚本
├── main.py                   # 主程序
├── requirements.txt          # Python 依赖
├── tests/
│   └── test_main.py          # 最小回归测试
└── README.md                 # 项目说明
```

## 🚀 快速开始

### Step 1: Fork 或创建仓库

Fork 本仓库或创建一个新的 GitHub 仓库。

### Step 2: 配置 Secrets

在 GitHub 仓库中：**Settings → Secrets and variables → Actions → New repository secret**

添加以下 Secrets：

| Secret Name | 必填 | 说明 |
|------------|------|------|
| `FEISHU_WEBHOOK` | ✅ | 飞书机器人 Webhook 地址 |
| `COZE_API_TOKEN` | ✅ | Coze API Token |
| `COZE_BOT_ID` | Chat 模式必填 | Coze Bot ID |
| `COZE_WORKFLOW_ID` | Workflow 模式可选 | Coze Workflow ID，配置后优先走 Workflow |
| `HTTP_PROXY` | ❌ | HTTP 代理（可选） |
| `HTTPS_PROXY` | ❌ | HTTPS 代理（可选） |

说明：

- 如果只使用 Coze Chat API，需要配置 `COZE_API_TOKEN` 和 `COZE_BOT_ID`。
- 如果你已经有稳定的 Coze Workflow，建议额外配置 `COZE_WORKFLOW_ID`，运行时会优先使用它。

### Step 3: 获取配置信息

#### 获取飞书 Webhook

1. 打开飞书群聊 → 设置 → 群机器人 → 添加机器人
2. 选择 **自定义机器人**
3. 复制 Webhook 地址

#### 获取 Coze Token、Bot ID 和 Workflow ID

1. 访问 [Coze 平台](https://www.coze.cn/)
2. 创建或打开一个 Bot
3. 点击 **发布** → **API 访问**
4. 复制 **Personal Access Token**
5. 如果使用 Chat API，复制 **Bot ID**
6. 如果使用 Workflow API，复制 **Workflow ID**

### Step 4: 测试运行

1. 打开 GitHub 仓库 → **Actions** 标签
2. 找到 `Daily GitHub Trending Report` 工作流
3. 点击 **Run workflow** 手动触发
4. 检查飞书群是否收到消息

## 📝 卡片展示说明

正常情况下，飞书卡片会展示：

- `今日趋势分析`
- `TOP 10 热门项目`
- 每个项目的统一格式：

```text
🥇 1. microsoft/markitdown · Python
📈2352 stars | ⭐100457 stars | 🍴 6161 forks
简介：将 Office / PDF / HTML 等内容转换为 Markdown 的工具
链接：https://github.com/microsoft/markitdown
```

说明：

- 卡片头部已经带标题，正文会自动去掉重复标题。
- 项目排名默认使用 `🥇 / 🥈 / 🥉 / 🏅`。
- 统计行统一使用 `|` 作为分隔符。
- 字段名统一为 `简介` 和 `链接`。
- GitHub 链接会直接输出完整地址，而不是只显示 `GitHub` 文本。

如果 Coze 调用失败，系统会自动进入兜底模式，继续推送基础项目列表，保证当天不会断更。

## ⏰ 定时配置

默认每天晚上 **10:00（北京时间）** 自动运行。

如需修改时间，编辑 `.github/workflows/daily.yml`：

```yaml
on:
  schedule:
    # UTC 时间 14:00 = 北京时间 22:00
    - cron: '0 14 * * *'
```

常用时间参考：

- `0 14 * * *` - 北京时间 22:00
- `0 1 * * *` - 北京时间 09:00
- `0 3 * * *` - 北京时间 11:00

## 🛠️ 常见问题

### Q1: 为什么一直显示“兜底模式”？

这通常说明：

1. GitHub Actions 任务本身执行成功了。
2. 但 Coze 正文没有被成功取回。
3. 代码捕获异常后自动切到了本地兜底报告。

常见原因：

- `COZE_API_TOKEN`、`COZE_BOT_ID` 或 `COZE_WORKFLOW_ID` 配置错误
- Coze 服务临时异常
- 网络波动或代理问题

建议排查顺序：

1. 检查仓库 Secrets 是否完整，尤其是 `COZE_API_TOKEN`、`COZE_BOT_ID`、`COZE_WORKFLOW_ID`
2. 手动运行 GitHub Actions，查看日志中的配置是否显示为 configured
3. 执行诊断脚本 `python diagnose_coze.py`
4. 检查流式响应是否能拿到 `assistant preview`

### Q2: 标题重复了怎么办？

代码已自动处理。`remove_duplicate_title()` 会移除正文中与卡片头部重复的标题，只保留卡片头部标题。

### Q3: 项目展示格式不统一怎么办？

代码会在发送飞书卡片前统一格式：

- `TOP 5` 会自动规范成 `TOP 10`
- `简短描述` 会自动改成 `简介`
- `项目链接` 会自动改成 `链接`
- Markdown 链接会自动展开成完整 URL
- 项目编号会自动转成 `🥇 / 🥈 / 🥉 / 🏅`
- 统计行会统一成 `📈x stars | ⭐y stars | 🍴 z forks`

### Q4: 如何只使用本地模式（不调用 Coze）？

可以修改 `main.py`，直接调用 `build_fallback_report()` 而不调用 Coze。但这样内容会比较简单，只有项目列表，没有 AI 总结。

### Q5: GitHub Trending 抓取失败怎么办？

现象：

- `No repositories parsed from GitHub Trending page.`

解决：

- 添加代理配置：`HTTP_PROXY` / `HTTPS_PROXY`
- 检查 GitHub 页面结构是否变化

## 🔧 本地测试

```powershell
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
$env:FEISHU_WEBHOOK="你的飞书 webhook"
$env:COZE_API_TOKEN="你的 coze token"
$env:COZE_BOT_ID="你的 bot id"
$env:COZE_WORKFLOW_ID="你的 workflow id"

# 运行主程序
python main.py

# 运行诊断脚本
python diagnose_coze.py

# 运行最小回归测试
python -m unittest tests.test_main -v
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 PR。
