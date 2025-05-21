#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
加密货币新闻收集模块
用于从各种来源收集加密货币相关的新闻和社交媒体数据
"""
import os
import sys
import json
import datetime
import logging
import requests
from typing import List, Dict, Any, Optional, Union
from textblob import TextBlob

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.database.db_manager import DatabaseManager

# 配置日志
logger = logging.getLogger('crypto_news_collector')

# 天行数据API接口
TIANAPI_CRYPTO_NEWS_URL = "http://api.tianapi.com/caijing/index"

def analyze_sentiment(text: str) -> str:
    """
    使用TextBlob分析文本情感
    
    Args:
        text (str): 要分析的文本
        
    Returns:
        str: 情感分析结果 (positive, negative, neutral)
    """
    if not text:
        return "neutral"
        
    try:
        analysis = TextBlob(text)
        # 获取极性分数 (-1.0 到 1.0)
        polarity = analysis.sentiment.polarity
        
        if polarity > 0.1:
            return "positive"
        elif polarity < -0.1:
            return "negative"
        else:
            return "neutral"
    except Exception as e:
        logger.error(f"情感分析失败: {e}")
        return "neutral"

def fetch_tianapi_crypto_news(api_key: str, num: int = 20) -> List[Dict[str, Any]]:
    """
    从天行数据API获取加密货币相关财经新闻
    
    Args:
        api_key (str): 天行数据API密钥
        num (int): 获取的新闻数量
        
    Returns:
        List[Dict[str, Any]]: 新闻数据列表
    """
    news_data = []
    params = {
        "key": api_key,
        "num": num,
        "word": "比特币,加密货币,区块链,数字货币,以太坊"  # 添加关键词过滤
    }
    
    try:
        response = requests.get(TIANAPI_CRYPTO_NEWS_URL, params=params)
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") == 200:
            news_list = result.get("newslist", [])
            
            for item in news_list:
                # 解析时间戳
                try:
                    timestamp_str = item.get("ctime", "")
                    timestamp_val = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    timestamp_val = datetime.datetime.now()
                
                # 处理内容摘要
                description = item.get("description", "")
                
                # 分析情感
                sentiment = analyze_sentiment(description)
                
                news_item = {
                    "timestamp": timestamp_val.strftime("%Y-%m-%d %H:%M:%S"),
                    "source": item.get("source", "天行数据"),
                    "title": item.get("title", "无标题"),
                    "url": item.get("url", ""),
                    "content_summary": description,
                    "sentiment": sentiment,
                    "retrieved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                news_data.append(news_item)
            
            logger.info(f"成功从天行数据获取{len(news_data)}条加密货币新闻")
        else:
            logger.error(f"天行数据API返回错误: {result.get('msg')}")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"请求天行数据API失败: {e}")
    except json.JSONDecodeError:
        logger.error("解析天行数据API响应失败")
    except Exception as e:
        logger.error(f"获取天行数据加密货币新闻时出错: {e}")
    
    return news_data

def fetch_coindesk_news(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    从CoinDesk获取加密货币新闻
    
    Args:
        api_key (Optional[str]): CoinDesk API密钥（如果需要）
        
    Returns:
        List[Dict[str, Any]]: 新闻数据列表
    """
    news_data = []
    
    # CoinDesk RSS Feed URL
    url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # 解析RSS内容
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        # 查找所有item元素
        for item in root.findall(".//item"):
            title_elem = item.find("title")
            link_elem = item.find("link")
            desc_elem = item.find("description")
            date_elem = item.find("pubDate")
            
            title = title_elem.text if title_elem is not None else "无标题"
            link = link_elem.text if link_elem is not None else ""
            description = desc_elem.text if desc_elem is not None else ""
            
            # 解析发布日期
            pub_date = datetime.datetime.now()
            if date_elem is not None and date_elem.text:
                try:
                    # RSS日期格式通常是: Wed, 21 Oct 2020 14:30:00 +0000
                    pub_date = datetime.datetime.strptime(date_elem.text, "%a, %d %b %Y %H:%M:%S %z")
                except ValueError:
                    pass
            
            # 分析情感
            sentiment = analyze_sentiment(description)
            
            news_item = {
                "timestamp": pub_date.strftime("%Y-%m-%d %H:%M:%S"),
                "source": "CoinDesk",
                "title": title,
                "url": link,
                "content_summary": description,
                "sentiment": sentiment,
                "retrieved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            news_data.append(news_item)
        
        logger.info(f"成功从CoinDesk获取{len(news_data)}条加密货币新闻")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"请求CoinDesk RSS失败: {e}")
    except ET.ParseError:
        logger.error("解析CoinDesk RSS内容失败")
    except Exception as e:
        logger.error(f"获取CoinDesk新闻时出错: {e}")
    
    return news_data

