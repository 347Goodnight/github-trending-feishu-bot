# 🔥 GitHub Trending 飞书日报机器人

每天自动抓取 GitHub Trending 热门项目，通过 Coze AI 生成日报，推送到飞书群。

## ✨ 功能特性

- 🤖 自动抓取 GitHub 每日热门项目
- 🧠 调用 Coze AI 生成技术日报（带颜色高亮）
- 📱 推送到飞书群机器人（富文本卡片）
- ⏰ GitHub Actions 定时自动执行（每晚 10 点）
- 🔄 支持手动触发
- 🛡️ 内置兜底报告（Coze 失败时自动生成基础报告）
- 🎨 自动删除重复标题，避免卡片头部和内容重复

## 📁 项目结构

```
github-trending-feishu-bot/
├── .github/
│   └── workflows/
│       └── daily.yml       # GitHub Actions 配置
├── .gitignore              # Git 忽略文件
├── LICENSE                 # MIT 许可证
├── main.py                 # 主程序
├── requirements.txt        # Python 依赖
└── README.md               # 项目说明
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
| `COZE_BOT_ID` | ✅ | Coze Bot ID |
| `HTTP_PROXY` | ❌ | HTTP 代理（可选）|
| `HTTPS_PROXY` | ❌ | HTTPS 代理（可选）|

### Step 3: 获取配置信息

#### 获取飞书 Webhook

1. 打开飞书群聊 → 设置 → 群机器人 → 添加机器人
2. 选择 **自定义机器人**
3. 复制 Webhook 地址

#### 获取 Coze Token 和 Bot ID

1. 访问 [Coze 平台](https://www.coze.cn/)
2. 创建一个 Bot
3. 点击 **发布** → **API 访问**
4. 复制 **Bot ID** 和 **Personal Access Token**

### Step 4: 测试运行

1. 打开 GitHub 仓库 → **Actions** 标签
2. 找到 `Daily GitHub Trending Report` 工作流
3. 点击 **Run workflow** 手动触发
4. 检查飞书群是否收到消息

## 📝 输出示例

飞书卡片消息格式：

```
┌─────────────────────────────────────────┐
│  🔥 GitHub 每日热门项目 - 2024-01-15    │
├─────────────────────────────────────────┤
│                                         │
│  📊 今日趋势                            │
│  - 今日热门项目覆盖 AI、开发工具...     │
│  - 开发者效率提升类工具持续受到关注     │
│                                         │
│  **1. microsoft/markdown** · Python     │
│  <font color='F5A623'>⭐ 97,896</font> |   │
│  <font color='8C8C8C'>🍴 5,997</font> |     │
│  <font color='FF0000'>📈 2,353 today</font>   │
│  • Description: Python tool for...      │
│  • Link: https://github.com/...         │
│                                         │
│  ...                                    │
│                                         │
│  🤖 由 GitHub Actions + Coze AI 自动生成│
└─────────────────────────────────────────┘
```

**颜色说明**：
- 🟡 **黄色** `F5A623` - 总 Stars
- ⚪ **灰色** `8C8C8C` - Forks
- 🔴 **红色** `FF0000` - 今日新增

## ⏰ 定时配置

默认每天晚上 **10:00 (北京时间)** 自动运行。

如需修改时间，编辑 `.github/workflows/daily.yml`：

```yaml
on:
  schedule:
    # UTC 时间 14:00 = 北京时间 22:00
    - cron: '0 14 * * *'
```

常用时间参考：
- `0 14 * * *` - 北京时间 22:00 (晚上10点)
- `0 1 * * *` - 北京时间 09:00 (早上9点)
- `0 3 * * *` - 北京时间 11:00 (早上11点)

## 🛠️ 常见问题

### Q1: 为什么显示"兜底模式"？

**原因**：Coze API 调用失败了

**可能原因**：
- `COZE_API_TOKEN` 或 `COZE_BOT_ID` 配置错误
- Coze 服务暂时不可用
- 网络问题

**解决**：
- 检查 Secrets 配置是否正确
- 查看 Actions 日志中的具体错误信息

### Q2: 标题重复了怎么办？

代码已自动处理！`remove_duplicate_title()` 函数会自动删除 Coze 生成的重复标题，只保留卡片头部的标题。

### Q3: 如何只使用本地模式（不调用 Coze）？

可以修改 `main.py`，直接调用 `build_fallback_report()` 而不调用 Coze。但这样内容会比较简单，只有项目列表没有 AI 总结。

### Q4: GitHub Trending 抓取失败？

**现象**：`No repositories parsed from GitHub Trending page.`

**解决**：
- 添加代理配置（`HTTP_PROXY` / `HTTPS_PROXY`）
- 检查 GitHub 页面结构是否变化

## 🔧 本地测试

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量（Windows PowerShell）
$env:FEISHU_WEBHOOK="你的飞书webhook"
$env:COZE_API_TOKEN="你的coze token"
$env:COZE_BOT_ID="你的bot id"

# 运行
python main.py
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 PR！
