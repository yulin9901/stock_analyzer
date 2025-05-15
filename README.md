# 股票分析系统

## 项目概述

这是一个自动化的股票分析系统，用于收集市场数据、分析热点话题和资金流向，并使用ChatGPT生成买入建议。系统可以定时运行，每小时自动收集数据，并在开盘前汇总数据发送给ChatGPT获取买入建议。

该项目已经从脚本形式重构为结构化的项目，支持作为定时任务调度器运行，也支持手动运行单个任务。

## 项目结构

```
stock_analyzer/
├── app/                        # 主应用包
│   ├── __init__.py
│   ├── data_collectors/        # 数据收集模块
│   │   ├── __init__.py
│   │   ├── hot_topics_collector.py
│   │   ├── market_fund_flow_collector.py
│   │   └── kline_data_collector.py
│   ├── data_processors/        # 数据处理模块
│   │   ├── __init__.py
│   │   └── daily_summary_processor.py
│   ├── decision_makers/        # 决策生成模块
│   │   ├── __init__.py
│   │   ├── buy_decision_chatgpt.py
│   │   └── sell_decision_processor.py
│   ├── database/               # 数据库管理模块
│   │   ├── __init__.py
│   │   └── db_manager.py
│   ├── reporting/              # 报告生成模块
│   │   ├── __init__.py
│   │   └── profit_loss_calculator.py
│   ├── scheduler/              # 定时任务调度模块
│   │   ├── __init__.py
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
├── main.py                     # 原始入口脚本
├── run.py                      # 新的主入口脚本
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
   * 创建数据库（例如：`stock_analysis`）
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
   * 编辑`config.py`并填入您的API密钥和数据库配置

## 运行方式

### 作为定时任务调度器运行

```bash
python run.py --run scheduler
```

这将启动定时任务调度器，按照配置的时间自动执行数据收集和分析任务。

### 运行单个任务

```bash
python run.py --run task --task <task_name> [--date YYYY-MM-DD] [--force]
```

可用的任务:
* `collect_hot_topics`: 收集热点数据
* `collect_market_fund_flows`: 收集大盘资金流向数据
* `summarize_daily_data`: 汇总每日数据
* `get_buy_decision`: 获取买入建议
* `collect_hourly_data`: 收集热点和资金流向数据
* `prepare_market_open`: 开盘前准备（汇总数据并获取买入建议）
* `full_run`: 运行完整流程

参数:
* `--date`: 指定目标日期，格式为YYYY-MM-DD，默认为今天
* `--force`: 强制运行任务，即使在非交易日

### 使用原始脚本运行

您仍然可以使用原始的`main.py`脚本运行:

```bash
python main.py --action <action_name> [options]
```

可用的操作:
* `collect_news`: 获取并存储热点财经新闻
* `collect_flows`: 获取并存储市场资金流向数据
* `summarize`: 汇总每日新闻和资金流向
* `get_buy_decision`: 从ChatGPT获取买入决策
* `collect_kline`: 收集特定股票的K线数据
* `full_run_daily`: 执行一系列日常任务

### 安装为Windows服务

```bash
python scripts/install_service.py --install
```

这将把系统安装为Windows服务，在系统启动时自动运行。

## 重要说明

* **API密钥**: 确保您在`config/config.py`中的API密钥正确有效
* **ChatGPT模拟**: 如果您的配置中`OPENAI_API_KEY`是占位符或为空，`buy_decision_chatgpt.py`将使用模拟响应
* **数据源可靠性**: 数据的准确性和可用性取决于外部API（TianAPI、AKShare、YahooFinance）
* **决策逻辑**: 实现的买入/卖出决策逻辑非常基础，仅用于演示目的
* **无实际交易**: 此应用程序不执行实际交易，所有"买入"和"卖出"操作都是模拟的并记录在数据库中

## 免责声明

本软件仅用于教育和演示目的，不构成财务建议。股票交易涉及重大损失风险。作者和贡献者不对基于本软件做出的任何财务决策负责。
