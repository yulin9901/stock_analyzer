#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
import datetime
import json
import os
import sys
from app.database.db_manager import DatabaseManager

# Append path for data_api module if not running in a standard environment
if os.path.exists("/opt/.manus/.sandbox-runtime"): # Check if in Manus sandbox
    sys.path.append("/opt/.manus/.sandbox-runtime")
    from data_api import ApiClient # type: ignore
else:
    # Provide a mock for ApiClient if not in Manus environment
    class ApiClient:
        def call_api(self, api_name, query):
            print(f"Mock ApiClient: Called {api_name} with query {query}")
            # Return a structure that mimics a failed or empty response
            return {"chart": {"result": None, "error": {"code": "MOCK_ENV", "description": "ApiClient not available outside Manus sandbox"}}}

# from ...config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME # To be loaded via a config utility
# from ...app.data_collectors.kline_data_collector import fetch_stock_kline_data # Potentially use this

# --- Constants for mock fees (example for China A-shares) ---
COMMISSION_RATE = 0.0003  # 0.03%
MIN_COMMISSION = 5.0      # 5 CNY
STAMP_DUTY_RATE_SELL = 0.001 # 0.1% for selling

def _get_open_positions(db_manager):
    """Fetches open positions from stock_buy_decisions that have been executed but not yet sold."""
    query = """
    SELECT
        sbd.id AS decision_id,
        sbd.stock_code,
        sbd.stock_name,
        sbd.executed_quantity,
        sbd.executed_buy_price,
        sbd.executed_timestamp,
        sbd.daily_summary_id
    FROM stock_buy_decisions sbd
    LEFT JOIN trades t ON sbd.id = t.related_buy_decision_id AND t.transaction_type = 'SELL'
    WHERE sbd.is_executed = TRUE AND t.id IS NULL;
    """
    positions = db_manager.execute_query(query, dictionary=True)
    print(f"Found {len(positions)} open positions to evaluate for selling.")
    return positions

def _fetch_latest_kline_for_decision(api_client, stock_code, region="US"):
    """Fetches recent K-line data for a sell decision."""
    print(f"Fetching latest K-line for {stock_code} (region: {region}) for sell decision...")
    try:
        response = api_client.call_api(
            'YahooFinance/get_stock_chart',
            query={'symbol': stock_code, 'interval': '1d', 'range': '5d', 'region': region, 'includeAdjustedClose': 'true'}
        )
        if response and response.get("chart") and response["chart"].get("result") and response["chart"]["result"][0]:
            result = response["chart"]["result"][0]
            timestamps = result.get("timestamp", [])
            indicators = result.get("indicators", {}).get("quote", [{}])[0]
            if timestamps and indicators.get("close") and len(indicators["close"]) > 0:
                latest_close_price = indicators["close"][-1]
                if latest_close_price is not None:
                    return {"latest_close": latest_close_price, "data": result}
                if len(indicators["close"]) > 1 and indicators["close"][-2] is not None:
                    return {"latest_close": indicators["close"][-2], "data": result}
            print(f"Could not determine latest close price for {stock_code} from K-line data.")
        elif response and response.get("chart") and response["chart"].get("error"):
            print(f"API Error fetching K-line for {stock_code}: {response['chart']['error']}")
        else:
            print(f"Failed to fetch or parse K-line for {stock_code}.")
        return None
    except Exception as e:
        print(f"Exception fetching K-line for {stock_code}: {e}")
        return None

def _get_daily_summary_context(db_manager, daily_summary_id):
    """Fetches the daily summary data for context."""
    if not daily_summary_id:
        return None
    query = "SELECT aggregated_hot_topics_summary, aggregated_fund_flow_summary, market_sentiment_indicator FROM daily_summary WHERE id = %(summary_id)s"
    results = db_manager.execute_query(query, {"summary_id": daily_summary_id}, dictionary=True)
    return results[0] if results else None

