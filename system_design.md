# 个人资产管理平台 - 系统设计文档

## 1. 系统概述

### 1.1 项目背景
创建一个综合性的个人资产管理平台，专门针对美股投资者的仓位管理和风险控制需求。系统能够汇集用户分散在各个渠道的资产信息，提供智能化的投资策略监控和再平衡建议。

### 1.2 核心功能
- **资产整合管理**：银行卡、支付平台、美股投资、保险、房产等
- **美股投资策略执行**：基于用户定义的投资策略框架进行监控
- **风险闸门监控**：实时监控S&P 500和VIX指数，自动触发风险控制
- **投资组合再平衡**：智能计算权重偏差，提供调仓建议
- **实时数据监控**：11只核心ETF的价格和技术指标追踪

### 1.3 目标用户
- 个人美股投资者
- 需要系统化资产管理的用户
- 追求策略化投资的用户

## 2. 架构设计

### 2.1 总体架构
```
┌─────────────────────────────────────────────────────────┐
│                    前端展示层                              │
├─────────────────────────────────────────────────────────┤
│                    业务逻辑层                              │
├─────────────────────────────────────────────────────────┤
│                    数据访问层                              │
├─────────────────────────────────────────────────────────┤
│                    外部API层                               │
└─────────────────────────────────────────────────────────┘
```

### 2.2 微服务架构
- **Web服务**：提供前端界面和REST API
- **数据采集服务**：从各种API获取实时数据
- **策略引擎服务**：执行投资策略逻辑
- **监控服务**：实时监控和预警
- **数据存储服务**：数据持久化和缓存

### 2.3 技术选型
- **后端框架**：Python FastAPI
- **前端框架**：React.js + TypeScript
- **数据库**：PostgreSQL（主库）+ Redis（缓存）
- **消息队列**：Celery + Redis
- **监控**：Prometheus + Grafana
- **部署**：Docker + Docker Compose

## 3. 模块设计

### 3.1 用户投资策略模块
#### 目标仓位配置
```python
TARGET_ALLOCATION = {
    "cash_short_debt": {"symbols": ["DUSB", "SGOV"], "target": 0.25},
    "sp_equal_weight": {"symbols": ["RSP", "SPYV"], "target": 0.20},
    "sp_market_cap": {"symbols": ["SPY", "VOO"], "target": 0.15},
    "high_beta": {"symbols": ["NVDA", "QQQ"], "target": 0.15},
    "global_ex_us": {"symbols": ["DFAW"], "target": 0.10},
    "defensive": {"symbols": ["BRK.B", "GLD"], "target": 0.10}
}
```

#### 投资阶段策略
- **早期积累**：全部定投，仅监控风险闸门
- **中期过渡**：风险闸门触发时卖出卫星仓
- **后期防守**：风险闸门触发时大幅减仓

### 3.2 风险闸门模块
#### 触发条件
- S&P 500 < 200日移动平均线
- VIX > 30
- 同时满足两个条件才触发

#### 解除条件
- S&P 500 连续10日收盘 > 200日移动平均线
- 后期阶段还需要VIX < 25

### 3.3 实时数据监控模块
#### 监控标的
```python
MONITORED_SYMBOLS = {
    "indices": ["^GSPC", "^VIX"],  # S&P 500, VIX
    "core_etfs": ["SPY", "VOO", "RSP", "SPYV"],
    "satellite_etfs": ["NVDA", "QQQ", "DFAW"],
    "defensive_etfs": ["BRK.B", "GLD"],
    "cash_etfs": ["DUSB", "SGOV"]
}
```

#### 更新频率
- 交易时间内：每1分钟更新
- 非交易时间：每小时检查
- 汇率：每小时更新

## 4. 数据库设计

