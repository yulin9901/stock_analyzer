#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
股票分析系统主入口
用于启动定时任务调度器
"""
import os
import sys
import time
import argparse
import logging
import datetime

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.scheduler.scheduler import StockAnalyzerScheduler
from app.scheduler.tasks import collect_hot_topics, collect_market_fund_flows, summarize_daily_data, get_buy_decision, is_trading_day
from app.utils import load_config, get_db_config

# 创建日志目录
os.makedirs(os.path.join(APP_DIR, 'logs'), exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(APP_DIR, 'logs', 'stock_analyzer.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger('stock_analyzer')

def run_scheduler():
    """运行定时任务调度器"""
    logger.info("启动股票分析系统定时任务调度器...")

    scheduler = StockAnalyzerScheduler()
    scheduler.start()

    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("接收到停止信号，正在停止调度器...")
        scheduler.stop()
        logger.info("调度器已停止")

def run_task(task_name, date_str=None):
    """运行指定的任务"""
    logger.info(f"运行任务: {task_name}")

    # 检查是否是交易日（对于某些任务）
    today = date_str or datetime.date.today().strftime("%Y-%m-%d")

    if task_name == "collect_hot_topics":
        success = collect_hot_topics()
    elif task_name == "collect_market_fund_flows":
        success = collect_market_fund_flows()
    elif task_name == "summarize_daily_data":
        success = summarize_daily_data(date_str)
    elif task_name == "get_buy_decision":
        success = get_buy_decision(date_str)
    elif task_name == "collect_hourly_data":
        # 收集热点和资金流向数据
        success1 = collect_hot_topics()
        success2 = collect_market_fund_flows()
        success = success1 and success2
    elif task_name == "prepare_market_open":
        # 汇总数据并获取买入建议
        if not is_trading_day(date_str):
            logger.info(f"{today} 不是交易日，跳过任务")
            return
        success1 = summarize_daily_data(date_str)
        if success1:
            success2 = get_buy_decision(date_str)
            success = success1 and success2
        else:
            success = False
    elif task_name == "full_run":
        # 运行完整流程
        if not is_trading_day(date_str):
            logger.info(f"{today} 不是交易日，跳过任务")
            return

        # 1. 收集数据
        logger.info("1. 收集热点数据和资金流向数据")
        success1 = collect_hot_topics()
        success2 = collect_market_fund_flows()

        if not (success1 and success2):
            logger.warning("数据收集失败，无法继续后续步骤")
            return

        # 2. 汇总数据
        logger.info("2. 汇总数据")
        success3 = summarize_daily_data(date_str)

        if not success3:
            logger.warning("数据汇总失败，无法继续后续步骤")
            return

        # 3. 获取买入建议
        logger.info("3. 获取买入建议")
        success4 = get_buy_decision(date_str)

        success = success1 and success2 and success3 and success4
    else:
        logger.error(f"未知任务: {task_name}")
        return

    if success:
        logger.info(f"任务 {task_name} 成功完成")
    else:
        logger.warning(f"任务 {task_name} 失败或未完成")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="股票分析系统")
    parser.add_argument("--run", choices=["scheduler", "task"], help="运行模式: scheduler(调度器) 或 task(单个任务)", default="scheduler")
    parser.add_argument("--task", choices=["collect_hot_topics", "collect_market_fund_flows", "summarize_daily_data",
                                          "get_buy_decision", "collect_hourly_data", "prepare_market_open", "full_run"],
                        help="要运行的任务名称")
    parser.add_argument("--date", help="目标日期 (YYYY-MM-DD)，默认为今天")
    parser.add_argument("--force", action="store_true", help="强制运行任务，即使在非交易日")

    args = parser.parse_args()

    # 如果指定了--force参数，临时修改is_trading_day函数的行为
    if args.force:
        logger.info("已启用强制运行模式，将忽略交易日检查")
        # 保存原始函数
        original_is_trading_day = is_trading_day
        # 替换为总是返回True的函数
        globals()["is_trading_day"] = lambda date_str=None: True

    try:
        if args.run == "scheduler":
            run_scheduler()
        elif args.run == "task":
            if not args.task:
                logger.error("运行单个任务时必须指定 --task 参数")
                parser.print_help()
                return
            run_task(args.task, args.date)
        else:
            logger.error(f"未知运行模式: {args.run}")
            parser.print_help()
    finally:
        # 如果修改了is_trading_day函数，恢复原始函数
        if args.force:
            globals()["is_trading_day"] = original_is_trading_day

if __name__ == "__main__":
    main()