def _evaluate_sell_condition(position_data, kline_info, daily_summary):
    """ Simple sell decision logic. """
    stock_code = position_data["stock_code"]
    buy_price = position_data["executed_buy_price"]
    latest_close = kline_info["latest_close"] if kline_info and kline_info.get("latest_close") is not None else None

    if latest_close is None or buy_price is None:
        print(f"Cannot evaluate sell for {stock_code}: missing latest close price or buy price.")
        return False, None, "Missing critical price data for evaluation."

    buy_price_float = float(buy_price)

    # Stop-loss: Sell if price drops 10% below buy price
    if latest_close < (buy_price_float * 0.90):
        reason = f"Stop-loss: Current price {latest_close} is >10% below buy price {buy_price_float:.2f}."
        return True, latest_close, reason

    # Profit-taking: Sell if price increases 20% above buy price
    if latest_close > (buy_price_float * 1.20):
        reason = f"Profit-taking: Current price {latest_close} is >20% above buy price {buy_price_float:.2f}."
        return True, latest_close, reason

    # Example based on market sentiment (simplified)
    # if daily_summary and daily_summary.get("market_sentiment_indicator"):
    #     sentiment = daily_summary["market_sentiment_indicator"].lower()
    #     if "bearish" in sentiment or "negative" in sentiment:
    #         reason = f"Market sentiment is '{daily_summary["market_sentiment_indicator"]}'. Considering selling."
    #         return True, latest_close, reason

    return False, None, "Hold: No specific sell conditions met."

def _record_sell_transaction_in_db(db_manager, position_data, sell_price, sell_reason):
    """Records the sell transaction in the trades table."""
    transaction_value = float(sell_price) * int(position_data["executed_quantity"])
    commission = max(MIN_COMMISSION, transaction_value * COMMISSION_RATE)
    stamp_duty = transaction_value * STAMP_DUTY_RATE_SELL
    total_fees = commission + stamp_duty
    total_amount_received = transaction_value - total_fees

    insert_trade_sql = """
    INSERT INTO trades
    (stock_code, stock_name, transaction_type, transaction_time, quantity, price,
     commission_fee, stamp_duty, total_amount, related_buy_decision_id, sell_reason)
    VALUES (%(stock_code)s, %(stock_name)s, 'SELL', %(transaction_time)s, %(quantity)s, %(price)s,
            %(commission_fee)s, %(stamp_duty)s, %(total_amount)s, %(related_buy_decision_id)s, %(sell_reason)s)
    """
    trade_data = {
        "stock_code": position_data["stock_code"],
        "stock_name": position_data["stock_name"],
        "transaction_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "quantity": position_data["executed_quantity"],
        "price": sell_price,
        "commission_fee": commission,
        "stamp_duty": stamp_duty,
        "total_amount": total_amount_received,
        "related_buy_decision_id": position_data["decision_id"],
        "sell_reason": sell_reason
    }
    try:
        # 不提交事务，由调用函数处理
        db_manager.execute_update(insert_trade_sql, trade_data)
        print(f"Prepared SELL transaction for {position_data['stock_code']} (Decision ID: {position_data['decision_id']}).")
        return True
    except Exception as err:
        print(f"Database error preparing SELL for {position_data['stock_code']}: {err}")
        return False

