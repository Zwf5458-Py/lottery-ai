# 🎰 六合彩智能分析系统

> 基于多维统计引擎 + AI 大模型的全栈轻量级彩票走势分析工具

> [!IMPORTANT]
> **免责声明**：本程序仅供统计学研究与学习交流。彩票为随机事件，AI 模型无法预测未来开奖结果。请理性对待，严禁非法博彩。

---

## 📖 项目简介

本系统深度聚焦澳门六合彩**特码（Special Number）**的多维度研究，集成了工业级统计引擎与多家 AI 大模型平台，通过加权算法 + AI 推理报告为用户提供可视化的走势分析。

### ✨ 核心亮点

- 🧠 **多平台 AI 引擎**：支持 Google Gemini、Nvidia NIM、OpenAI、本地模型等 10+ 平台一键切换
- 📊 **8 大统计维度**：大小、单双、冷热、尾数、波色、生肖路单、马尔可夫链、贝叶斯推断
- 🎯 **底层数学引擎出号**：号码由加权模拟器精准计算，AI 负责撰写逻辑自洽的推理报告
- 📸 **一键存图分享**：分析结果支持高清截图下载，自带水印
- 👥 **多用户权限体系**：管理员 / VIP / 普通用户 / 试用，积分制图表分析

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────┐
│                    前端 (HTML/CSS/JS)              │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ 统计图表  │ │ AI 模拟  │ │  系统设置面板     │  │
│  └────┬─────┘ └────┬─────┘ └────────┬─────────┘  │
├───────┼────────────┼────────────────┼─────────────┤
│       │   Flask 后端 (app.py)        │             │
│  ┌────┴────────────┴────────────────┴──────────┐  │
│  │    路由层 (API + 页面渲染 + 权限控制)         │  │
│  └──┬──────────┬──────────────┬────────────────┘  │
│  ┌──┴───┐  ┌───┴────────┐  ┌─┴──────────────┐    │
│  │统计   │  │ AI 引擎    │  │ 用户/积分/配置  │    │
│  │引擎   │  │(多平台适配) │  │   管理模块      │    │
│  └──┬───┘  └───┬────────┘  └─┬──────────────┘    │
│     │          │              │                    │
│  ┌──┴──────────┴──────────────┴──────────────┐    │
│  │          SQLite 数据库 (data/)              │    │
│  └────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

---

## 🧠 AI 推算引擎

### 马尔可夫链 (Markov Chain)
统计历史开奖中生肖与波色的接替规律，计算转移概率并转化为 0.5x ~ 2.5x 的权重因子。

### 高级 RLE 模式识别 (Run-Length Encoding)
- **长龙断龙**：自动探测连庄是否接近历史天花板（极限约 13 期），大幅提升反跳权重
- **天花板双向研判**：当某方向连续 N 次未突破 K 连时，同时提供"压制延续"和"蓄能突破"两种解读
- **锯齿震荡**：识别 1-2-1-2 单跳循环，根据防跳心理动态调整模拟概率

### 贝叶斯极值反弹 (Bayesian Inference)
结合真实历史最大遗漏值，当某生肖遗漏逼近极限时赋予指数级暴增的后验权重。突破历史纪录时标注 🚨 极端信号。

### 路单拐点动量体系
- 连续 **2 期**即触发强烈掉头预警（实质等同 3 连形态，历史极限约 5 连）
- 多维模式检测：波色连庄、生肖连庄、UDUDUD 交替、112112 分组节奏

---

## 📊 图表维度一览

| 维度 | 统计内容 | AI 关注点 |
|:-----|:---------|:----------|
| 🔥 冷热号码 | 近 N 期出现频次 TOP10 | 金色脉冲标注全场最大遗漏号 |
| 🎯 尾数分布 | 0-9 尾数出现频率 | 超长遗漏尾数标注 ⚠️ 回补信号 |
| 📐 大小走势 | ≥25 为大，<25 为小 K 线 | 天花板壁垒 + 长龙极值压力 |
| 🔢 单双走势 | 单/双 K 线连庄值 | 反转概率 + 天花板双向解读 |
| 🎨 波色推测 | 红蓝绿遗漏与极值反弹 | CDF 累积概率极端度 |
| 🐾 生肖路单 | Y 轴生肖排位折线 | 拐点预警 + 多维交替模式 |
| 🕸️ 马尔可夫 | 生肖转移概率矩阵 | 跃迁权重 TOP5 |
| 🎲 贝叶斯 | 12 生肖后验概率 | 突破历史极值标记 |

---

## 🚀 快速启动

### 方式一：Windows 本地开发（推荐）

