# Python + MySQL Stock Analyzer Application

## Project Overview

This project is a Python application designed to assist with stock market analysis and decision-making. It fetches financial news, market fund flow data, and stock K-line data, stores it in a MySQL database, summarizes daily information, uses a (mocked or real) ChatGPT interface for buy suggestions, processes sell decisions based on simple logic, and calculates daily profit and loss.

This version has been refactored into a more structured Python application with a main entry point (`main.py`), modular components, and clearer configuration management.

## Project Structure

```
stock_analyzer_app/
├── app/                        # Main application package
│   ├── __init__.py
│   ├── data_collectors/        # Modules for fetching data
│   │   ├── __init__.py
│   │   ├── hot_topics_collector.py
│   │   ├── market_fund_flow_collector.py
│   │   └── kline_data_collector.py
│   ├── data_processors/        # Modules for processing and summarizing data
│   │   ├── __init__.py
│   │   └── daily_summary_processor.py
│   ├── decision_makers/        # Modules for buy/sell decisions
│   │   ├── __init__.py
│   │   ├── buy_decision_chatgpt.py
│   │   └── sell_decision_processor.py
│   ├── reporting/                # Modules for P&L calculation
│   │   ├── __init__.py
│   │   └── profit_loss_calculator.py
│   └── utils.py                # Utility functions (e.g., config loading)
├── config/
│   └── config.py.template      # Configuration template
├── main.py                     # Main entry point of the application
├── requirements.txt            # Python dependencies
├── database_schema.sql         # MySQL database schema
└── README.md                   # This file
```

## Setup and Installation

1.  **Prerequisites**:
    *   Python 3.11+
    *   MySQL Server

2.  **Clone/Download**: Get the project files.

3.  **Create Virtual Environment (Recommended)**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

4.  **Install Dependencies**:
    Navigate to the project root (`stock_analyzer_app/`) and run:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Database Setup**:
    *   Ensure your MySQL server is running.
    *   Create a database (e.g., `stock_analysis`).
    *   Execute the `database_schema.sql` script to create the necessary tables:
        ```bash
        mysql -u YOUR_MYSQL_USER -p YOUR_DATABASE_NAME < database_schema.sql
        ```
        (Replace `YOUR_MYSQL_USER` and `YOUR_DATABASE_NAME` accordingly.)

6.  **Configuration**:
    *   Navigate to the `config/` directory.
    *   Copy `config.py.template` to `config.py`:
        ```bash
        cp config.py.template config.py
        ```
    *   Edit `config.py` and fill in your actual API keys (TianAPI, OpenAI) and MySQL database credentials (host, user, password, database name).

## Running the Application

The application is controlled via `main.py` using command-line arguments.

**General Usage**:
```bash
python main.py --action <action_name> [options]
```

**Available Actions**:

*   `setup_db`: Provides guidance on setting up the database schema (does not execute SQL directly).
*   `collect_news`: Fetches and stores hot financial news.
*   `collect_flows`: Fetches and stores market fund flow data.
*   `summarize`: Summarizes daily news and flows. Use `--date YYYY-MM-DD` if not for today.
*   `get_buy_decision`: Gets buy decisions from ChatGPT (mocked/real). Use `--date YYYY-MM-DD` if not for today.
*   `collect_kline`: Collects K-line data for a specific stock.
    *   Requires: `--symbol <STOCK_SYMBOL>` (e.g., `AAPL`, `600519.SS`)
    *   Optional: `--region <REGION_CODE>` (e.g., `US`, `SS`, `SZ`, `HK` - default `US`)
    *   Optional: `--interval <INTERVAL>` (e.g., `1d`, `1h` - default `1d`)
    *   Optional: `--range <RANGE>` (e.g., `1mo`, `5d` - default `1mo`)
*   `make_sell_decision`: Evaluates open positions and makes sell decisions.
*   `calc_pnl`: Calculates and stores daily profit/loss. Use `--date YYYY-MM-DD` if not for today.
*   `full_run_daily`: Executes a sequence of daily tasks: `collect_news`, `collect_flows`, `summarize`, `get_buy_decision`, `make_sell_decision`, `calc_pnl`. Use `--date YYYY-MM-DD` if not for today.

**Examples**:

*   Fetch news for today:
    ```bash
    python main.py --action collect_news
    ```
*   Summarize data for May 10, 2025:
    ```bash
    python main.py --action summarize --date 2025-05-10
    ```
*   Collect K-line data for stock `600519.SS` (Shanghai market):
    ```bash
    python main.py --action collect_kline --symbol 600519.SS --region SS --interval 1d --range 3mo
    ```
*   Run the full daily process for today:
    ```bash
    python main.py --action full_run_daily
    ```

## Important Notes

*   **API Keys**: Ensure your API keys in `config/config.py` are correct and active.
*   **ChatGPT Mocking**: The ChatGPT integration in `buy_decision_chatgpt.py` will use a mocked response if the `OPENAI_API_KEY` in your config is the placeholder or empty. To use the real API, provide a valid key.
*   **Data Source Reliability**: The accuracy and availability of data depend on external APIs (TianAPI, AKShare, YahooFinance via system API).
*   **Decision Logic**: The buy/sell decision logic implemented is very basic and for demonstration purposes. Real-world trading requires far more sophisticated strategies and risk management.
*   **No Real Trading**: This application DOES NOT execute real trades. All "buy" and "sell" actions are simulated and recorded in the database.

## Disclaimer

This software is for educational and demonstrational purposes only. It is not financial advice. Trading stocks involves significant risk of loss. The authors and contributors are not responsible for any financial decisions made based on this software.

