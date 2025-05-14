#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
import datetime
import json
from app.database.db_manager import DatabaseManager

def process_and_store_daily_summary(db_config, target_date_str=None):
    """Fetches daily data from hot_topics and market_fund_flows, summarizes it,
       and stores it in the daily_summary table.
    Args:
        db_config (dict): Dictionary containing DB_HOST, DB_USER, DB_PASSWORD, DB_NAME.
        target_date_str (str, optional): The date for which to summarize data, in 'YYYY-MM-DD' format.
                                         Defaults to today if None.
    """
    if target_date_str:
        try:
            target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid date format: {target_date_str}. Please use YYYY-MM-DD.")
            return False
    else:
        target_date = datetime.date.today()

    print(f"Starting daily data summarization for {target_date.strftime('%Y-%m-%d')}...")

    db_manager = DatabaseManager(db_config)

    try:
        # 使用数据库管理器的上下文管理器
        with db_manager.get_connection(dictionary=True) as (connection, cursor):
            # 1. Fetch and summarize hot topics for the target date
            query_topics = """
            SELECT title, source, content_summary FROM hot_topics
            WHERE DATE(retrieved_at) = %(target_date)s
            ORDER BY timestamp DESC LIMIT 10
            """
            cursor.execute(query_topics, {"target_date": target_date.strftime("%Y-%m-%d")})
            topics = cursor.fetchall()

            if topics:
                topic_details = []
                for t in topics:
                    if t['content_summary']:
                        topic_details.append(f"{t['title']} ({t['source']}): {t['content_summary']}")
                    else:
                        topic_details.append(f"{t['title']} ({t['source']})")
                aggregated_hot_topics_summary = "Today's key topics: " + "; ".join(topic_details)
            else:
                aggregated_hot_topics_summary = "No specific hot topics found for today in the database."

            # 2. Fetch and summarize market fund flows for the target date
            query_flows = """
            SELECT DISTINCT market_index, inflow_amount, change_rate FROM market_fund_flows
            WHERE DATE(retrieved_at) = %(target_date)s
            ORDER BY inflow_amount DESC
            """
            cursor.execute(query_flows, {"target_date": target_date.strftime("%Y-%m-%d")})
            flows = cursor.fetchall()

            if flows:
                flow_details = []
                total_inflow_sh_sz = 0
                for f in flows:
                    flow_details.append(f"{f['market_index']}: Inflow {f.get('inflow_amount', 0):.2f}亿, Change {f.get('change_rate', 0):.2f}%")
                    if f['market_index'] in ["上证指数", "深证成指"]:
                         total_inflow_sh_sz += f['inflow_amount'] if f['inflow_amount'] else 0
                aggregated_fund_flow_summary = f"Market fund flows: {'; '.join(flow_details)}. Shanghai & Shenzhen total net inflow: {total_inflow_sh_sz:.2f}亿."
            else:
                aggregated_fund_flow_summary = "No specific market fund flow data found for today in the database."

            market_sentiment_indicator = "Neutral (To be determined by a dedicated sentiment analysis module)"
            key_economic_indicators = json.dumps({}) # Placeholder, could be fetched by another module

            # 3. Store the summary in daily_summary table
            # Note: Table creation should ideally be handled by a separate schema management script or initial setup.
            # Keeping it here for now to ensure the function can run if the table doesn't exist, similar to original script.
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                id INT AUTO_INCREMENT PRIMARY KEY,
                date DATE UNIQUE NOT NULL COMMENT '汇总数据的日期',
                aggregated_hot_topics_summary TEXT COMMENT '当日热点资讯汇总摘要',
                aggregated_fund_flow_summary TEXT COMMENT '当日大盘资金流入情况汇总摘要',
                market_sentiment_indicator VARCHAR(255) COMMENT '市场情绪指标',
                key_economic_indicators TEXT COMMENT '当日关键经济指标 (JSON格式存储)',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '汇总数据创建时间'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            insert_summary_sql = ("""
            INSERT INTO daily_summary
            (date, aggregated_hot_topics_summary, aggregated_fund_flow_summary, market_sentiment_indicator, key_economic_indicators)
            VALUES (%(date)s, %(topics_summary)s, %(flows_summary)s, %(sentiment)s, %(eco_indicators)s)
            ON DUPLICATE KEY UPDATE
            aggregated_hot_topics_summary = VALUES(aggregated_hot_topics_summary),
            aggregated_fund_flow_summary = VALUES(aggregated_fund_flow_summary),
            market_sentiment_indicator = VALUES(market_sentiment_indicator),
            key_economic_indicators = VALUES(key_economic_indicators),
            created_at = CURRENT_TIMESTAMP
            """)

            summary_data = {
                "date": target_date.strftime("%Y-%m-%d"),
                "topics_summary": aggregated_hot_topics_summary,
                "flows_summary": aggregated_fund_flow_summary,
                "sentiment": market_sentiment_indicator,
                "eco_indicators": key_economic_indicators
            }

            cursor.execute(insert_summary_sql, summary_data)
            connection.commit()
            print(f"Successfully stored/updated daily summary for {target_date.strftime('%Y-%m-%d')}.")
            return True

    except Exception as err:
        print(f"Database error during daily summarization: {err}")
        return False

# Example of how this module might be called (for testing or from a main script)
if __name__ == "__main__":
    print("Executing daily_summary_processor.py as a standalone script (for testing purposes).")

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
        # 使用今天的日期进行测试
        success = process_and_store_daily_summary(db_config=db_config)
        # 使用特定日期进行测试
        # success = process_and_store_daily_summary(db_config=db_config, target_date_str="2025-05-13")
        if success:
            print("每日数据汇总过程成功完成（来自测试调用）。")
        else:
            print("每日数据汇总过程失败或遇到错误（来自测试调用）。")