```powershell
# 1. 克隆项目
git clone <仓库地址>
cd 六合彩

# 2. 创建虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
copy .env.example .env
# 编辑 .env 文件，填入你的 API Key

# 5. 启动服务
python app.py
```

访问：`http://127.0.0.1:5000`

### 方式二：Linux 本地开发

```bash
# 环境准备
sudo apt update && sudo apt install -y python3.12-venv

# 启动
cd /path/to/六合彩
bash start.sh dev
```

访问：`http://127.0.0.1:5000`

### 方式三：Docker 生产部署

```bash
sudo docker compose -p macau-mark-six up --build -d
```

### 常用运维命令

```bash
bash logs.sh error    # Gunicorn 错误日志
bash logs.sh access   # 访问日志
bash logs.sh ai       # AI 故障日志
bash logs.sh all      # 全部日志

curl http://127.0.0.1:5000/healthz   # 健康检查
```

---

## ⚙️ AI 平台配置

系统支持多种 AI 平台，在**系统设置 → AI 模型配置**中切换：

| 平台 | 说明 | 模型示例 |
|:-----|:-----|:---------|
| **Google Gemini** | 默认平台 | `gemini-2.5-pro`、`gemini-2.5-flash` |
| **Nvidia NIM** | 国内可达 | `z-ai/glm4.7`、`meta/llama-4-scout-17b-16e-instruct` |
| **OpenAI** | 需科学上网 | `gpt-4o`、`gpt-4o-mini` |
| **本地模型** | 离线可用 | 任意 OpenAI 兼容接口 |
| **自定义平台** | 支持扩展 | 在设置面板中添加任意平台和模型 |

### 环境变量配置

```env
# .env 文件
FLASK_SECRET_KEY=your-secret-key-here
GEMINI_API_KEY=your-gemini-key           # Google Gemini
```

> [!TIP]
> 也可以在登录后的**系统设置面板**中直接填写 API Key 和选择平台，无需编辑文件。Nvidia 平台的 Key 以 `nvapi-` 开头时会自动路由。

---

## 👥 用户权限体系

| 角色 | 权限 |
|:-----|:-----|
| **管理员** (admin) | 全功能 + 后台管理 + AI 免费 + 模拟他人登录 |
| **VIP** | 全功能 + AI 免费 + 自定义图表期数 |
| **普通用户** | AI 分析消耗积分，修改图表期数消耗积分 |
| **试用用户** | 有限功能体验 |

### 积分系统
- 每次 AI 分析消耗积分（管理员/VIP 免费）
- 修改统计图表期数消耗积分（冷热、尾数免费）
- 积分不足时自动提示充值

---

## 📁 核心文件结构

```
六合彩/
├── app.py                    # Flask 主应用 (路由 + API)
├── extensions.py             # Flask 扩展初始化
├── requirements.txt          # Python 依赖
├── config.json               # 全局配置
├── .env                      # 环境变量 (API Keys)
│
├── modules/                  # 核心业务模块
│   ├── ai_engine.py          # AI 引擎 (多平台适配 + Prompt 工程)
│   ├── statistics_engine.py  # 统计引擎 (贝叶斯/马尔可夫/RLE)
│   ├── simulator.py          # 加权模拟器 (底层出号)
│   ├── data_processor.py     # 数据采集与处理
│   ├── config_manager.py     # 配置管理
│   ├── auth.py               # 用户认证
│   └── points_manager.py     # 积分管理
│
├── static/                   # 前端静态资源
│   ├── css/style.css         # 全局样式
│   └── js/app.js             # 前端逻辑 (图表/设置/AI交互)
│
├── templates/
│   └── index.html            # 单页应用模板
│
├── data/                     # SQLite 数据库目录
├── Dockerfile                # Docker 构建
├── docker-compose.yml        # Docker Compose 编排
├── start.sh                  # Linux 启动脚本
└── logs.sh                   # 日志查看工具
```

---

## 🔧 技术栈

| 层级 | 技术 |
|:-----|:-----|
| 后端 | Python 3.12 + Flask 3.1 |
| 数据库 | SQLite (WAL 模式) |
| 缓存 | Flask-Caching (FileSystemCache) |
| AI | Google Gemini / Nvidia NIM / OpenAI 兼容 |
| 统计 | pandas + scikit-learn + numpy |
| 安全 | Flask-WTF (CSRF) + Flask-Limiter + PyJWT |
| 前端 | 原生 HTML/CSS/JS + Chart.js + html2canvas |
| 部署 | Gunicorn + Docker / 本地开发模式 |

---

## 📄 许可证

本项目仅供学习研究使用，未经授权不得用于商业用途。

*Powered by Google Gemini AI & Nvidia NIM & Advanced Statistics Engine*