def store_crypto_news_data(db_config: Dict[str, Any], news_data: List[Dict[str, Any]]) -> int:
    """
    将加密货币新闻数据存储到数据库
    
    Args:
        db_config (Dict[str, Any]): 数据库配置
        news_data (List[Dict[str, Any]]): 新闻数据列表
        
    Returns:
        int: 成功插入的记录数
    """
    if not news_data:
        logger.warning("没有加密货币新闻数据可存储")
        return 0
    
    db_manager = DatabaseManager(db_config)
    inserted_count = 0
    
    try:
        with db_manager.get_connection() as (connection, cursor):
            add_news_sql = ("""
            INSERT INTO hot_topics
            (timestamp, source, title, url, content_summary, sentiment, retrieved_at)
            VALUES (%(timestamp)s, %(source)s, %(title)s, %(url)s, %(content_summary)s, %(sentiment)s, %(retrieved_at)s)
            ON DUPLICATE KEY UPDATE 
            title=VALUES(title), 
            content_summary=VALUES(content_summary), 
            sentiment=VALUES(sentiment),
            retrieved_at=VALUES(retrieved_at)
            """)
            
            for news_item in news_data:
                try:
                    cursor.execute(add_news_sql, news_item)
                    inserted_count += 1
                except Exception as err:
                    logger.error(f"数据库错误，无法存储新闻 '{news_item.get('title')}': {err}")
            
            connection.commit()
            logger.info(f"成功存储了{inserted_count}条加密货币新闻")
    
    except Exception as err:
        logger.error(f"连接数据库或执行查询时出错: {err}")
        return 0
    
    return inserted_count

def fetch_crypto_hot_topics(api_key: str) -> List[Dict[str, Any]]:
    """
    获取加密货币热点话题（整合多个来源）
    
    Args:
        api_key (str): 天行数据API密钥
        
    Returns:
        List[Dict[str, Any]]: 热点话题数据列表
    """
    all_news = []
    
    # 从天行数据获取新闻
    tianapi_news = fetch_tianapi_crypto_news(api_key)
    all_news.extend(tianapi_news)
    
    # 从CoinDesk获取新闻
    coindesk_news = fetch_coindesk_news()
    all_news.extend(coindesk_news)
    
    # 可以添加更多来源...
    
    logger.info(f"总共获取了{len(all_news)}条加密货币热点话题")
    return all_news

# 如果直接运行此脚本，执行测试
if __name__ == "__main__":
    print("执行crypto_news_collector.py作为独立脚本（用于测试）")
    
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
        api_key = "YOUR_TIANAPI_KEY_HERE"
        db_config = {
            "DB_HOST": "localhost",
            "DB_PORT": 3306,
            "DB_USER": "your_db_user",
            "DB_PASSWORD": "your_db_password",
            "DB_NAME": "crypto_trading"
        }
    
    if api_key != "YOUR_TIANAPI_KEY_HERE":
        # 测试获取加密货币热点话题
        hot_topics = fetch_crypto_hot_topics(api_key)
        
        if hot_topics:
            print(f"获取到{len(hot_topics)}条加密货币热点话题")
            
            # 打印前3条热点话题
            for i, topic in enumerate(hot_topics[:3]):
                print(f"\n热点话题 {i+1}:")
                print(f"标题: {topic['title']}")
                print(f"来源: {topic['source']}")
                print(f"情感: {topic['sentiment']}")
                print(f"摘要: {topic['content_summary'][:100]}...")
            
            # 如果数据库配置有效，存储热点话题
            if db_config["DB_USER"] != "your_db_user":
                inserted = store_crypto_news_data(db_config, hot_topics)
                print(f"存储了{inserted}条热点话题")
    else:
        print("未提供有效的天行数据API密钥，无法执行测试")