def process_sell_decisions(db_config, api_client):
    """Main process to evaluate open positions and make/record sell decisions."""
    print(f"Starting sell decision process at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")

    db_manager = DatabaseManager(db_config)
    sells_made = 0

    try:
        # 使用数据库管理器的上下文管理器
        with db_manager.get_connection() as (connection, cursor):
            # Table creation should be handled by a separate schema management script or initial setup
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
                stock_name VARCHAR(100) COMMENT '股票名称',
                transaction_type ENUM('BUY', 'SELL') NOT NULL COMMENT '交易类型',
                transaction_time DATETIME NOT NULL COMMENT '交易时间',
                quantity INT NOT NULL COMMENT '交易数量',
                price DECIMAL(10, 2) NOT NULL COMMENT '交易价格',
                commission_fee DECIMAL(10, 2) COMMENT '手续费',
                stamp_duty DECIMAL(10, 2) COMMENT '印花税',
                other_fees DECIMAL(10, 2) COMMENT '其他费用',
                total_amount DECIMAL(20, 2) COMMENT '总金额 (买入为负，卖出为正)',
                related_buy_decision_id INT COMMENT '关联的买入决策ID (针对卖出交易)',
                sell_reason TEXT COMMENT '卖出理由',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
                FOREIGN KEY (related_buy_decision_id) REFERENCES stock_buy_decisions(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            open_positions = _get_open_positions(db_manager)
            if not open_positions:
                print("No open positions found to evaluate.")
                return sells_made

            for pos in open_positions:
                print(f"\nEvaluating position: ID {pos['decision_id']}, Stock {pos['stock_code']}")
                # Determine region based on stock_code format (e.g., .SS, .SZ)
                stock_region = "US" # Default
                if ".SS" in pos['stock_code'].upper(): stock_region = "SS"
                elif ".SZ" in pos['stock_code'].upper(): stock_region = "SZ"
                elif ".HK" in pos['stock_code'].upper(): stock_region = "HK"

                kline_info = _fetch_latest_kline_for_decision(api_client, pos["stock_code"], region=stock_region)
                daily_summary_ctx = _get_daily_summary_context(db_manager, pos.get("daily_summary_id"))

                if not kline_info or kline_info.get("latest_close") is None:
                    print(f"Could not get valid K-line info for {pos['stock_code']}. Skipping sell decision.")
                    continue

                sell_signal, sell_price, reason = _evaluate_sell_condition(pos, kline_info, daily_summary_ctx)

                if sell_signal and sell_price is not None:
                    if _record_sell_transaction_in_db(db_manager, pos, sell_price, reason):
                        sells_made += 1
                else:
                    print(f"Holding {pos['stock_code']}. Reason: {reason}")

            if sells_made > 0:
                connection.commit()
                print(f"Committed {sells_made} sell transactions.")
            else:
                print("No sell transactions were made in this run.")

    except Exception as err:
        print(f"Database connection error in sell process: {err}")
        return sells_made

    return sells_made

# Example of how this module might be called
if __name__ == "__main__":
    print("Executing sell_decision_processor.py as a standalone script (for testing purposes).")

    # 使用统一的配置加载方式
    try:
        from app.utils import load_config, get_db_config
        config = load_config()
        db_config = get_db_config(config)
        print("成功加载配置文件")
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        print("使用测试配置...")
        # 测试配置
        db_config = {
            "DB_HOST": "localhost",
            "DB_PORT": 3306,
            "DB_USER": "your_db_user", # 替换为实际测试值
            "DB_PASSWORD": "your_db_password", # 替换为实际测试值
            "DB_NAME": "stock_analysis"
        }

    if db_config["DB_USER"] == "your_db_user":
        print("警告: 使用占位符数据库凭据进行直接脚本执行。")
        print("如果未配置，数据库操作可能会失败。")
        print("此脚本需要在'stock_buy_decisions'表中有未平仓的持仓记录和相关数据。")
    else:
        # 初始化ApiClient（如果不在Manus环境中，将使用模拟客户端）
        api_cli = ApiClient()
        # 确保您的数据库中存在未平仓的持仓记录，这样脚本才能正常工作。
        # 您可能需要先运行buy_decision_chatgpt，并手动将决策标记为已执行。
        print("确保'stock_buy_decisions'表中存在未平仓的持仓记录以进行测试。")
        num_sells = process_sell_decisions(db_config=db_config, api_client=api_cli)
        print(f"卖出决策过程已完成。卖出数量: {num_sells}")

