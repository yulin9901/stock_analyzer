# 加密货币交易策略系统

## 项目概述

这是一个自动化的加密货币交易策略系统，用于收集加密货币市场数据、分析热点话题和市场情绪，并使用AI生成交易策略建议。系统可以定时运行，每小时自动收集数据，并每日生成交易策略。

该项目支持作为定时任务调度器运行，也支持手动运行单个任务。系统集成了Binance API，可以获取实时价格、K线数据、资金费率等市场信息，并通过自然语言处理分析市场情绪。

## 项目结构

```bash
crypto_trading/
├── app/                        # 主应用包
│   ├── __init__.py
│   ├── data_collectors/        # 数据收集模块
│   │   ├── __init__.py
│   │   ├── binance_data_collector.py
│   │   ├── crypto_news_collector.py
│   │   ├── hot_topics_collector.py
│   │   └── market_fund_flow_collector.py
│   ├── data_processors/        # 数据处理模块
│   │   ├── __init__.py
│   │   ├── crypto_daily_summary_processor.py
│   │   └── daily_summary_processor.py
│   ├── decision_makers/        # 决策生成模块
│   │   ├── __init__.py
│   │   ├── crypto_trading_strategy_ai.py
│   │   └── buy_decision_chatgpt.py
│   ├── database/               # 数据库管理模块
│   │   ├── __init__.py
│   │   └── db_manager.py
│   ├── reporting/              # 报告生成模块
│   │   ├── __init__.py
│   │   └── profit_loss_calculator.py
│   ├── scheduler/              # 定时任务调度模块
│   │   ├── __init__.py
│   │   ├── crypto_scheduler.py
│   │   ├── crypto_tasks.py
│   │   ├── scheduler.py
│   │   └── tasks.py
│   └── utils.py                # 工具函数
├── config/                     # 配置文件
│   └── config.py.template      # 配置模板
├── logs/                       # 日志文件
├── models/                     # 数据库模型
│   └── database_schema.sql     # 数据库架构
├── scripts/                    # 辅助脚本
│   └── install_service.py      # 安装Windows服务脚本
├── test/                       # 测试脚本
├── main.py                     # 原始入口脚本（股票分析）
├── run.py                      # 股票分析入口脚本
├── crypto_run.py               # 加密货币交易入口脚本
└── README.md                   # 本文件
```

## 安装步骤

1. **系统要求**:
   * Python 3.11+
   * MySQL 数据库服务器
   * Windows 操作系统（如需作为服务运行）

2. **克隆/下载**: 获取项目文件。

3. **创建虚拟环境（推荐）**:

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

4. **安装依赖**:
   导航到项目根目录并运行:

```bash
pip install -r requirements.txt
```

5. **数据库设置**:
   * 确保MySQL服务器正在运行
   * 创建数据库（例如：`crypto_trading`）
   * 执行`models/database_schema.sql`脚本创建必要的表:

```bash
mysql -u 你的MySQL用户名 -p 你的数据库名 < models/database_schema.sql
```

6. **配置**:
   * 导航到`config/`目录
   * 复制`config.py.template`到`config.py`:

```bash
cp config.py.template config.py
```
   * 编辑`config.py`并填入您的API密钥和数据库配置，特别是Binance API密钥和OpenAI API密钥

## 运行方式

### 作为定时任务调度器运行

```bash
python crypto_run.py --run scheduler
```

这将启动定时任务调度器，按照配置的时间自动执行数据收集和策略生成任务。

### 运行单个任务

```bash
python crypto_run.py --run task --task <task_name> [--date YYYY-MM-DD] [--pairs BTCUSDT,ETHUSDT]
```

可用的任务:

* `collect_crypto_news`: 收集加密货币热点新闻
* `collect_crypto_market_data`: 收集加密货币市场数据
* `summarize_crypto_daily_data`: 汇总加密货币每日数据
* `generate_crypto_trading_strategy`: 生成加密货币交易策略
* `collect_hourly_data`: 收集加密货币新闻和市场数据
* `daily_strategy`: 汇总数据并生成交易策略
* `full_workflow`: 运行完整工作流程

参数:

* `--date`: 指定目标日期，格式为YYYY-MM-DD，默认为今天
* `--pairs`: 指定交易对列表，用逗号分隔，例如: BTCUSDT,ETHUSDT,SOLUSDT

### 安装为Windows服务

```bash
python scripts/install_service.py --install
```

这将把系统安装为Windows服务，在系统启动时自动运行。

## 功能特点

1. **数据采集**:
   * 通过Binance API获取加密货币实时价格、K线数据、资金费率等
   * 收集加密货币相关热点新闻和社交媒体数据
   * 支持多种时间周期的K线数据（1分钟、5分钟、1小时、1天）

2. **数据处理**:
   * 使用自然语言处理分析新闻情感
   * 汇总市场数据和热点资讯
   * 计算市场情绪指标

3. **AI决策**:
   * 通过Sealos AI Proxy调用大模型生成交易策略
   * 提供详细的入场价格、止损价格、止盈价格和仓位大小建议
   * 支持多种交易对的策略生成

4. **自动化调度**:
   * 定时收集数据和生成策略
   * 支持24/7运行，适应加密货币市场特性

## 重要说明

* **API密钥**: 确保您在`config/config.py`中的Binance API密钥和OpenAI API密钥正确有效
* **测试网络**: 默认使用Binance测试网络，如需使用实盘，请将`BINANCE_TESTNET`设置为`False`
* **AI模拟**: 如果您的配置中`OPENAI_API_KEY`是占位符或为空，系统将使用模拟响应
* **数据源可靠性**: 数据的准确性和可用性取决于外部API（Binance、TianAPI等）
* **决策逻辑**: 生成的交易策略仅供参考，不构成投资建议
* **自动交易**: 系统默认不执行实际交易，如需启用自动交易，请将`ENABLE_AUTO_TRADING`设置为`True`（谨慎使用）

## 免责声明

本软件仅用于教育和演示目的，不构成财务建议。加密货币交易涉及重大损失风险。作者和贡献者不对基于本软件做出的任何财务决策负责。
