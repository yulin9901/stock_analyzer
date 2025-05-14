#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
import akshare as ak
import pandas as pd
import datetime
import json
from app.database.db_manager import DatabaseManager

def fetch_market_fund_flow_data_from_source():
    """Fetches overall market fund flow data using AKShare."""
    print("Fetching market fund flow data using AKShare...")
    market_data_list = []
    try:
        # 使用 stock_sector_fund_flow_rank 函数获取按板块分类的资金流向
        print("Calling ak.stock_sector_fund_flow_rank()...")
        df_market_flow = ak.stock_sector_fund_flow_rank() # 按板块分类的资金流向
        print(f"AKShare response type: {type(df_market_flow)}")

        if df_market_flow is None or df_market_flow.empty:
            print("Failed to fetch market fund flow data or no data returned from ak.stock_sector_fund_flow_rank().")
            return None

        print(f"DataFrame columns: {df_market_flow.columns.tolist()}")
        print(f"DataFrame shape: {df_market_flow.shape}")
        print(f"First few rows: {df_market_flow.head().to_dict('records')}")

        for index, row in df_market_flow.iterrows():
            # 获取板块名称
            market_index_name = row.get("名称", "未知板块")

            try:
                # 获取涨跌幅
                change_rate = float(row.get("今日涨跌幅", 0))

                # 获取主力净流入-净额
                inflow_str = str(row.get("今日主力净流入-净额", "0"))
                # 将科学计数法转换为普通数字，并转换为亿元单位
                inflow_amount = float(inflow_str) / 100000000  # 转换为亿元
            except (ValueError, TypeError) as e:
                print(f"Error parsing numeric values for {market_index_name}: {e}")
                inflow_amount = 0.0
                change_rate = 0.0

            # 获取其他资金流向数据，用于构建 sector_flows
            try:
                sector_flows = {
                    "超大单": {
                        "inflow": float(row.get("今日超大单净流入-净额", 0)) / 100000000,  # 转换为亿元
                        "change": float(row.get("今日超大单净流入-净占比", 0))
                    },
                    "大单": {
                        "inflow": float(row.get("今日大单净流入-净额", 0)) / 100000000,  # 转换为亿元
                        "change": float(row.get("今日大单净流入-净占比", 0))
                    },
                    "中单": {
                        "inflow": float(row.get("今日中单净流入-净额", 0)) / 100000000,  # 转换为亿元
                        "change": float(row.get("今日中单净流入-净占比", 0))
                    },
                    "小单": {
                        "inflow": float(row.get("今日小单净流入-净额", 0)) / 100000000,  # 转换为亿元
                        "change": float(row.get("今日小单净流入-净占比", 0))
                    },
                    "主力净流入最大股": row.get("今日主力净流入最大股", "")
                }
            except (ValueError, TypeError) as e:
                print(f"Error parsing sector flows for {market_index_name}: {e}")
                sector_flows = {}

            current_time = datetime.datetime.now()
            market_data = {
                "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "market_index": market_index_name,
                "inflow_amount": inflow_amount,
                "change_rate": change_rate,
                "sector_flows": json.dumps(sector_flows),
                "data_source": "AKShare (stock_sector_fund_flow_rank)",
                "retrieved_at": current_time.strftime("%Y-%m-%d %H:%M:%S")
            }
            market_data_list.append(market_data)

        print(f"Successfully fetched fund flow data for {len(market_data_list)} market indices.")
        return market_data_list

    except Exception as e:
        print(f"Error fetching or processing market fund flow data from AKShare: {e}")
        return None

def store_market_fund_flow_data(db_config, flows_data):
    """Stores fetched market fund flow data into the MySQL database."""
    if not flows_data:
        print("No market fund flow data to store.")
        return 0

    inserted_count = 0
    db_manager = DatabaseManager(db_config)

    try:
        # 使用数据库管理器的上下文管理器
        with db_manager.get_connection() as (connection, cursor):
            add_flow_sql = ("""
            INSERT INTO market_fund_flows
            (timestamp, market_index, inflow_amount, change_rate, sector_flows, data_source, retrieved_at)
            VALUES (%(timestamp)s, %(market_index)s, %(inflow_amount)s, %(change_rate)s, %(sector_flows)s, %(data_source)s, %(retrieved_at)s)
            ON DUPLICATE KEY UPDATE
            inflow_amount=VALUES(inflow_amount),
            change_rate=VALUES(change_rate),
            retrieved_at=VALUES(retrieved_at)
            """) # Added ON DUPLICATE KEY UPDATE

            for flow_item in flows_data:
                try:
                    cursor.execute(add_flow_sql, flow_item)
                    inserted_count += 1
                except Exception as err:
                    print(f"Database error for fund flow {flow_item.get('market_index')}: {err}")

            connection.commit()
            print(f"Successfully processed {len(flows_data)} fund flow items. Stored/Updated {inserted_count} items.")

    except Exception as err:
        print(f"Error connecting to MySQL or executing query for market fund flows: {err}")
        return 0

    return inserted_count

# Example of how this module might be called (for testing or from a main script)
if __name__ == "__main__":
    print("Executing market_fund_flow_collector.py as a standalone script (for testing purposes).")

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
            "DB_USER": "your_db_user",
            "DB_PASSWORD": "your_db_password",
            "DB_NAME": "stock_analysis"
        }

    if db_config["DB_USER"] == "your_db_user":
        print("警告: 使用占位符数据库凭据进行直接脚本执行。")
        print("如果要使用真实数据进行测试，请配置它们。")
    else:
        market_flows = fetch_market_fund_flow_data_from_source()
        if market_flows:
            store_market_fund_flow_data(db_config=db_config, flows_data=market_flows)
        else:
            print("无法获取市场资金流向数据或未返回数据。")

