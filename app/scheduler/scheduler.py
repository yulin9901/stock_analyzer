#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
定时任务调度器
用于定时执行数据收集、汇总和决策任务
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
from app.data_collectors.hot_topics_collector import fetch_hot_topics_data, store_hot_topics_data
from app.data_collectors.market_fund_flow_collector import fetch_market_fund_flow_data_from_source, store_market_fund_flow_data
from app.data_processors.daily_summary_processor import process_and_store_daily_summary
from app.decision_makers.buy_decision_chatgpt import get_buy_decision_from_chatgpt

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(APP_DIR, 'logs', 'scheduler.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger('scheduler')

class StockAnalyzerScheduler:
    """股票分析系统定时任务调度器"""

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

        # 初始化API客户端（如果在Manus环境中）
        if os.path.exists("/opt/.manus/.sandbox-runtime"):
            sys.path.append("/opt/.manus/.sandbox-runtime")
            from data_api import ApiClient
            self.api_client = ApiClient()
        else:
            # 使用模拟的API客户端
            class ApiClient:
                def call_api(self, api_name, query):
                    logger.info(f"模拟API调用: {api_name}, 查询: {query}")
                    return {"chart": {"result": None, "error": {"code": "MOCK_ENV", "description": "ApiClient not available outside Manus sandbox"}}}
            self.api_client = ApiClient()

    def collect_hourly_data(self):
        """收集每小时数据（热点和资金流向）"""
        logger.info("开始收集每小时数据...")

        # 收集热点数据
        try:
            logger.info("收集热点数据...")
            topics = fetch_hot_topics_data(api_key=self.config.TIANAPI_KEY)
            if topics:
                store_hot_topics_data(db_config=self.db_config, topics=topics)
                logger.info(f"成功收集并存储了 {len(topics)} 条热点数据")
            else:
                logger.warning("未能获取热点数据或返回为空")
        except Exception as e:
            logger.error(f"收集热点数据时出错: {e}")

        # 收集资金流向数据
        try:
            logger.info("收集资金流向数据...")
            flows = fetch_market_fund_flow_data_from_source()
            if flows:
                store_market_fund_flow_data(db_config=self.db_config, flows_data=flows)
                logger.info(f"成功收集并存储了 {len(flows)} 条资金流向数据")
            else:
                logger.warning("未能获取资金流向数据或返回为空")
        except Exception as e:
            logger.error(f"收集资金流向数据时出错: {e}")

        logger.info("每小时数据收集完成")

    def prepare_market_open(self):
        """开盘前准备（汇总数据并获取买入建议）"""
        logger.info("开始开盘前准备...")
        today = datetime.date.today().strftime("%Y-%m-%d")

        # 汇总数据
        try:
            logger.info(f"汇总 {today} 的数据...")
            success = process_and_store_daily_summary(db_config=self.db_config, target_date_str=today)
            if success:
                logger.info("成功汇总数据")
            else:
                logger.warning("数据汇总失败或未完成")
                return
        except Exception as e:
            logger.error(f"汇总数据时出错: {e}")
            return

        # 获取买入建议
        try:
            logger.info("从ChatGPT获取买入建议...")
            success = get_buy_decision_from_chatgpt(
                db_config=self.db_config,
                openai_api_key=self.config.OPENAI_API_KEY,
                target_date_str=today
            )
            if success:
                logger.info("成功获取买入建议")
            else:
                logger.warning("获取买入建议失败或未完成")
        except Exception as e:
            logger.error(f"获取买入建议时出错: {e}")

        logger.info("开盘前准备完成")

    def is_trading_day(self):
        """判断今天是否是交易日（周一至周五，非法定假日）"""
        from app.scheduler.tasks import is_trading_day as check_trading_day
        return check_trading_day()

    def setup_schedule(self):
        """设置定时任务计划"""
        # 清除现有的所有任务
        schedule.clear()

        # 获取配置中的定时任务设置
        hourly_minute = getattr(self.config, "HOURLY_COLLECTION_MINUTE", 0)
        market_prep_time = getattr(self.config, "MARKET_OPEN_PREP_TIME", "09:00")
        run_on_non_trading_days = getattr(self.config, "RUN_ON_NON_TRADING_DAYS", False)

        # 每小时收集数据
        if hourly_minute == 0:
            # 在整点运行
            if run_on_non_trading_days:
                schedule.every().hour.at(":00").do(self.collect_hourly_data)
            else:
                schedule.every().hour.at(":00").do(self._run_if_trading_day, self.collect_hourly_data)
        else:
            # 在指定分钟运行
            minute_str = f":{hourly_minute:02d}"
            if run_on_non_trading_days:
                schedule.every().hour.at(minute_str).do(self.collect_hourly_data)
            else:
                schedule.every().hour.at(minute_str).do(self._run_if_trading_day, self.collect_hourly_data)

        # 开盘前准备
        if run_on_non_trading_days:
            schedule.every().day.at(market_prep_time).do(self.prepare_market_open)
        else:
            schedule.every().day.at(market_prep_time).do(self._run_if_trading_day, self.prepare_market_open)

        logger.info(f"定时任务计划已设置: 每小时{hourly_minute}分收集数据, {market_prep_time}进行开盘前准备")

    def _run_if_trading_day(self, task_func):
        """仅在交易日运行任务"""
        if self.is_trading_day():
            return task_func()
        else:
            logger.info("今天不是交易日，跳过任务")
            return None

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
    scheduler = StockAnalyzerScheduler()
    scheduler.start()

    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("正在停止调度器...")
        scheduler.stop()
        print("调度器已停止")
