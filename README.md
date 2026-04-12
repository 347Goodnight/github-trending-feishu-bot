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
- 🎨 自动删除重复标题，避免卡片头部和内容重复

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

## 📝 输出说明

正常情况下，飞书卡片会显示 Coze 生成的日报正文。

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
- Coze Chat 创建成功，但后续消息列表中没有取到 assistant 正文
- Coze Workflow 已配置，但仓库 Secrets 中没有设置 `COZE_WORKFLOW_ID`
- 网络波动、代理问题或 Coze 服务临时异常

建议排查顺序：

1. 检查仓库 Secrets 是否完整，尤其是 `COZE_API_TOKEN`、`COZE_BOT_ID`、`COZE_WORKFLOW_ID`
2. 手动运行 GitHub Actions，查看日志中的这些字段是否显示为 configured
3. 先执行诊断脚本 `python diagnose_coze.py`
4. 确认 Coze 接口链路是否完整跑通：
   - `POST /v3/chat`
   - `POST /v3/chat/retrieve`
   - `POST /v1/conversation/message/list`
5. 如果 `retrieve` 成功但 `message/list` 没拿到 assistant 内容，通常就会触发兜底

### Q2: 如何确认当前是不是走了 Workflow 模式？

运行日志中会打印：

- `Using Coze Workflow API...`
- 或 `Using Coze Chat API...`

如果你已经设置了 `COZE_WORKFLOW_ID`，但日志里仍然显示 Chat API，优先检查：

- GitHub Secrets 里是否真的存在 `COZE_WORKFLOW_ID`
- `.github/workflows/daily.yml` 是否把它注入到了运行环境

### Q3: 标题重复了怎么办？

代码已自动处理。`remove_duplicate_title()` 会自动删除 Coze 正文里的重复标题，只保留卡片头部标题。

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
