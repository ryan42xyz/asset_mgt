# 个人资产管理平台

[English](README.md) · **[中文]**

一个自托管的美股投资仪表盘——之所以自己做，是因为没有现成工具能满足我的需求，而 AI 让这件事变得切实可行。

---

## 为什么要自己做

我的资产很分散：美股券商账户、国内银行账户、保险产品、微信零钱，以及分布在两家券商的 ETF 持仓。主流的资产追踪工具要么不支持中国资产，要么需要你上交券商账号密码，要么需要付费订阅才能看自己的数据。

更深层的问题是投资策略本身。我遵循一套规则驱动的配置框架：六个资产类别固定目标权重、当市场真正承压时触发风险闸门（标普 500 低于 200 日均线**且** VIX > 30）、随着从积累期迈向提前退休而切换策略阶段。这套逻辑足够具体，没有任何现成仪表盘能正确追踪它。

所以我自己搭了一个。

---

## AI 在哪里发挥作用

有两个地方，AI 让原本不可能的事情变成了可能。

**构建系统本身。** 整个代码库都是在 AI 辅助下完成的。策略逻辑、OCR 流水线、再平衡计算——如果单打独斗，这些可能需要几周时间。有了 LLM 作为结对编程搭档，一个可工作的原型几天内就成型了。代码质量也更好：边界情况会被发现，API 设计更清晰，错误处理比我在时间压力下独立写出来的要更完善。

**把数据导进来。** 这是更难的问题，也是 AI 价值最明显的地方。

大多数金融数据被锁在 app 里。你的券商没有开放 API；你的银行"导出"按钮生成的 PDF 没有工具能解析；你的保险公司只有手机 app，没有网页版。数据就在那里——你能**看到**它——但没有任何程序能直接消费它。

解决方案：**截图 → LLM → 结构化数据 → 人工审核 → 导入**。

1. 对券商/银行 app 的持仓页面截图（手机截图、网页截图都行）
2. 将截图发给支持视觉的 LLM，用提示词提取持仓数据为 JSON
3. 人工审核输出结果——发现识别错误的数字，修正股票代码
4. 通过 API 导入

这个流程有一个关键特性：**人工参与是 feature，不是 bug**。每个数字在进入系统之前都经过你的眼睛。你能抓住 OCR 把 28 股识别成 28.0 的错误，或者成本价从错误列提取的问题。人工审核步骤是快速的合理性校验，不是负担——它保证你分析的是你亲眼确认过的数据。

最终效果：这个平台能从**任何**金融机构导入数据，不局限于有官方 API 的机构，只要你能对账户页面截图。

---

## 功能

- **投资组合仪表盘** — 实时持仓、盈亏、当前配置 vs 目标配置图表，多账户多币种（USD/CNY）统一展示
- **风险闸门监控** — 实时追踪标普 500 vs 200 日均线及 VIX，显示风险闸门状态
- **再平衡建议** — 计算各类别偏离目标权重的幅度，告诉你买什么卖什么
- **SPY 行情仪表盘** — 标普 500 价格及技术指标视图
- **FIRE 计算器** — 根据当前储蓄率和目标金额，测算财务独立所需时间

## 截图

![投资组合仪表盘](docs/screenshots/dashboard-portfolio.png)

![SPY 行情仪表盘](docs/screenshots/dashboard-spy-market.png)

![FIRE 计算器](docs/screenshots/dashboard-fire-calculator.png)

---

## 数据流

```
金融账户（券商 app、银行 app、截图）
        │
        ▼
截图 + LLM 提取（OCR 服务）
        │
        ▼
人工审核 + 修正
        │
        ▼
导入 API
        │
        ▼
SQLite（app.db）— 持仓、价格历史、风险闸门状态
        │
雅虎财经（实时价格）──► 内存缓存
        │
        ▼
FastAPI — 策略引擎、再平衡计算
        │
        ▼
浏览器仪表盘
```

