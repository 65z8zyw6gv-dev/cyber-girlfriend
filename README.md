# 赛博女友 · 网页版 AI 聊天服务

一个基于 Flask + 火山引擎（方舟）大模型的网页版 AI 女友聊天应用，单文件即可运行，自带情感表情系统和工具调用能力。

## ✨ 功能特点

- 💬 网页聊天界面，即开即用
- 🎭 情感识别系统：根据对话内容自动切换表情状态（害羞、开心、撒娇等）
- 🛠️ 内置工具调用：计算器、当前时间等 Function Calling
- 📚 支持挂载个人知识库文档，AI 能记住"你"的信息
- ✅ 待办清单管理
- 🔧 单文件部署，无需前端构建

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

到 [火山引擎方舟控制台](https://console.volcengine.com/ark) 创建推理接入点，获取 API Key。

**推荐用环境变量（安全）：**

```bash
# Windows
setx ARK_API_KEY "你的API_KEY"
# 设置后重新打开终端
```

或在 `app.py` 配置区直接填入（注意不要提交到公开仓库！）。

### 3. 运行

```bash
python app.py
```

浏览器打开 http://127.0.0.1:8080

## ⚙️ 配置说明

| 配置项 | 说明 |
|---|---|
| `API_KEY` | 火山引擎 API Key（建议走环境变量） |
| `MODEL_ID` | 模型 ID 或接入点 ID（ep-xxx） |
| `BASE_URL` | 方舟 API 地址，默认官方地址 |
| `DOC_PATH` | 个人知识库文档路径（txt） |
| `PORT` | 服务端口，默认 8080 |

## 📁 项目结构

```
cyber-girlfriend/
├── app.py              # 主程序（后端 + 前端页面，单文件）
├── requirements.txt    # Python 依赖
└── README.md
```

## ⚠️ 安全提示

- **永远不要**把真实 API Key 提交到 Git 仓库
- 个人笔记、待办数据已在 `.gitignore` 中排除

## 📄 License

MIT
