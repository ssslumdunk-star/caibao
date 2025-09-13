#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
雅虎财经财报数据API模块
专门优化雅虎财经的数据抓取功能，确保高成功率
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import json
import re
import time
import random
import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from config import CUSTOM_HEADERS, REQUEST_TIMEOUT, MIN_DELAY, MAX_DELAY, MAX_RETRIES

logger = logging.getLogger('YahooEarningsAPI')

@dataclass
class YahooEarningsEvent:
    """雅虎财经财报事件数据结构"""
    symbol: str
    company_name: str
    earnings_date: str
    earnings_time: str  # BMO (Before Market Open), AMC (After Market Close)
    quarter: str
    fiscal_year: int
    eps_estimate: Optional[float] = None
    eps_actual: Optional[float] = None
    revenue_estimate: Optional[float] = None
    revenue_actual: Optional[float] = None
    surprise_percent: Optional[float] = None
    market_cap: Optional[str] = None

@dataclass
class YahooAnalystData:
    """雅虎财经分析师数据"""
    symbol: str
    current_price: float
    target_mean: Optional[float] = None
    target_high: Optional[float] = None
    target_low: Optional[float] = None
    recommendation_mean: Optional[float] = None  # 1=Strong Buy, 5=Strong Sell
    recommendation_key: Optional[str] = None  # "buy", "hold", "sell"
    analyst_count: Optional[int] = None
    last_updated: Optional[str] = None

