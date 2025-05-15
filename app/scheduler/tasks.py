#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
定时任务定义
定义了系统中的各种定时任务
"""
import os
import sys
import datetime
import logging

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
logger = logging.getLogger('tasks')

def collect_hot_topics():
    """收集热点数据任务"""
    logger.info("开始收集热点数据...")

    try:
        config = load_config()
        db_config = get_db_config(config)

        topics = fetch_hot_topics_data(api_key=config.TIANAPI_KEY)
        if topics:
            inserted_count = store_hot_topics_data(db_config=db_config, topics=topics)
            logger.info(f"成功收集并存储了 {inserted_count} 条热点数据")
            return True
        else:
            logger.warning("未能获取热点数据或返回为空")
            return False
    except Exception as e:
        logger.error(f"收集热点数据时出错: {e}")
        return False

def collect_market_fund_flows():
    """收集市场资金流向数据任务"""
    logger.info("开始收集市场资金流向数据...")

    try:
        config = load_config()
        db_config = get_db_config(config)

        flows = fetch_market_fund_flow_data_from_source()
        if flows:
            inserted_count = store_market_fund_flow_data(db_config=db_config, flows_data=flows)
            logger.info(f"成功收集并存储了 {inserted_count} 条市场资金流向数据")
            return True
        else:
            logger.warning("未能获取市场资金流向数据或返回为空")
            return False
    except Exception as e:
        logger.error(f"收集市场资金流向数据时出错: {e}")
        return False

def summarize_daily_data(target_date_str=None):
    """汇总每日数据任务"""
    if not target_date_str:
        target_date_str = datetime.date.today().strftime("%Y-%m-%d")

    logger.info(f"开始汇总 {target_date_str} 的数据...")

    try:
        config = load_config()
        db_config = get_db_config(config)

        success = process_and_store_daily_summary(db_config=db_config, target_date_str=target_date_str)
        if success:
            logger.info(f"成功汇总 {target_date_str} 的数据")
            return True
        else:
            logger.warning(f"汇总 {target_date_str} 的数据失败或未完成")
            return False
    except Exception as e:
        logger.error(f"汇总 {target_date_str} 的数据时出错: {e}")
        return False

def get_buy_decision(target_date_str=None):
    """获取买入建议任务"""
    if not target_date_str:
        target_date_str = datetime.date.today().strftime("%Y-%m-%d")

    logger.info(f"开始获取 {target_date_str} 的买入建议...")

    try:
        config = load_config()
        db_config = get_db_config(config)

        success = get_buy_decision_from_chatgpt(
            db_config=db_config,
            openai_api_key=config.OPENAI_API_KEY,
            target_date_str=target_date_str
        )
        if success:
            logger.info(f"成功获取 {target_date_str} 的买入建议")
            return True
        else:
            logger.warning(f"获取 {target_date_str} 的买入建议失败或未完成")
            return False
    except Exception as e:
        logger.error(f"获取 {target_date_str} 的买入建议时出错: {e}")
        return False

def is_trading_day(date_str=None):
    """判断指定日期是否是交易日（周一至周五，非法定假日）

    Args:
        date_str (str, optional): 日期字符串，格式为'YYYY-MM-DD'。默认为今天。

    Returns:
        bool: 是否是交易日
    """
    if date_str:
        try:
            target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"无效的日期格式: {date_str}，应为YYYY-MM-DD")
            return False
    else:
        target_date = datetime.date.today()

    # 检查是否是周末
    if target_date.weekday() >= 5:  # 5=周六, 6=周日
        logger.info(f"{target_date.strftime('%Y-%m-%d')} 是周末，非交易日")
        return False

    # 中国法定节假日列表（部分）
    # 这里只列出了一些主要节假日，实际使用时应该更完整
    # 最好使用API或每年更新的节假日数据

    holidays_2024 = [
        "2024-01-01",  # 元旦
        "2024-02-10", "2024-02-11", "2024-02-12", "2024-02-13", "2024-02-14", "2024-02-15", "2024-02-16", "2024-02-17",  # 春节
        "2024-04-04", "2024-04-05", "2024-04-06",  # 清明节
        "2024-05-01", "2024-05-02", "2024-05-03", "2024-05-04", "2024-05-05",  # 劳动节
        "2024-06-08", "2024-06-09", "2024-06-10",  # 端午节
        "2024-09-15", "2024-09-16", "2024-09-17",  # 中秋节
        "2024-10-01", "2024-10-02", "2024-10-03", "2024-10-04", "2024-10-05", "2024-10-06", "2024-10-07",  # 国庆节
    ]
    
    holidays_2025 = [
        "2025-01-01",  # 元旦
        "2025-01-02",  # 元旦调休
        "2025-01-21", "2025-01-22", "2025-01-23", "2025-01-24", "2025-01-25", "2025-01-26", "2025-01-27",  # 春节
        "2025-04-05",  # 清明节
        "2025-05-01", "2025-05-02", "2025-05-03",  # 劳动节
        "2025-06-22", "2025-06-23", "2025-06-24",  # 端午节
        "2025-09-29", "2025-09-30", "2025-10-01", "2025-10-02", "2025-10-03", "2025-10-04", "2025-10-05", "2025-10-06",  # 中秋节和国庆节
    ]

    # 合并节假日列表
    holidays = holidays_2024 + holidays_2025

    # 检查是否是法定节假日
    date_str = target_date.strftime("%Y-%m-%d")
    if date_str in holidays:
        logger.info(f"{date_str} 是法定节假日，非交易日")
        return False

    logger.info(f"{date_str} 是交易日")
    return True

# 测试代码
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 测试收集热点数据
    collect_hot_topics()

    # 测试收集市场资金流向数据
    collect_market_fund_flows()

    # 测试汇总每日数据
    summarize_daily_data()

    # 测试获取买入建议
    get_buy_decision()
