#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
import datetime
import json
import requests # For actual ChatGPT API call
from app.database.db_manager import DatabaseManager

# API URL for ChatGPT
CHATGPT_API_URL = "https://api.openai.com/v1/chat/completions" # Example URL

def get_buy_decision_from_chatgpt(db_config, openai_api_key, target_date_str=None):
    """Fetches daily summary, sends to ChatGPT (mocked or real), gets buy decision, and stores it."""
    if target_date_str:
        try:
            target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid date format for decision: {target_date_str}. Please use YYYY-MM-DD.")
            return False
    else:
        target_date = datetime.date.today()

    print(f"Attempting to get ChatGPT buy decision for {target_date.strftime("%Y-%m-%d")}...")

    daily_summary_id = None
    daily_summary_content = None
    db_manager = DatabaseManager(db_config)

    try:
        # 使用数据库管理器获取每日汇总数据
        query_summary = """
        SELECT id, aggregated_hot_topics_summary, aggregated_fund_flow_summary,
               market_sentiment_indicator, key_economic_indicators
        FROM daily_summary WHERE date = %(target_date)s
        """
        results = db_manager.execute_query(
            query_summary,
            {"target_date": target_date.strftime("%Y-%m-%d")},
            dictionary=True
        )

        if not results:
            print(f"No daily summary found for {target_date.strftime('%Y-%m-%d')} to send to ChatGPT.")
            return False

        summary_row = results[0]
        daily_summary_id = summary_row["id"]
        daily_summary_content = summary_row
        print(f"Daily summary ID {daily_summary_id} fetched for ChatGPT input.")

    except Exception as err:
        print(f"Database error fetching daily summary: {err}")
        return False

    # Prepare prompt for ChatGPT
    prompt = f"""
    Analyze the following Chinese stock market data for {target_date.strftime("%Y-%m-%d")} and provide a buy recommendation for the upcoming trading session.
    If recommending a stock, specify the stock code, stock name, a suggested buy price, and a brief reasoning.
    Format your primary recommendation clearly. If no strong buy signal, state that.

    Daily Hot Topics Summary: {daily_summary_content.get("aggregated_hot_topics_summary")}
    Daily Market Fund Flow Summary: {daily_summary_content.get("aggregated_fund_flow_summary")}
    Market Sentiment Indicator: {daily_summary_content.get("market_sentiment_indicator")}
    Key Economic Indicators: {daily_summary_content.get("key_economic_indicators")}

    Provide your top stock pick if any.
    Example of desired output format if recommending:
    Stock Code: [CODE]
    Stock Name: [NAME]
    Suggested Buy Price: [PRICE]
    Reasoning: [YOUR REASONING]
    """

    parsed_decision = {
        "stock_code": None, "stock_name": None, "buy_price_suggestion": None,
        "quantity_suggestion": None, "reasoning": None, "chatgpt_raw_response": None
    }

    if openai_api_key == "YOUR_OPENAI_API_KEY_HERE" or not openai_api_key:
        print("Warning: OpenAI API Key is a placeholder or not provided. Simulating ChatGPT response.")
        raw_chatgpt_text_response = "Stock Code: SIM007\nStock Name: Simulated AI Corp\nSuggested Buy Price: 250.50\nReasoning: Strong simulated growth potential based on mock data analysis."
        parsed_decision["chatgpt_raw_response"] = json.dumps({"simulated_content": raw_chatgpt_text_response})
    else:
        print("Sending data to ChatGPT API...")
        headers = {"Authorization": f"Bearer {openai_api_key}", "Content-Type": "application/json"}
        payload = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}], "max_tokens": 300}
        try:
            response = requests.post(CHATGPT_API_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            chatgpt_api_result = response.json()
            raw_chatgpt_text_response = chatgpt_api_result.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed_decision["chatgpt_raw_response"] = json.dumps(chatgpt_api_result) # Store full API response
            print(f"Received response from ChatGPT.")
        except requests.exceptions.RequestException as e:
            print(f"ChatGPT API request failed: {e}")
            return False
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Error parsing ChatGPT API response: {e}")
            return False

    # Parse ChatGPT response (this will need to be robust)
    lines = raw_chatgpt_text_response.strip().split("\n")
    for line in lines:
        if line.startswith("Stock Code:"):
            parsed_decision["stock_code"] = line.split(":", 1)[1].strip()
        elif line.startswith("Stock Name:"):
            parsed_decision["stock_name"] = line.split(":", 1)[1].strip()
        elif line.startswith("Suggested Buy Price:"):
            try:
                parsed_decision["buy_price_suggestion"] = float(line.split(":", 1)[1].strip().replace(",","")) # Handle comma in price
            except ValueError:
                print(f"Warning: Could not parse buy price from ChatGPT: {line.split(":", 1)[1].strip()}")
        elif line.startswith("Reasoning:"):
            parsed_decision["reasoning"] = line.split(":", 1)[1].strip()

    if not parsed_decision["stock_code"]:
        print("ChatGPT did not provide a stock code or parsing failed. No decision will be stored.")
        return False

    # Store decision
    try:
        # 使用数据库管理器的上下文管理器
        with db_manager.get_connection() as (connection, cursor):
            # Table creation should be handled by a separate schema management script or initial setup
            cursor.execute("""
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
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            add_decision_sql = ("""
            INSERT INTO stock_buy_decisions
            (daily_summary_id, stock_code, stock_name, buy_price_suggestion, quantity_suggestion, reasoning, chatgpt_raw_response, decision_timestamp)
            VALUES (%(daily_summary_id)s, %(stock_code)s, %(stock_name)s, %(buy_price_suggestion)s, %(quantity_suggestion)s, %(reasoning)s, %(chatgpt_raw_response)s, %(decision_timestamp)s)
            """)

            decision_data_to_store = {
                "daily_summary_id": daily_summary_id,
                "stock_code": parsed_decision["stock_code"],
                "stock_name": parsed_decision["stock_name"],
                "buy_price_suggestion": parsed_decision.get("buy_price_suggestion"),
                "quantity_suggestion": parsed_decision.get("quantity_suggestion"),
                "reasoning": parsed_decision["reasoning"],
                "chatgpt_raw_response": parsed_decision["chatgpt_raw_response"],
                "decision_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            cursor.execute(add_decision_sql, decision_data_to_store)
            connection.commit()
            print(f"Successfully stored ChatGPT buy decision for {parsed_decision['stock_code']}.")
            return True

    except Exception as err:
        print(f"Database error storing ChatGPT decision: {err}")
        return False

# Example of how this module might be called
if __name__ == "__main__":
    print("Executing buy_decision_chatgpt.py as a standalone script (for testing purposes).")

    # 使用统一的配置加载方式
    try:
        from app.utils import load_config, get_db_config
        config = load_config()
        db_config = get_db_config(config)
        openai_api_key = config.OPENAI_API_KEY
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
        openai_api_key = "YOUR_OPENAI_API_KEY_HERE" # 替换为实际测试值

    if db_config["DB_USER"] == "your_db_user" or openai_api_key == "YOUR_OPENAI_API_KEY_HERE":
        print("警告: 使用占位符数据库凭据或OpenAI API密钥进行直接脚本执行。")
        print("该过程将使用模拟/模拟的API调用运行，如果未配置，数据库操作可能会失败。")

    # 确保您的数据库中存在当天（或特定日期）的每日摘要
    # 您可能需要先运行daily_summary_processor，或确保数据存在。
    # 为了进行干净的测试，您可能需要插入一个虚拟的daily_summary记录。
    print("在运行此测试之前，请确保数据库中存在目标日期的daily_summary记录。")

    success = get_buy_decision_from_chatgpt(db_config=db_config, openai_api_key=openai_api_key)
    # 使用特定日期进行测试
    # success = get_buy_decision_from_chatgpt(db_config=db_config, openai_api_key=openai_api_key, target_date_str="2025-05-13")

    if success:
        print("ChatGPT买入决策过程已完成（来自测试调用）。")
    else:
        print("ChatGPT买入决策过程失败或未做出/存储决策（来自测试调用）。")

