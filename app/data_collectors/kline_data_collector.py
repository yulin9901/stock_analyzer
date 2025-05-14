#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
import datetime
import json # Not strictly needed here but good for consistency if other collectors use it
import os
import sys
from app.database.db_manager import DatabaseManager

# Append path for data_api module if not running in a standard environment
# This is specific to the Manus environment structure
if os.path.exists("/opt/.manus/.sandbox-runtime"): # Check if in Manus sandbox
    sys.path.append("/opt/.manus/.sandbox-runtime")
    from data_api import ApiClient # type: ignore
else:
    # Provide a mock or raise an error if ApiClient is essential and not found outside Manus
    class ApiClient:
        def call_api(self, api_name, query):
            print(f"Mock ApiClient: Called {api_name} with query {query}")
            # Return a structure that mimics a failed or empty response
            return {"chart": {"result": None, "error": {"code": "MOCK_ENV", "description": "ApiClient not available outside Manus sandbox"}}}

# from ...config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME # To be loaded via a config utility

def fetch_stock_kline_data(api_client, symbol, region="US", interval="1d", range_period="1mo"):
    """Fetches K-line data for a given symbol using the YahooFinance datasource API via ApiClient."""
    print(f"Fetching K-line data for symbol: {symbol}, region: {region}, interval: {interval}, range: {range_period}")
    try:
        kline_response = api_client.call_api(
            'YahooFinance/get_stock_chart',
            query={'symbol': symbol, 'region': region, 'interval': interval, 'range': range_period, 'includeAdjustedClose': 'true'}
        )

        if kline_response and kline_response.get("chart") and kline_response["chart"].get("result") and kline_response["chart"]["result"][0]:
            result = kline_response["chart"]["result"][0]
            timestamps = result.get("timestamp", [])
            indicators = result.get("indicators", {}).get("quote", [{}])[0]
            # adjclose_indicators = result.get("indicators", {}).get("adjclose", [{}])[0] # If needed

            if not timestamps or not indicators.get("open"):
                print(f"Warning: Timestamps or open prices missing in API response for {symbol}.")
                return []

            kline_data_points = []
            for i in range(len(timestamps)):
                try:
                    dt_object = datetime.datetime.fromtimestamp(timestamps[i])
                    open_price = indicators.get("open", [])[i]
                    high_price = indicators.get("high", [])[i]
                    low_price = indicators.get("low", [])[i]
                    close_price = indicators.get("close", [])[i]
                    volume = indicators.get("volume", [])[i]

                    if any(p is None for p in [open_price, high_price, low_price, close_price]):
                        # print(f"Skipping data point for {symbol} at {dt_object.strftime("%Y-%m-%d %H:%M:%S")} due to missing price data.")
                        continue

                    data_point = {
                        "stock_code": symbol,
                        "timestamp": dt_object.strftime("%Y-%m-%d %H:%M:%S"),
                        "open_price": open_price,
                        "high_price": high_price,
                        "low_price": low_price,
                        "close_price": close_price,
                        "volume": volume if volume is not None else 0,
                        "retrieved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    kline_data_points.append(data_point)
                except IndexError:
                    # print(f"Index error while processing K-line data for {symbol} at index {i}.")
                    continue
                except TypeError as te:
                    # print(f"Type error processing data for {symbol} at index {i}: {te}.")
                    continue

            print(f"Successfully parsed {len(kline_data_points)} K-line data points for {symbol}.")
            return kline_data_points
        elif kline_response and kline_response.get("chart") and kline_response["chart"].get("error"):
            print(f"API Error for {symbol}: {kline_response["chart"]["error"]}")
            return []
        else:
            print(f"Failed to fetch K-line data for {symbol} or unexpected response structure.")
            # print(f"API Response: {kline_response}") # Can be verbose
            return []

    except Exception as e:
        print(f"Exception during K-line API call for {symbol}: {e}")
        return []

def store_kline_data_in_db(db_config, kline_data_points):
    """Stores fetched K-line data into the MySQL database."""
    if not kline_data_points:
        print("No K-line data to store.")
        return 0

    inserted_count = 0
    db_manager = DatabaseManager(db_config)

    try:
        # 使用数据库管理器的上下文管理器
        with db_manager.get_connection() as (connection, cursor):
            # Table creation should be handled by a separate schema management script or initial setup
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS kline_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
                timestamp DATETIME NOT NULL COMMENT 'K线时间点',
                open_price DECIMAL(10, 2) NOT NULL COMMENT '开盘价',
                high_price DECIMAL(10, 2) NOT NULL COMMENT '最高价',
                low_price DECIMAL(10, 2) NOT NULL COMMENT '最低价',
                close_price DECIMAL(10, 2) NOT NULL COMMENT '收盘价',
                volume BIGINT COMMENT '成交量',
                turnover DECIMAL(20,2) COMMENT '成交额',
                retrieved_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据入库时间',
                UNIQUE KEY `idx_stock_time` (`stock_code`, `timestamp`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            add_kline_sql = ("""
            INSERT INTO kline_data
            (stock_code, timestamp, open_price, high_price, low_price, close_price, volume, retrieved_at)
            VALUES (%(stock_code)s, %(timestamp)s, %(open_price)s, %(high_price)s, %(low_price)s, %(close_price)s, %(volume)s, %(retrieved_at)s)
            ON DUPLICATE KEY UPDATE
            open_price = VALUES(open_price),
            high_price = VALUES(high_price),
            low_price = VALUES(low_price),
            close_price = VALUES(close_price),
            volume = VALUES(volume),
            retrieved_at = VALUES(retrieved_at)
            """)

            for data_point in kline_data_points:
                try:
                    cursor.execute(add_kline_sql, data_point)
                    inserted_count += 1
                except Exception as err:
                    print(f"Database error for K-line {data_point.get('stock_code')} at {data_point.get('timestamp')}: {err}")

            connection.commit()
            print(f"Successfully processed {len(kline_data_points)} K-line points. Stored/Updated {inserted_count} points.")

    except Exception as err:
        print(f"Error connecting to MySQL or executing K-line query: {err}")
        return 0

    return inserted_count

# Example of how this module might be called
if __name__ == "__main__":
    print("Executing kline_data_collector.py as a standalone script (for testing purposes).")

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

    # For Chinese A-shares, symbols are like '600519.SS' (Shanghai) or '000001.SZ' (Shenzhen)
    # For US stocks, 'AAPL', 'MSFT'
    example_stock_symbol = "AAPL"
    example_region = "US"
    # example_stock_symbol = "000001.SZ" # Ping An Bank, China
    # example_region = "SZ" # Or try "SS" for Shanghai, "HK" for Hong Kong listed Chinese stocks

    if db_config["DB_USER"] == "your_db_user":
        print("警告: 使用占位符数据库凭据进行直接脚本执行。")
        print("如果未配置，数据库操作可能会失败。")

    # Initialize ApiClient (will be mock if not in Manus env)
    api_cli = ApiClient()

    kline_points = fetch_stock_kline_data(api_client=api_cli, symbol=example_stock_symbol, region=example_region, interval="1d", range_period="1mo")

    if kline_points:
        if db_config["DB_USER"] != "your_db_user":
            store_kline_data_in_db(db_config=db_config, kline_data_points=kline_points)
        else:
            print("已获取K线数据，但由于使用占位符数据库配置，未存储。")
            print("获取的数据:")
            for point in kline_points[:5]: # 打印前5个点
                print(point)
    else:
        print(f"未能获取 {example_stock_symbol} 的K线数据。")

