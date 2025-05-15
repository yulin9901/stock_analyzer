#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
import requests
import json
import datetime
import re
from app.database.db_manager import DatabaseManager

# --- TianAPI endpoint for financial news ---
TIANAPI_FINANCE_NEWS_URL = "http://api.tianapi.com/caijing/index"

def fetch_hot_topics_data(api_key):
    """Fetches hot financial news from TianAPI."""
    hot_topics_data = []
    params = {
        "key": api_key,
        "num": 10,  # Fetch 20 news items
    }
    print(f"Fetching hot topics from TianAPI with URL: {TIANAPI_FINANCE_NEWS_URL} and params: {params}")
    try:
        response = requests.get(TIANAPI_FINANCE_NEWS_URL, params=params, timeout=10, col=135)
        print(f"Response status code: {response.status_code}")
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        print(f"Response data: {data}")

        if data.get("code") == 200:
            news_list = data.get("newslist", [])
            for item in news_list:
                ctime_str = item.get("ctime")
                try:
                    if ctime_str and len(ctime_str) == 16: # YYYY-MM-DD HH:MM
                        timestamp_val = datetime.datetime.strptime(ctime_str + ":00", "%Y-%m-%d %H:%M:%S")
                    elif ctime_str and len(ctime_str) == 19: # YYYY-MM-DD HH:MM:SS
                        timestamp_val = datetime.datetime.strptime(ctime_str, "%Y-%m-%d %H:%M:%S")
                    else:
                        timestamp_val = datetime.datetime.now()
                except ValueError:
                    print(f"Warning: Could not parse ctime \'{ctime_str}\' for a news item. Defaulting to current time.")
                    timestamp_val = datetime.datetime.now()

                # 处理content_summary，移除时间戳信息
                description = item.get("description", "")
                # 检查description是否只包含时间戳
                if description and description.replace("-", "").replace(":", "").replace(" ", "").isdigit():
                    # 如果只包含时间戳，则设置为空字符串
                    content_summary = ""
                else:
                    # 尝试移除末尾的时间戳（如果存在）
                    # 匹配末尾的时间戳格式：YYYY-MM-DDHH:MM 或 YYYY-MM-DD HH:MM
                    timestamp_pattern = r'\d{4}-\d{2}-\d{2}[ ]?\d{2}:\d{2}$'
                    content_summary = re.sub(timestamp_pattern, '', description).strip()

                topic = {
                    "timestamp": timestamp_val.strftime("%Y-%m-%d %H:%M:%S"),
                    "source": item.get("source", "Unknown Source"),
                    "title": item.get("title", "No Title"),
                    "url": item.get("url"),
                    "content_summary": content_summary,
                    "retrieved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                hot_topics_data.append(topic)
            print(f"Successfully fetched {len(hot_topics_data)} hot topics.")
        else:
            print(f"Error from TianAPI (code: {data.get('code')}): {data.get('msg')}")
            return None

    except requests.exceptions.Timeout:
        print(f"Request to TianAPI timed out.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except json.JSONDecodeError:
        print("Failed to decode JSON response from TianAPI.")
        return None
    return hot_topics_data

def store_hot_topics_data(db_config, topics):
    """Stores fetched hot topics into the MySQL database."""
    if not topics:
        print("No topics to store.")
        return 0

    inserted_count = 0
    db_manager = DatabaseManager(db_config)

    try:
        # 使用数据库管理器的上下文管理器
        with db_manager.get_connection() as (connection, cursor):
            # Table creation should be handled by a separate schema management script or initial setup
            # cursor.execute(""" CREATE TABLE IF NOT EXISTS ... """) # Removed for modularity

            add_topic_sql = ("""
            INSERT INTO hot_topics
            (timestamp, source, title, url, content_summary, retrieved_at)
            VALUES (%(timestamp)s, %(source)s, %(title)s, %(url)s, %(content_summary)s, %(retrieved_at)s)
            ON DUPLICATE KEY UPDATE title=VALUES(title), content_summary=VALUES(content_summary), retrieved_at=VALUES(retrieved_at)
            """) # Added ON DUPLICATE KEY UPDATE for robustness

            for topic_data in topics:
                if not topic_data.get("url"):
                    print(f"Skipping topic due to missing URL: {topic_data.get('title')}")
                    continue
                try:
                    cursor.execute(add_topic_sql, topic_data)
                    inserted_count += 1
                except Exception as err:
                    print(f"Database error for URL {topic_data.get('url')}: {err}")

            connection.commit()
            print(f"Successfully processed {len(topics)} topics. Stored/Updated {inserted_count} topics in the database.")

    except Exception as err:
        print(f"Error connecting to MySQL or executing query: {err}")
        return 0

    return inserted_count

# Example of how this module might be called (for testing or from a main script)
if __name__ == "__main__":
    print("Executing hot_topics_collector.py as a standalone script (for testing purposes).")

    # 使用统一的配置加载方式
    try:
        from app.utils import load_config, get_db_config
        config = load_config()
        db_config = get_db_config(config)
        api_key = config.TIANAPI_KEY

        print("成功加载配置文件")
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        print("使用测试配置...")
        # 测试配置
        api_key = "YOUR_TIANAPI_KEY_HERE" # 替换为您的API密钥进行测试
        db_config = {
            "DB_HOST": "localhost",
            "DB_PORT": 3306,
            "DB_USER": "your_db_user",
            "DB_PASSWORD": "your_db_password",
            "DB_NAME": "stock_analysis"
        }

    if api_key == "YOUR_TIANAPI_KEY_HERE" or db_config["DB_USER"] == "your_db_user":
        print("警告: 使用占位符API密钥或数据库凭据进行直接脚本执行。")
        print("如果要使用真实数据进行测试，请配置它们。")
    else:
        fetched_data = fetch_hot_topics_data(api_key=api_key)
        if fetched_data:
            store_hot_topics_data(db_config=db_config, topics=fetched_data)
        else:
            print("无法获取热门话题或未返回数据。")