---

## 投资策略

平台围绕一套具体的配置框架构建，可在 `app/config.py` 中修改。

### 目标配置

| 类别 | 标的 | 目标权重 |
|---|---|---|
| 现金 / 短期债券 | DUSB, SGOV | 25% |
| 标普等权重 | RSP, SPYV | 20% |
| 标普市值权重 | SPY, VOO | 15% |
| 高贝塔 | NVDA, QQQ | 15% |
| 全球（除美国） | DFAW | 10% |
| 防御性资产 | BRK.B, GLD | 10% |

### 风险闸门

同时满足以下**两个**条件时触发：
- 标普 500 收盘价低于 200 日移动均线
- VIX > 30

标普 500 连续 10 个交易日收盘价高于 200 日均线后解除。逻辑：单一条件是噪音，两个条件同时满足才代表真正值得应对的市场压力。

---

## 快速开始

**环境要求：** Python 3.11+（无需 Docker）

```bash
git clone https://github.com/ryan42xyz/asset_mgt
cd asset_mgt

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
./start.sh
```

打开 **http://localhost:8000**。首次启动时会自动创建 demo 用户。

### 导入持仓数据

**方式 A — 直接调 API（持仓少时最快）**
```bash
curl -X POST http://localhost:8000/api/v1/portfolio/1/holdings \
  -H "Content-Type: application/json" \
  -d '{"symbol":"VOO","shares":10,"cost_basis":450.00,"broker_name":"你的券商"}'
```

**方式 B — 截图流水线（适用于无 API 的券商/银行）**
1. 对账户持仓页面截图
2. POST 到 `/api/v1/ocr/extract`，LLM 返回结构化 JSON
3. 人工审核提取结果，修正错误
4. POST 到 `/api/v1/portfolio/1/holdings` 导入

需要在 `.env` 中配置 LLM API key（`OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`）。

---

## 页面

| 路径 | 说明 |
|---|---|
| `/` | 主投资组合仪表盘 |
| `/spy-dashboard` | SPY / 标普 500 技术指标监控 |
| `/fire-calc` | FIRE 退休计算器 |
| `/docs` | Swagger API 文档 |
| `/health` | 服务健康检查 |

---

## 架构

```
FastAPI（端口 8000）
├── /api/v1/auth        — demo 用户管理
├── /api/v1/portfolio   — 持仓 CRUD + 价格刷新
├── /api/v1/strategy    — 配置分析、风险闸门、再平衡
├── /api/v1/market      — 实时价格、技术指标、汇率
├── /api/v1/ocr         — 截图 → 结构化持仓提取
└── /api/v1/fire        — FIRE 测算

app.db（SQLite）        — 持仓、价格历史、风险闸门状态
内存缓存               — 价格 + 指标缓存（60 秒 TTL，重启清空）
```

市场价格来自雅虎财经（免费，交易时段约 15 分钟延迟）。

---

## 项目结构

```
asset_mgt/
├── app/                    # FastAPI 应用
│   ├── api/                # 路由处理（portfolio、strategy、market、ocr、fire）
│   ├── models/             # SQLAlchemy 模型
│   ├── services/           # 业务逻辑（行情数据、策略、OCR）
│   ├── schemas/            # Pydantic 请求/响应模型
│   ├── static/             # 前端 HTML 页面
│   └── main.py
├── docs/
│   ├── screenshots/        # 界面截图
│   └── system_design.md    # 架构与设计说明
├── scripts/                # 数据导入和维护脚本
├── tests/
│   └── test_system.py
├── tools/                  # 工具脚本（OCR 辅助、网页抓取）
├── .env.example
├── docker-compose.yml      # 可选：PostgreSQL 替换方案
├── requirements.txt
└── start.sh
```

## 开发

```bash
# 运行系统测试
venv/bin/python3 tests/test_system.py

# API 文档
open http://localhost:8000/docs
```
