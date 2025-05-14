-- 数据库整体设计：用于存储热点资讯、大盘资金流向、每日汇总、买卖决策、K线图和盈亏等数据。

-- 1. 热点资讯表 (hot_topics)
CREATE TABLE IF NOT EXISTS hot_topics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '资讯发布时间或抓取时间',
    source VARCHAR(255) COMMENT '资讯来源, 例如：新浪财经、腾讯新闻等',
    title TEXT NOT NULL COMMENT '资讯标题',
    url VARCHAR(1024) UNIQUE COMMENT '资讯原始链接',
    content_summary TEXT COMMENT '资讯内容摘要',
    retrieved_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据入库时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存储获取的国内热点资讯';

-- 2. 大盘资金流入情况表 (market_fund_flows)
CREATE TABLE IF NOT EXISTS market_fund_flows (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据观测时间点',
    market_index VARCHAR(50) COMMENT '大盘指数名称, 例如：上证指数、深证成指、沪深300',
    inflow_amount DECIMAL(20, 4) COMMENT '资金净流入金额（亿元），可为负数表示流出',
    change_rate DECIMAL(10, 4) COMMENT '涨跌幅',
    sector_flows TEXT COMMENT '板块资金流向详情 (JSON格式存储，例如: {"电子": 10.5, "医药": -5.2})',
    data_source VARCHAR(255) COMMENT '数据来源平台',
    retrieved_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据入库时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存储大盘资金流入情况';

-- 3. 每日数据汇总表 (daily_summary)
CREATE TABLE IF NOT EXISTS daily_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE UNIQUE NOT NULL COMMENT '汇总数据的日期',
    aggregated_hot_topics_summary TEXT COMMENT '当日热点资讯汇总摘要',
    aggregated_fund_flow_summary TEXT COMMENT '当日大盘资金流入情况汇总摘要',
    market_sentiment_indicator VARCHAR(100) COMMENT '市场情绪指标（例如：看涨、看跌、中性）',
    key_economic_indicators TEXT COMMENT '当日关键经济指标 (JSON格式存储)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '汇总数据创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存储每日汇总后的数据';

-- 4. 股票买入决策表 (stock_buy_decisions)
CREATE TABLE IF NOT EXISTS stock_buy_decisions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    decision_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '决策生成时间',
    daily_summary_id INT COMMENT '关联的每日数据汇总ID',
    stock_code VARCHAR(20) NOT NULL COMMENT '建议买入的股票代码',
    stock_name VARCHAR(100) COMMENT '建议买入的股票名称',
    buy_price_suggestion DECIMAL(10, 2) COMMENT '建议买入价格',
    quantity_suggestion INT COMMENT '建议买入数量',
    reasoning TEXT COMMENT 'ChatGPT给出的买入理由',
    chatgpt_raw_response TEXT COMMENT 'ChatGPT原始回复内容',
    is_executed BOOLEAN DEFAULT FALSE COMMENT '是否已执行买入操作',
    executed_buy_price DECIMAL(10,2) COMMENT '实际执行买入价格',
    executed_quantity INT COMMENT '实际执行买入数量',
    executed_timestamp DATETIME COMMENT '实际执行买入时间',
    FOREIGN KEY (daily_summary_id) REFERENCES daily_summary(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存储ChatGPT判断的股票买入信息';

-- 5. K线图数据表 (kline_data)
CREATE TABLE IF NOT EXISTS kline_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    timestamp DATETIME NOT NULL COMMENT 'K线时间点（例如：分钟级、小时级、日级）',
    open_price DECIMAL(10, 2) NOT NULL COMMENT '开盘价',
    high_price DECIMAL(10, 2) NOT NULL COMMENT '最高价',
    low_price DECIMAL(10, 2) NOT NULL COMMENT '最低价',
    close_price DECIMAL(10, 2) NOT NULL COMMENT '收盘价',
    volume BIGINT COMMENT '成交量',
    turnover DECIMAL(20,2) COMMENT '成交额',
    retrieved_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据入库时间',
    UNIQUE KEY `idx_stock_time` (`stock_code`, `timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存储获取的股票K线图数据';

-- 6. 交易记录表 (trades)
CREATE TABLE IF NOT EXISTS trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(100) COMMENT '股票名称',
    transaction_type ENUM('BUY', 'SELL') NOT NULL COMMENT '交易类型：买入或卖出',
    transaction_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '交易执行时间',
    quantity INT NOT NULL COMMENT '成交数量',
    price DECIMAL(10, 2) NOT NULL COMMENT '成交价格',
    commission_fee DECIMAL(10, 2) DEFAULT 0.00 COMMENT '手续费',
    stamp_duty DECIMAL(10, 2) DEFAULT 0.00 COMMENT '印花税（卖出时）',
    other_fees DECIMAL(10, 2) DEFAULT 0.00 COMMENT '其他费用',
    total_amount DECIMAL(15, 2) COMMENT '总金额 (买入为负，卖出为正，已扣除费用)',
    related_buy_decision_id INT COMMENT '关联的买入决策ID (如果是基于决策的买入)',
    sell_reason TEXT COMMENT '卖出原因 (如果是卖出操作)',
    FOREIGN KEY (related_buy_decision_id) REFERENCES stock_buy_decisions(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='记录实际的股票买卖操作';

-- 7. 每日盈亏统计表 (daily_profit_loss)
CREATE TABLE IF NOT EXISTS daily_profit_loss (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE UNIQUE NOT NULL COMMENT '统计日期',
    total_realized_profit_loss DECIMAL(15, 2) DEFAULT 0.00 COMMENT '当日已实现总盈亏',
    total_unrealized_profit_loss DECIMAL(15, 2) DEFAULT 0.00 COMMENT '当日持仓未实现总盈亏 (基于当日收盘价计算)',
    total_fees_paid DECIMAL(10, 2) DEFAULT 0.00 COMMENT '当日总支付费用（手续费+印花税等）',
    portfolio_value DECIMAL(20,2) COMMENT '当日收盘时组合总价值',
    calculation_details TEXT COMMENT '盈亏计算的简要说明或涉及的交易ID列表',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '统计数据创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存储每日的盈亏情况（考虑手续费）';


