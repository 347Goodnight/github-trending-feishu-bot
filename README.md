# 🔥 GitHub Trending 飞书日报机器人

每天自动抓取 GitHub Trending 热门项目，通过 Coze AI 生成中文日报，推送到飞书群。

## ✨ 功能特性

- 🤖 自动抓取 GitHub 每日热门项目
- 🧠 调用 Coze AI 生成中文技术日报
- 📱 推送到飞书群机器人
- ⏰ GitHub Actions 定时自动执行
- 🔄 支持手动触发
- 🛡️ 内置兜底报告（Coze 失败时自动生成基础报告）

## 📁 项目结构

```
github-trending-feishu-bot/
├── main.py              # 主程序
├── requirements.txt     # Python 依赖
├── README.md           # 项目说明
└── .github/
    └── workflows/
        └── daily.yml   # GitHub Actions 配置
```

## 🚀 快速开始

### Step 1: 新建 GitHub 仓库

Fork 本仓库或创建一个新的 GitHub 仓库。

### Step 2: 创建文件

创建以下 3 个文件：
- `main.py`
- `requirements.txt`
- `.github/workflows/daily.yml`

### Step 3: 复制代码

把项目中的代码完整复制到对应文件中。

### Step 4: 配置 Secrets

在你的 GitHub 仓库中：

**Settings → Secrets and variables → Actions → New repository secret**

添加以下 Secrets：

| Secret Name | 必填 | 说明 |
|------------|------|------|
| `FEISHU_WEBHOOK` | ✅ | 飞书机器人 Webhook 地址 |
| `COZE_API_TOKEN` | ✅ | Coze API Token |
| `COZE_BOT_ID` | ⚪ | Coze Bot ID（Chat 模式）|
| `COZE_WORKFLOW_ID` | ⚪ | Coze Workflow ID（Workflow 模式，二选一）|
| `HTTP_PROXY` | ❌ | HTTP 代理（可选）|
| `HTTPS_PROXY` | ❌ | HTTPS 代理（可选）|

**注意**：`COZE_BOT_ID` 和 `COZE_WORKFLOW_ID` 至少配置一个。

### Step 5: 提交代码

```bash
git add .
git commit -m "Initial commit"
git push origin main
```

### Step 6: 手动测试运行

1. 打开 GitHub 仓库
2. 点击 **Actions** 标签
3. 找到 `Daily GitHub Trending to Feishu` 工作流
4. 点击 **Run workflow** 手动触发

### Step 7: 检查飞书群

如果一切正常，你的飞书群就会收到日报消息！🎉

---

## 🔧 配置详解

### 1. 获取飞书机器人 Webhook

1. 打开飞书群聊 → 设置 → 群机器人 → 添加机器人
2. 选择 "自定义机器人"
3. 复制 Webhook 地址（格式：`https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`）

### 2. 获取 Coze API Token

#### 方式一：Chat API（简单推荐）