class YahooEarningsAPI:
    """雅虎财经财报API类"""
    
    def __init__(self):
        self.headers = CUSTOM_HEADERS.copy()
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 雅虎财经的基础URLs
        self.base_urls = {
            'calendar': 'https://finance.yahoo.com/calendar/earnings',
            'quote': 'https://finance.yahoo.com/quote/{symbol}',
            'analysis': 'https://finance.yahoo.com/quote/{symbol}/analysis',
            'api_v1': 'https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}',
            'api_v2': 'https://query2.finance.yahoo.com/v1/finance/search',
            'calendar_api': 'https://finance.yahoo.com/calendar/earnings?from={start_date}&to={end_date}&day={date}'
        }
        
    def _make_request(self, url: str, params: dict = None, use_api: bool = False) -> Optional[requests.Response]:
        """优化的请求方法，专门针对雅虎财经"""
        retry_count = 0
        
        # 为API请求添加特殊头部
        headers = self.headers.copy()
        if use_api:
            headers.update({
                'Referer': 'https://finance.yahoo.com/',
                'X-Requested-With': 'XMLHttpRequest',
                'Cache-Control': 'no-cache'
            })
        
        while retry_count < MAX_RETRIES:
            try:
                # 随机延迟
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                time.sleep(delay)
                
                response = self.session.get(
                    url, 
                    params=params, 
                    headers=headers,
                    timeout=REQUEST_TIMEOUT
                )
                
                # 检查是否被限制
                if response.status_code == 429:  # Too Many Requests
                    logger.warning("请求频率过高，等待更长时间...")
                    time.sleep(random.uniform(10, 20))
                    retry_count += 1
                    continue
                    
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                retry_count += 1
                logger.warning(f"雅虎财经请求失败 (第{retry_count}次重试): {url} - {str(e)}")
                
                if retry_count < MAX_RETRIES:
                    sleep_time = random.uniform(3, 8) * retry_count
                    time.sleep(sleep_time)
                    
        logger.error(f"雅虎财经请求最终失败: {url}")
        return None

    def get_earnings_calendar(self, start_date: str = None, end_date: str = None) -> List[YahooEarningsEvent]:
        """
        从雅虎财经获取财报日历
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            财报事件列表
        """
        if start_date is None:
            start_date = datetime.now().strftime('%Y-%m-%d')
        if end_date is None:
            end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            
        events = []
        logger.info(f"正在从雅虎财经获取财报日历: {start_date} 到 {end_date}")
        
        try:
            # 方法1: 通过财报日历页面抓取
            calendar_events = self._scrape_earnings_calendar_page(start_date, end_date)
            events.extend(calendar_events)
            
            # 方法2: 通过API获取补充数据
            api_events = self._fetch_earnings_via_api(start_date, end_date)
            events.extend(api_events)
            
            # 去重并排序
            events = self._deduplicate_events(events)
            events.sort(key=lambda x: x.earnings_date)
            
            logger.info(f"成功获取 {len(events)} 个财报事件")
            
        except Exception as e:
            logger.error(f"获取雅虎财经财报日历失败: {str(e)}")
            
        return events

    def _scrape_earnings_calendar_page(self, start_date: str, end_date: str) -> List[YahooEarningsEvent]:
        """抓取雅虎财经财报日历页面"""
        events = []
        
        try:
            # 构建URL
            url = self.base_urls['calendar']
            params = {
                'from': start_date,
                'to': end_date,
                'day': start_date  # 从指定日期开始
            }
            
            response = self._make_request(url, params=params)
            if not response:
                return events
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找财报数据表格
            # 雅虎财经通常使用特定的class名称
            table_selectors = [
                'table[data-test="earnings-calendar-table"]',
                'table.W\\(100\\%\\)',
                'div[data-test="earnings-calendar"] table',
                'table tbody tr'
            ]
            
            for selector in table_selectors:
                try:
                    if 'tbody tr' in selector:
                        rows = soup.select(selector)
                    else:
                        table = soup.select_one(selector)
                        if table:
                            rows = table.find_all('tr')[1:]  # 跳过表头
                        else:
                            continue
                    
                    if rows:
                        logger.info(f"使用选择器找到 {len(rows)} 行数据: {selector}")
                        break
                        
                except Exception as e:
                    logger.debug(f"选择器 {selector} 失败: {str(e)}")
                    continue
            else:
                # 如果所有选择器都失败，尝试通用方法
                rows = soup.find_all('tr')
                logger.info(f"使用通用方法找到 {len(rows)} 行数据")
            
            # 解析表格行
            for row in rows:
                try:
                    event = self._parse_calendar_row(row)
                    if event:
                        events.append(event)
                        
                except Exception as e:
                    logger.debug(f"解析行数据失败: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"抓取雅虎财经日历页面失败: {str(e)}")
            
        return events

    def _parse_calendar_row(self, row) -> Optional[YahooEarningsEvent]:
        """解析日历表格行"""
        try:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 4:  # 至少需要公司、日期、时间、预期EPS
                return None
                
            # 提取数据 - 雅虎财经的列顺序通常是:
            # [公司名称/代码, 日期, 时间, 预期EPS, 实际EPS]
            
            # 公司信息 (通常包含symbol和company name)
            company_cell = cells[0]
            symbol_link = company_cell.find('a')
            if symbol_link:
                symbol = self._extract_symbol_from_link(symbol_link.get('href', ''))
                company_name = symbol_link.get_text(strip=True)
            else:
                # 备用方法
                text = company_cell.get_text(strip=True)
                symbol = self._extract_symbol_from_text(text)
                company_name = text
            
            if not symbol:
                return None
                
            # 日期
            date_cell = cells[1] if len(cells) > 1 else None
            earnings_date = self._parse_date(date_cell.get_text(strip=True)) if date_cell else None
            
            # 时间 (BMO/AMC)
            time_cell = cells[2] if len(cells) > 2 else None
            earnings_time = time_cell.get_text(strip=True) if time_cell else "N/A"
            
            # 预期EPS
            eps_estimate_cell = cells[3] if len(cells) > 3 else None
            eps_estimate = self._parse_number(eps_estimate_cell.get_text(strip=True)) if eps_estimate_cell else None
            
            # 实际EPS (如果有)
            eps_actual = None
            if len(cells) > 4:
                eps_actual_cell = cells[4]
                eps_actual = self._parse_number(eps_actual_cell.get_text(strip=True))
            
            # 计算季度和财政年度
            quarter, fiscal_year = self._calculate_quarter_and_year(earnings_date)
            
            event = YahooEarningsEvent(
                symbol=symbol,
                company_name=company_name,
                earnings_date=earnings_date or datetime.now().strftime('%Y-%m-%d'),
                earnings_time=earnings_time,
                quarter=quarter,
                fiscal_year=fiscal_year,
                eps_estimate=eps_estimate,
                eps_actual=eps_actual
            )
            
            return event
            
        except Exception as e:
            logger.debug(f"解析日历行失败: {str(e)}")
            return None

    def _fetch_earnings_via_api(self, start_date: str, end_date: str) -> List[YahooEarningsEvent]:
        """通过雅虎财经API获取财报数据"""
        events = []
        
        try:
            # 雅虎财经的quoteSummary API
            # 这个方法需要先获取symbol列表，然后逐个查询
            
            # 从热门股票开始
            from config import DEFAULT_TICKERS
            symbols = DEFAULT_TICKERS[:10]  # 限制数量避免过多请求
            
            for symbol in symbols:
                try:
                    event = self._fetch_single_stock_earnings(symbol)
                    if event and self._is_date_in_range(event.earnings_date, start_date, end_date):
                        events.append(event)
                        
                except Exception as e:
                    logger.debug(f"API获取 {symbol} 失败: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"API获取财报数据失败: {str(e)}")
            
        return events

    def _fetch_single_stock_earnings(self, symbol: str) -> Optional[YahooEarningsEvent]:
        """获取单个股票的财报信息"""
        try:
            # 使用quoteSummary API
            url = self.base_urls['api_v1'].format(symbol=symbol)
            params = {
                'modules': 'calendarEvents,earningsHistory,financialData',
                'formatted': 'true'
            }
            
            response = self._make_request(url, params=params, use_api=True)
            if not response:
                return None
                
            data = response.json()
            
            if 'quoteSummary' not in data or 'result' not in data['quoteSummary']:
                return None
                
            result = data['quoteSummary']['result'][0]
            
            # 提取财报日期
            earnings_date = None
            earnings_time = "N/A"
            
            if 'calendarEvents' in result:
                calendar_events = result['calendarEvents']
                if 'earnings' in calendar_events:
                    earnings = calendar_events['earnings']
                    if 'earningsDate' in earnings and earnings['earningsDate']:
                        # 获取下一个财报日期
                        next_earnings = earnings['earningsDate'][0] if earnings['earningsDate'] else None
                        if next_earnings:
                            earnings_date = datetime.fromtimestamp(next_earnings['raw']).strftime('%Y-%m-%d')
            
            # 提取其他信息
            company_name = symbol  # 默认使用symbol
            eps_estimate = None
            
            if earnings_date:
                quarter, fiscal_year = self._calculate_quarter_and_year(earnings_date)
                
                event = YahooEarningsEvent(
                    symbol=symbol,
                    company_name=company_name,
                    earnings_date=earnings_date,
                    earnings_time=earnings_time,
                    quarter=quarter,
                    fiscal_year=fiscal_year,
                    eps_estimate=eps_estimate
                )
                
                return event
                
        except Exception as e:
            logger.debug(f"获取 {symbol} 单股财报信息失败: {str(e)}")
            
        return None

    def get_analyst_recommendations(self, symbol: str) -> Optional[YahooAnalystData]:
        """获取雅虎财经的分析师推荐数据"""
        try:
            url = self.base_urls['api_v1'].format(symbol=symbol)
            params = {
                'modules': 'recommendationTrend,financialData,price',
                'formatted': 'true'
            }
            
            response = self._make_request(url, params=params, use_api=True)
            if not response:
                return None
                
            data = response.json()
            
            if 'quoteSummary' not in data or 'result' not in data['quoteSummary']:
                return None
                
            result = data['quoteSummary']['result'][0]
            
            # 提取当前价格
            current_price = 0
            if 'price' in result and 'regularMarketPrice' in result['price']:
                current_price = result['price']['regularMarketPrice'].get('raw', 0)
            
            # 提取分析师数据
            analyst_data = YahooAnalystData(
                symbol=symbol,
                current_price=current_price
            )
            
            if 'financialData' in result:
                financial_data = result['financialData']
                
                if 'targetMeanPrice' in financial_data:
                    analyst_data.target_mean = financial_data['targetMeanPrice'].get('raw')
                if 'targetHighPrice' in financial_data:
                    analyst_data.target_high = financial_data['targetHighPrice'].get('raw')
                if 'targetLowPrice' in financial_data:
                    analyst_data.target_low = financial_data['targetLowPrice'].get('raw')
                if 'recommendationMean' in financial_data:
                    analyst_data.recommendation_mean = financial_data['recommendationMean'].get('raw')
                if 'recommendationKey' in financial_data:
                    analyst_data.recommendation_key = financial_data['recommendationKey'].get('raw')
            
            if 'recommendationTrend' in result:
                trend = result['recommendationTrend']
                if 'trend' in trend and trend['trend']:
                    latest = trend['trend'][0]  # 最新的推荐
                    if 'strongBuy' in latest and 'buy' in latest:
                        total_analysts = sum([
                            latest.get('strongBuy', 0),
                            latest.get('buy', 0),
                            latest.get('hold', 0),
                            latest.get('sell', 0),
                            latest.get('strongSell', 0)
                        ])
                        analyst_data.analyst_count = total_analysts
            
            analyst_data.last_updated = datetime.now().strftime('%Y-%m-%d')
            
            return analyst_data
            
        except Exception as e:
            logger.error(f"获取 {symbol} 分析师数据失败: {str(e)}")
            return None

    def get_earnings_details(self, symbol: str, earnings_date: str) -> Dict:
        """获取特定财报的详细信息"""
        try:
            # 获取基本财报信息
            earnings_event = self._fetch_single_stock_earnings(symbol)
            
            # 获取分析师数据
            analyst_data = self.get_analyst_recommendations(symbol)
            
            # 组合数据
            details = {
                'symbol': symbol,
                'earnings_date': earnings_date,
                'company_name': symbol,  # 可以后续优化获取完整公司名
                'quarter': '',
                'fiscal_year': datetime.now().year
            }
            
            if earnings_event:
                details.update(asdict(earnings_event))
                
            if analyst_data:
                details['analyst_data'] = asdict(analyst_data)
                
            # 获取分析师评论 (从网页抓取)
            comments = self._scrape_analyst_comments(symbol)
            details['analyst_comments'] = comments
            
            return details
            
        except Exception as e:
            logger.error(f"获取 {symbol} 财报详情失败: {str(e)}")
            return {}

    def _scrape_analyst_comments(self, symbol: str) -> List[Dict]:
        """从雅虎财经抓取分析师评论"""
        comments = []
        
        try:
            url = self.base_urls['analysis'].format(symbol=symbol)
            response = self._make_request(url)
            
            if not response:
                return comments
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找分析师评论区域
            # 这里需要根据雅虎财经的实际页面结构调整选择器
            comment_selectors = [
                'div[data-test="analysis-content"]',
                'div.analysis-content',
                'section.analysis',
                'div.recommendation'
            ]
            
            for selector in comment_selectors:
                elements = soup.select(selector)
                if elements:
                    for element in elements[:5]:  # 限制数量
                        try:
                            comment_text = element.get_text(strip=True)
                            if comment_text and len(comment_text) > 20:  # 过滤太短的内容
                                comment = {
                                    'analyst_name': 'Yahoo Finance Analysis',
                                    'firm': 'Yahoo Finance',
                                    'rating': 'Analysis',
                                    'price_target': None,
                                    'comment': comment_text[:500],  # 限制长度
                                    'publish_date': datetime.now().strftime('%Y-%m-%d'),
                                    'source': 'Yahoo Finance'
                                }
                                comments.append(comment)
                                
                        except Exception as e:
                            logger.debug(f"解析分析师评论失败: {str(e)}")
                            continue
                    break
                    
        except Exception as e:
            logger.error(f"抓取 {symbol} 分析师评论失败: {str(e)}")
            
        return comments

    # 工具方法
    def _extract_symbol_from_link(self, href: str) -> str:
        """从链接中提取股票代码"""
        if not href:
            return ""
        
        # 雅虎财经链接格式: /quote/AAPL/ 或 /quote/AAPL
        match = re.search(r'/quote/([^/\?]+)', href)
        if match:
            return match.group(1).upper()
        
        return ""

    def _extract_symbol_from_text(self, text: str) -> str:
        """从文本中提取股票代码"""
        if not text:
            return ""
        
        # 查找括号中的代码，如 "Apple Inc. (AAPL)"
        match = re.search(r'\(([A-Z]+)\)', text)
        if match:
            return match.group(1)
        
        # 查找纯大写字母，如 "AAPL"
        match = re.search(r'\b[A-Z]{1,5}\b', text)
        if match:
            return match.group(0)
        
        return ""

    def _parse_date(self, date_str: str) -> Optional[str]:
        """解析日期字符串"""
        if not date_str or date_str.lower() in ['n/a', '-', 'tbd']:
            return None
            
        try:
            # 雅虎财经常用的日期格式
            date_formats = [
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%m-%d-%Y',
                '%b %d, %Y',
                '%B %d, %Y',
                '%d %b %Y',
                '%m/%d/%y'
            ]
            
            clean_date = date_str.strip()
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(clean_date, fmt)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
                    
        except Exception:
            pass
            
        return None

    def _parse_number(self, value_str: str) -> Optional[float]:
        """解析数字字符串"""
        if not value_str or value_str.lower() in ['n/a', '-', 'tbd', '']:
            return None
            
        try:
            # 清理字符串
            clean_value = re.sub(r'[^\d\.\-\+]', '', value_str.strip())
            if clean_value:
                return float(clean_value)
        except (ValueError, AttributeError):
            pass
            
        return None

    def _calculate_quarter_and_year(self, date_str: str) -> Tuple[str, int]:
        """计算季度和财政年度"""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            month = date_obj.month
            year = date_obj.year
            
            if month in [1, 2, 3]:
                quarter = f"Q1 {year}"
            elif month in [4, 5, 6]:
                quarter = f"Q2 {year}"  
            elif month in [7, 8, 9]:
                quarter = f"Q3 {year}"
            else:
                quarter = f"Q4 {year}"
                
            return quarter, year
            
        except:
            current_year = datetime.now().year
            return f"Q1 {current_year}", current_year

    def _is_date_in_range(self, date_str: str, start_date: str, end_date: str) -> bool:
        """检查日期是否在指定范围内"""
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            return start <= target_date <= end
        except:
            return False

    def _deduplicate_events(self, events: List[YahooEarningsEvent]) -> List[YahooEarningsEvent]:
        """去除重复事件"""
        seen = set()
        unique_events = []
        
        for event in events:
            key = (event.symbol, event.earnings_date)
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
                
        return unique_events

if __name__ == "__main__":
    # 测试代码
    yahoo_api = YahooEarningsAPI()
    
    print("测试雅虎财经财报API...")
    
    # 测试获取财报日历
    events = yahoo_api.get_earnings_calendar()
    print(f"获取到 {len(events)} 个财报事件")
    
    for event in events[:3]:
        print(f"  {event.symbol} ({event.company_name})")
        print(f"    日期: {event.earnings_date} {event.earnings_time}")
        print(f"    季度: {event.quarter}")
        if event.eps_estimate:
            print(f"    预期EPS: ${event.eps_estimate:.2f}")
        print()
    
    # 测试获取分析师数据
    if events:
        test_symbol = events[0].symbol
        print(f"测试获取 {test_symbol} 的分析师数据...")
        
        analyst_data = yahoo_api.get_analyst_recommendations(test_symbol)
        if analyst_data:
            print(f"  当前价格: ${analyst_data.current_price:.2f}")
            if analyst_data.target_mean:
                print(f"  目标价格: ${analyst_data.target_mean:.2f}")
            if analyst_data.recommendation_key:
                print(f"  推荐等级: {analyst_data.recommendation_key}")
        else:
            print("  获取分析师数据失败")