### 4.1 核心数据表
#### 用户表 (users)
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    investment_stage VARCHAR(20) DEFAULT 'early', -- early, middle, late
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 持仓表 (holdings)
```sql
CREATE TABLE holdings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    symbol VARCHAR(10) NOT NULL,
    shares DECIMAL(18, 6) NOT NULL,
    cost_basis DECIMAL(18, 2) NOT NULL,
    current_price DECIMAL(18, 2),
    market_value DECIMAL(18, 2),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 价格历史表 (price_history)
```sql
CREATE TABLE price_history (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    price DECIMAL(18, 2) NOT NULL,
    volume BIGINT,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 技术指标表 (technical_indicators)
```sql
CREATE TABLE technical_indicators (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    indicator_type VARCHAR(20) NOT NULL, -- sma_200, vix
    value DECIMAL(18, 4) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 风险闸门状态表 (risk_gate_status)
```sql
CREATE TABLE risk_gate_status (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    is_triggered BOOLEAN DEFAULT FALSE,
    sp500_below_sma BOOLEAN DEFAULT FALSE,
    vix_above_30 BOOLEAN DEFAULT FALSE,
    consecutive_days_above_sma INTEGER DEFAULT 0,
    trigger_date TIMESTAMP,
    resolution_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 策略执行日志表 (strategy_actions)
```sql
CREATE TABLE strategy_actions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action_type VARCHAR(50) NOT NULL, -- rebalance, risk_gate_trigger, etc.
    symbol VARCHAR(10),
    action_details JSONB,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending' -- pending, completed, failed
);
```

### 4.2 Redis缓存设计
```python
# 价格缓存
PRICE_CACHE_KEY = "price:{symbol}"
PRICE_CACHE_TTL = 60  # 1分钟

# 技术指标缓存
INDICATOR_CACHE_KEY = "indicator:{symbol}:{type}"
INDICATOR_CACHE_TTL = 300  # 5分钟

# 风险闸门状态缓存
RISK_GATE_CACHE_KEY = "risk_gate:{user_id}"
RISK_GATE_CACHE_TTL = 60  # 1分钟
```

## 5. API设计

### 5.1 RESTful API设计
#### 基础URL
```
https://api.assetmgmt.com/v1
```

#### 认证
- JWT Token认证
- API Key认证（用于第三方集成）

#### 核心API端点
```python
# 用户管理
POST /auth/login
POST /auth/register
GET /auth/me
POST /auth/logout

# 持仓管理
GET /portfolio/holdings
POST /portfolio/holdings
PUT /portfolio/holdings/{id}
DELETE /portfolio/holdings/{id}

# 实时数据
GET /market/prices
GET /market/prices/{symbol}
GET /market/indicators
GET /market/indicators/{symbol}

# 策略管理
GET /strategy/status
GET /strategy/allocation
POST /strategy/rebalance
GET /strategy/risk-gate

# 历史数据
GET /history/prices/{symbol}
GET /history/performance
GET /history/actions
```

### 5.2 WebSocket API
```python
# 实时价格推送
ws://api.assetmgmt.com/v1/ws/prices

# 风险闸门状态推送
ws://api.assetmgmt.com/v1/ws/risk-gate

# 策略执行状态推送
ws://api.assetmgmt.com/v1/ws/strategy-status
```

## 6. 外部API集成

### 6.1 美股数据API
#### 主要数据源
```python
API_SOURCES = {
    "primary": {
        "name": "Yahoo Finance",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart",
        "rate_limit": "无限制",
        "delay": "15-20分钟"
    },
    "secondary": {
        "name": "Alpha Vantage",
        "url": "https://www.alphavantage.co/query",
        "rate_limit": "500次/天",
        "delay": "实时"
    },
    "backup": {
        "name": "IEX Cloud",
        "url": "https://cloud.iexapis.com/stable/stock",
        "rate_limit": "50,000次/月",
        "delay": "15分钟"
    }
}
```

#### 汇率API
```python
EXCHANGE_RATE_API = {
    "url": "https://api.exchangerate-api.com/v4/latest/USD",
    "rate_limit": "1500次/月",
    "update_frequency": "每小时"
}
```

### 6.2 API调用策略
- **主备切换**：主API失败时自动切换到备用API
- **缓存策略**：频繁调用的数据使用Redis缓存
- **限流控制**：实现API调用频率控制

## 7. 实时监控系统

### 7.1 数据采集任务
```python
# Celery定时任务
@celery.task
def update_market_prices():
    """更新市场价格数据"""
    pass

@celery.task
def calculate_technical_indicators():
    """计算技术指标"""
    pass

@celery.task
def check_risk_gate():
    """检查风险闸门状态"""
    pass

@celery.task
def analyze_portfolio_weights():
    """分析投资组合权重"""
    pass
```

### 7.2 监控频率
- **价格更新**：交易时间内每1分钟
- **技术指标**：每5分钟计算一次
- **风险闸门**：每1分钟检查一次
- **权重分析**：每10分钟分析一次

## 8. 前端界面设计

### 8.1 主要页面
- **仪表盘**：总体资产概览
- **投资策略**：策略监控和执行状态
- **持仓管理**：持仓查看和调整
- **历史分析**：历史表现分析
- **设置**：用户配置和偏好

### 8.2 关键组件
- **实时价格组件**：显示ETF实时价格
- **风险闸门指示器**：显示风险闸门状态
- **权重对比图**：当前权重vs目标权重
- **技术指标图表**：S&P 500和VIX走势
- **策略执行建议**：智能化操作建议

## 9. 部署架构

### 9.1 容器化部署
```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: assetmgmt
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
  
  redis:
    image: redis:6
    ports:
      - "6379:6379"
  
  celery:
    build: .
    command: celery -A app.celery worker --loglevel=info
    depends_on:
      - postgres
      - redis
  
  celery-beat:
    build: .
    command: celery -A app.celery beat --loglevel=info
    depends_on:
      - postgres
      - redis
```

### 9.2 环境配置
```python
# .env
DATABASE_URL=postgresql://postgres:password@postgres:5432/assetmgmt
REDIS_URL=redis://redis:6379/0
ALPHA_VANTAGE_API_KEY=your_api_key
IEX_CLOUD_API_KEY=your_api_key
JWT_SECRET_KEY=your_secret_key
```

## 10. 安全考虑

### 10.1 数据安全
- **加密存储**：敏感数据使用AES-256加密
- **传输安全**：使用HTTPS/WSS协议
- **访问控制**：基于角色的访问控制(RBAC)

### 10.2 API安全
- **身份验证**：JWT Token + API Key
- **授权验证**：接口访问权限控制
- **限流保护**：防止API滥用

### 10.3 数据隐私
- **本地化部署**：支持本地环境部署
- **数据脱敏**：敏感信息脱敏处理
- **审计日志**：操作行为记录

## 11. 性能优化

### 11.1 数据库优化
- **索引优化**：关键字段建立索引
- **查询优化**：复杂查询使用合适的索引
- **连接池**：数据库连接池管理

### 11.2 缓存策略
- **Redis缓存**：频繁查询数据缓存
- **本地缓存**：应用层缓存
- **CDN**：静态资源CDN加速

### 11.3 异步处理
- **Celery任务队列**：耗时操作异步处理
- **WebSocket**：实时数据推送
- **批量处理**：数据批量更新

## 12. 监控和日志

### 12.1 系统监控
- **应用性能监控**：响应时间、吞吐量
- **资源监控**：CPU、内存、磁盘使用
- **错误监控**：异常和错误跟踪

### 12.2 业务监控
- **API调用监控**：外部API调用成功率
- **数据准确性监控**：数据一致性检查
- **用户行为监控**：用户操作统计

### 12.3 日志管理
- **结构化日志**：JSON格式日志
- **日志分级**：DEBUG、INFO、WARNING、ERROR
- **日志聚合**：集中日志管理

## 13. 扩展性设计

### 13.1 水平扩展
- **负载均衡**：多实例部署
- **数据库分片**：大数据量分片存储
- **缓存集群**：Redis集群部署

### 13.2 功能扩展
- **插件系统**：支持第三方策略插件
- **API开放**：开放API给第三方集成
- **多币种支持**：扩展到其他市场

## 14. 测试策略

### 14.1 单元测试
- **覆盖率**：代码覆盖率 > 80%
- **测试框架**：pytest
- **模拟数据**：使用mock数据进行测试

### 14.2 集成测试
- **API测试**：接口功能测试
- **数据库测试**：数据操作测试
- **外部API测试**：第三方API集成测试

### 14.3 性能测试
- **负载测试**：并发用户负载测试
- **压力测试**：系统极限测试
- **稳定性测试**：长时间运行测试

## 15. 实施计划

### 15.1 第一阶段（MVP）
- [ ] 基础架构搭建
- [ ] 用户认证系统
- [ ] 持仓管理功能
- [ ] 价格数据获取

### 15.2 第二阶段（核心功能）
- [ ] 投资策略引擎
- [ ] 风险闸门监控
- [ ] 实时数据推送
- [ ] 基础前端界面

### 15.3 第三阶段（完善功能）
- [ ] 高级分析功能
- [ ] 自动化建议
- [ ] 历史数据分析
- [ ] 性能优化

### 15.4 第四阶段（扩展功能）
- [ ] 移动端支持
- [ ] 高级图表分析
- [ ] 社区功能
- [ ] AI智能建议

---

*本文档将随着项目进展持续更新和完善* 