1. 访问 [Coze 平台](https://www.coze.cn/)
2. 创建一个 Bot
3. 在 **发布** → **API 访问** 中获取：
   - **Bot ID**
   - **API Token**（Personal Access Token）

#### 方式二：Workflow API（更灵活）

1. 在 Coze 创建一个 **工作流**
2. 添加输入参数（如 `input`, `date`, `repos_count`）
3. 添加 LLM 节点处理日报生成
4. 发布工作流，获取 **Workflow ID**

---

## 🖥️ 本地运行测试

你也可以在本地先测试：

```bash
# 安装依赖
pip install -r requirements.txt
```

**Mac/Linux:**

```bash
export FEISHU_WEBHOOK='你的飞书webhook'
export COZE_API_TOKEN='你的coze token'
export COZE_BOT_ID='你的bot id'
# 或 export COZE_WORKFLOW_ID='你的工作流id'
python main.py
```

**Windows PowerShell:**

```powershell
$env:FEISHU_WEBHOOK="你的飞书webhook"
$env:COZE_API_TOKEN="你的coze token"
$env:COZE_BOT_ID="你的bot id"
# 或 $env:COZE_WORKFLOW_ID="你的工作流id"
python main.py
```

---

## ⏰ 定时配置

默认每天早上 9:00 (北京时间) 自动运行。

如需修改时间，编辑 `.github/workflows/daily.yml` 中的 cron 表达式：

```yaml
on:
  schedule:
    # 格式：分 时 日 月 周 (UTC 时间)
    - cron: '0 1 * * *'  # UTC 1:00 = 北京时间 9:00
```

常用时间参考：
- `0 1 * * *` - 北京时间 9:00
- `0 3 * * *` - 北京时间 11:00
- `30 22 * * *` - 北京时间 6:30（次日）

---

## 📝 输出示例

飞书群收到的消息格式：

```
🔥 《GitHub 每日热门项目速览 - 2024-01-15》

📊 今日趋势
- 今日热门项目覆盖 AI、开发工具、自动化与基础设施等方向。
- 开发者效率提升类工具持续受到关注。
- 开源 AI 应用与工程化能力仍然是热点。

🏆 热门项目 TOP 10

**1. owner/repo-name**
- 简介：项目的中文简介
- 语言：Python
- 今日新增：⭐ 1,234 stars today
- 链接：https://github.com/owner/repo-name

...

🎯 重点关注
- **owner/repo-name**：当前热度较高，值得进一步关注其应用场景与社区增长。

---
⚠️ 注：Coze AI 服务暂时不可用，以上为自动生成的兜底报告。
```

---

## 🛠️ 常见问题

### Q1: GitHub Trending 抓取失败？

**现象：**
```text
No repositories parsed from GitHub Trending page.
```

**原因：**
- GitHub 页面结构变了
- 被风控
- 地区网络问题

**解决：**
- 添加代理配置（`HTTP_PROXY` / `HTTPS_PROXY`）
- 打印 `resp.text[:2000]` 查看返回内容
- 更新 `main.py` 中的 CSS 选择器

---

### Q2: Coze API 调用失败？

**现象：**
```text
Coze API error: 401
```

**原因：**
- Token 错误
- Bot ID 或 Workflow ID 错误
- 接口域名不对

**解决：**
- 检查 Token 和 ID 是否正确
- 查看 Coze 开放平台的 API 文档
- 国内版和国际版的域名可能不同

**调试方法：**

查看 GitHub Actions 日志中的这一句：
```python
log(f"Coze response: {json.dumps(data, ensure_ascii=False)[:1000]}")
```

它会打印前 1000 个字符。根据返回的 JSON 结构，调整 `call_coze_generate_report()` 中的解析逻辑。

如果你把 Coze 返回的 JSON 发给我，我可以帮你改成准确适配版。

---

### Q3: 飞书发送失败？

**现象：**
```text
Feishu send failed
```

**原因：**
- Webhook 地址错误
- 群机器人安全设置限制了关键词/IP
- 消息过长

**解决：**
- 检查飞书机器人设置
- 暂时关掉安全限制测试
- 只发 Top 5 试试

---

### Q4: 不想依赖 Coze API 是否稳定？

当前代码已经内置兜底逻辑：
- Coze 失败时，自动使用 Python 本地模板拼接日报
- 照样能发飞书

这意味着：
- 抓取成功 = 至少能收到日报
- Coze 成功 = 收到更智能的总结版日报

这个设计适合生产环境。

---

## 🔮 建议的增强版本

当前版本跑起来后，可以继续升级：

### 升级 1：支持指定语言榜单

把 URL 改成指定语言：

```python
GITHUB_TRENDING_URL = "https://github.com/trending/python?since=daily"
```

或做成环境变量 `TRENDING_LANGUAGE=python`。

### 升级 2：飞书卡片消息

比 text 模式更好看，支持富文本、按钮、图片等。

### 升级 3：缓存日报到 Markdown 文件

同时提交到仓库，方便归档和搜索。

### 升级 4：增加去重与历史趋势分析

- 连续 3 天上榜项目
- 新上榜项目
- 上升最快项目

这些都可以交给 Coze 分析。

---

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 PR！

---

## 💡 提示

如果你的 Coze 接口地址不是默认的，可以修改 `main.py` 中的：

```python
# Chat API
url = "https://api.coze.cn/v3/chat"

# Workflow API
url = "https://api.coze.cn/v1/workflow/run"
```

国内版和国际版的域名可能不同，请根据你的 Coze 平台文档调整。
