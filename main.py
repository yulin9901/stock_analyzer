#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
import argparse
import datetime
import os
import sys

# Ensure the app directory is in the Python path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.utils import load_config, get_db_config

# Import Manus-specific ApiClient if available, otherwise use a mock for local testing
if os.path.exists("/opt/.manus/.sandbox-runtime"): # Check if in Manus sandbox
    sys.path.append("/opt/.manus/.sandbox-runtime")
    from data_api import ApiClient # type: ignore
else:
    class ApiClient:
        def call_api(self, api_name, query):
            print(f"Mock ApiClient: Called {api_name} with query {query}")
            return {"chart": {"result": None, "error": {"code": "MOCK_ENV", "description": "ApiClient not available outside Manus sandbox"}}}

# Dynamically import a module and call a function
def run_module_function(module_path, function_name, *args, **kwargs):
    try:
        module_name = module_path.replace("/", ".") # Convert path to module name
        module = __import__(module_name, fromlist=[function_name])
        func = getattr(module, function_name)
        print(f"\n--- Running {module_path} -> {function_name} ---")
        return func(*args, **kwargs)
    except Exception as e:
        print(f"Error running {module_path} -> {function_name}: {e}")
        # import traceback
        # traceback.print_exc()
        return None

def main():
    parser = argparse.ArgumentParser(description="Stock Analysis and Decision Support System")
    parser.add_argument("--action", choices=["collect_news", "collect_flows", "summarize", "get_buy_decision", "collect_kline", "make_sell_decision", "calc_pnl", "full_run_daily", "setup_db"], 
                        help="Action to perform.", required=True)
    parser.add_argument("--date", help="Target date for operations (YYYY-MM-DD). Defaults to today for most operations.")
    parser.add_argument("--symbol", help="Stock symbol for K-line data collection (e.g., AAPL, 600519.SS).")
    parser.add_argument("--region", help="Stock region for K-line data (e.g., US, SS, SZ, HK). Default: US", default="US")
    parser.add_argument("--interval", help="K-line interval (e.g., 1d, 1h, 5m). Default: 1d", default="1d")
    parser.add_argument("--range", help="K-line range (e.g., 1mo, 5d, 1y). Default: 1mo", default="1mo")

    args = parser.parse_args()

    try:
        config = load_config()
        db_params = get_db_config(config)
        api_client = ApiClient() # Initialize Manus ApiClient (or mock)
    except Exception as e:
        print(f"Failed to initialize application: {e}")
        return

    target_date = args.date if args.date else datetime.date.today().strftime("%Y-%m-%d")

    if args.action == "setup_db":
        print("Database setup: Please ensure your MySQL server is running and use the database_schema.sql file to create tables.")
        print("Example: mysql -u your_user -p your_database_name < /path/to/database_schema.sql")
        print("The individual modules also contain CREATE TABLE IF NOT EXISTS statements for convenience during development, but a full schema setup is recommended.")
        return

    if args.action == "collect_news":
        run_module_function("app.data_collectors.hot_topics_collector", "fetch_hot_topics_data", api_key=config.TIANAPI_KEY)
        # The original script also stored it. Let's assume the module does both fetch and store for now.
        # Or, we can separate fetch and store calls if modules are designed that way.
        # For now, assuming `fetch_hot_topics_data` gets data, and we need a separate call to store.
        # Re-checking the refactored module: it has fetch_hot_topics_data and store_hot_topics_data
        topics = run_module_function("app.data_collectors.hot_topics_collector", "fetch_hot_topics_data", api_key=config.TIANAPI_KEY)
        if topics:
            run_module_function("app.data_collectors.hot_topics_collector", "store_hot_topics_data", db_config=db_params, topics=topics)

    elif args.action == "collect_flows":
        flows = run_module_function("app.data_collectors.market_fund_flow_collector", "fetch_market_fund_flow_data_from_source")
        if flows:
            run_module_function("app.data_collectors.market_fund_flow_collector", "store_market_fund_flow_data", db_config=db_params, flows_data=flows)

    elif args.action == "summarize":
        run_module_function("app.data_processors.daily_summary_processor", "process_and_store_daily_summary", db_config=db_params, target_date_str=target_date)

    elif args.action == "get_buy_decision":
        run_module_function("app.decision_makers.buy_decision_chatgpt", "get_buy_decision_from_chatgpt", db_config=db_params, openai_api_key=config.OPENAI_API_KEY, target_date_str=target_date)

    elif args.action == "collect_kline":
        if not args.symbol:
            print("Error: --symbol is required for collect_kline action.")
            return
        kline_data = run_module_function("app.data_collectors.kline_data_collector", "fetch_stock_kline_data", api_client=api_client, symbol=args.symbol, region=args.region, interval=args.interval, range_period=args.range)
        if kline_data:
            run_module_function("app.data_collectors.kline_data_collector", "store_kline_data_in_db", db_config=db_params, kline_data_points=kline_data)

    elif args.action == "make_sell_decision":
        run_module_function("app.decision_makers.sell_decision_processor", "process_sell_decisions", db_config=db_params, api_client=api_client)

    elif args.action == "calc_pnl":
        run_module_function("app.reporting.profit_loss_calculator", "calculate_and_store_daily_profit_loss", db_config=db_params, api_client=api_client, target_date_str=target_date)

    elif args.action == "full_run_daily":
        print(f"--- Starting Full Daily Run for {target_date} ---")
        # 1. Collect News
        topics = run_module_function("app.data_collectors.hot_topics_collector", "fetch_hot_topics_data", api_key=config.TIANAPI_KEY)
        if topics: run_module_function("app.data_collectors.hot_topics_collector", "store_hot_topics_data", db_config=db_params, topics=topics)
        # 2. Collect Market Flows
        flows = run_module_function("app.data_collectors.market_fund_flow_collector", "fetch_market_fund_flow_data_from_source")
        if flows: run_module_function("app.data_collectors.market_fund_flow_collector", "store_market_fund_flow_data", db_config=db_params, flows_data=flows)
        # 3. Summarize Data
        run_module_function("app.data_processors.daily_summary_processor", "process_and_store_daily_summary", db_config=db_params, target_date_str=target_date)
        # 4. Get Buy Decision (e.g., pre-market)
        run_module_function("app.decision_makers.buy_decision_chatgpt", "get_buy_decision_from_chatgpt", db_config=db_params, openai_api_key=config.OPENAI_API_KEY, target_date_str=target_date)
        # (User would then manually execute buys based on decisions)
        # 5. Collect K-line for open positions (assuming this is done intraday or for sell decisions)
        # This part needs logic to get open positions and fetch K-line for them.
        # For simplicity, we might fetch K-line for specific stocks if needed, or assume it's done before sell decisions.
        print("Note: K-line collection for specific open positions would typically run before sell decisions.")
        # 6. Make Sell Decisions (e.g., before market close)
        run_module_function("app.decision_makers.sell_decision_processor", "process_sell_decisions", db_config=db_params, api_client=api_client)
        # 7. Calculate P&L (e.g., after market close)
        run_module_function("app.reporting.profit_loss_calculator", "calculate_and_store_daily_profit_loss", db_config=db_params, api_client=api_client, target_date_str=target_date)
        print(f"--- Full Daily Run for {target_date} Completed ---")
    else:
        print(f"Unknown action: {args.action}")

if __name__ == "__main__":
    main()

