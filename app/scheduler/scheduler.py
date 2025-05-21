#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
加密货币定时任务调度器
用于定时执行加密货币数据收集、汇总和策略生成任务
"""
import os
import sys
import time
import datetime
import logging
import threading
import schedule
from typing import Callable, Dict, Any

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.utils import load_config, get_db_config
from app.scheduler.tasks import (
    collect_crypto_news,
    collect_crypto_market_data,
    summarize_crypto_daily_data,
    generate_crypto_trading_strategy,
    run_crypto_full_workflow
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(APP_DIR, 'logs', 'crypto_scheduler.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger('crypto_scheduler')

class CryptoTradingScheduler:
    """加密货币交易系统定时任务调度器"""

    def __init__(self):
        """初始化调度器"""
        # 创建日志目录
        os.makedirs(os.path.join(APP_DIR, 'logs'), exist_ok=True)

        # 加载配置
        try:
            self.config = load_config()
            self.db_config = get_db_config(self.config)
            logger.info("成功加载配置")
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            raise

        # 初始化调度器
        self.scheduler_thread = None
        self.is_running = False

        # 设置交易对
        self.trading_pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT"]

    def collect_hourly_data(self):
        """收集每小时数据（加密货币新闻和市场数据）"""
        logger.info("开始收集每小时加密货币数据...")

        # 收集加密货币热点新闻
        try:
            logger.info("收集加密货币热点新闻...")
            news_success = collect_crypto_news()
            if news_success:
                logger.info("成功收集加密货币热点新闻")
            else:
                logger.warning("收集加密货币热点新闻失败或未完成")
        except Exception as e:
            logger.error(f"收集加密货币热点新闻时出错: {e}")

        # 收集加密货币市场数据
        try:
            logger.info("收集加密货币市场数据...")
            market_success = collect_crypto_market_data(self.trading_pairs)
            if market_success:
                logger.info("成功收集加密货币市场数据")
            else:
                logger.warning("收集加密货币市场数据失败或未完成")
        except Exception as e:
            logger.error(f"收集加密货币市场数据时出错: {e}")

        logger.info("每小时加密货币数据收集完成")

    def generate_daily_strategy(self):
        """每日策略生成（汇总数据并生成交易策略）"""
        logger.info("开始每日加密货币策略生成...")
        today = datetime.date.today().strftime("%Y-%m-%d")

        # 汇总数据
        try:
            logger.info(f"汇总 {today} 的加密货币数据...")
            summary_success = summarize_crypto_daily_data(today)
            if summary_success:
                logger.info("成功汇总加密货币数据")
            else:
                logger.warning("加密货币数据汇总失败或未完成")
                return
        except Exception as e:
            logger.error(f"汇总加密货币数据时出错: {e}")
            return

        # 生成交易策略
        try:
            logger.info("生成加密货币交易策略...")
            strategy_success = generate_crypto_trading_strategy(
                target_date_str=today,
                trading_pairs=self.trading_pairs
            )
            if strategy_success:
                logger.info("成功生成加密货币交易策略")
            else:
                logger.warning("生成加密货币交易策略失败或未完成")
        except Exception as e:
            logger.error(f"生成加密货币交易策略时出错: {e}")

        logger.info("每日加密货币策略生成完成")

    def setup_schedule(self):
        """设置定时任务计划"""
        # 清除现有的所有任务
        schedule.clear()

        # 获取配置中的定时任务设置
        hourly_minute = getattr(self.config, "HOURLY_COLLECTION_MINUTE", 0)
        daily_strategy_time = getattr(self.config, "DAILY_STRATEGY_TIME", "00:05")
        run_always = getattr(self.config, "RUN_ALWAYS", True)

        # 每小时收集数据
        if hourly_minute == 0:
            # 在整点运行
            schedule.every().hour.at(":00").do(self.collect_hourly_data)
        else:
            # 在指定分钟运行
            minute_str = f":{hourly_minute:02d}"
            schedule.every().hour.at(minute_str).do(self.collect_hourly_data)

        # 每日策略生成
        schedule.every().day.at(daily_strategy_time).do(self.generate_daily_strategy)

        logger.info(f"定时任务计划已设置: 每小时{hourly_minute}分收集数据, {daily_strategy_time}生成每日策略")

    def _run_scheduler(self):
        """运行调度器（在单独的线程中）"""
        logger.info("调度器线程已启动")
        self.is_running = True

        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"运行调度器时出错: {e}")
                time.sleep(10)  # 出错后等待一段时间再继续

    def start(self):
        """启动调度器"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.warning("调度器已经在运行中")
            return

        # 设置定时任务
        self.setup_schedule()

        # 启动调度器线程
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()

        logger.info("调度器已启动")

    def stop(self):
        """停止调度器"""
        if not self.scheduler_thread or not self.scheduler_thread.is_alive():
            logger.warning("调度器未在运行")
            return

        self.is_running = False
        self.scheduler_thread.join(timeout=5)

        if self.scheduler_thread.is_alive():
            logger.warning("调度器线程未能正常停止")
        else:
            logger.info("调度器已停止")
            self.scheduler_thread = None

# 测试代码
if __name__ == "__main__":
    scheduler = CryptoTradingScheduler()
    scheduler.start()

    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("正在停止调度器...")
        scheduler.stop()
        print("调度器已停止")
