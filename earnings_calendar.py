#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财报日历功能模块
功能：
1. 获取股票财报发布日期
2. 创建交互式日历界面  
3. 抓取分析师评论和预测
4. 提供点击查看详细信息功能
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta, date
import json
import os
import time
import random
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import calendar
from config import CUSTOM_HEADERS, REQUEST_TIMEOUT, MIN_DELAY, MAX_DELAY, MAX_RETRIES

# 配置日志
logger = logging.getLogger('EarningsCalendar')

@dataclass
class EarningsEvent:
    """财报事件数据结构"""
    symbol: str
    company_name: str
    earnings_date: str  # YYYY-MM-DD 格式
    quarter: str  # 如 "Q3 2024"
    fiscal_year: int
    estimated_eps: Optional[float] = None
    actual_eps: Optional[float] = None
    estimated_revenue: Optional[float] = None
    actual_revenue: Optional[float] = None
    beat_estimate: Optional[bool] = None
    market_cap: Optional[str] = None
    sector: Optional[str] = None
    announcement_type: str = "earnings"  # earnings, guidance, etc.

@dataclass  
class AnalystComment:
    """分析师评论数据结构"""
    analyst_name: str
    firm: str
    rating: str  # Buy/Hold/Sell
    price_target: Optional[float]
    comment: str
    publish_date: str
    source: str

class EarningsCalendar:
    """财报日历类"""
    
    def __init__(self):
        self.headers = CUSTOM_HEADERS
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 数据缓存
        self.earnings_data = {}
        self.analyst_comments = {}
        
        # 确保数据目录存在
        os.makedirs('data/calendar', exist_ok=True)
        
    def _make_request(self, url: str, method: str = 'get', **kwargs) -> Optional[requests.Response]:
        """带重试机制的HTTP请求"""
        retry_count = 0
        
        while retry_count < MAX_RETRIES:
            try:
                # 随机延迟避免被封
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                time.sleep(delay)
                
                if method.lower() == 'get':
                    response = self.session.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
                else:
                    response = self.session.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
                    
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                retry_count += 1
                logger.warning(f"请求失败 (第{retry_count}次重试): {url} - {str(e)}")
                
                if retry_count < MAX_RETRIES:
                    sleep_time = random.uniform(2, 5) * retry_count
                    time.sleep(sleep_time)
                else:
                    logger.error(f"请求失败，已达到最大重试次数: {url}")
                    
        return None

    def get_earnings_dates(self, symbols: List[str], start_date: str = None, end_date: str = None) -> List[EarningsEvent]:
        """
        获取指定股票的财报发布日期
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            财报事件列表
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')
            
        earnings_events = []
        
        logger.info(f"正在获取财报日期数据，时间范围: {start_date} 到 {end_date}")
        
        for symbol in symbols:
            try:
                # 从 Yahoo Finance 获取财报日期
                events = self._fetch_yahoo_earnings(symbol, start_date, end_date)
                earnings_events.extend(events)
                
                # 从 Seeking Alpha 获取补充数据
                sa_events = self._fetch_seeking_alpha_earnings(symbol, start_date, end_date)
                earnings_events.extend(sa_events)
                
            except Exception as e:
                logger.error(f"获取 {symbol} 财报数据失败: {str(e)}")
                continue
                
        # 去重并排序
        earnings_events = self._deduplicate_events(earnings_events)
        earnings_events.sort(key=lambda x: x.earnings_date)
        
        # 缓存数据
        self.earnings_data[f"{start_date}_{end_date}"] = earnings_events
        
        return earnings_events
    
    def _fetch_yahoo_earnings(self, symbol: str, start_date: str, end_date: str) -> List[EarningsEvent]:
        """从 Yahoo Finance 获取财报数据"""
        events = []
        
        try:
            # Yahoo Finance 财报日历API
            url = f"https://finance.yahoo.com/calendar/earnings"
            params = {
                'symbol': symbol,
                'from': start_date,
                'to': end_date
            }
            
            response = self._make_request(url, params=params)
            if not response:
                return events
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 解析财报数据表格
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # 跳过表头
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        try:
                            # 提取数据
                            company_name = cols[0].get_text(strip=True)
                            earnings_date = cols[1].get_text(strip=True)
                            eps_estimate = self._parse_float(cols[2].get_text(strip=True))
                            reported_eps = self._parse_float(cols[3].get_text(strip=True))
                            
                            # 转换日期格式
                            earnings_date = self._parse_date(earnings_date)
                            if not earnings_date:
                                continue
                                
                            event = EarningsEvent(
                                symbol=symbol,
                                company_name=company_name,
                                earnings_date=earnings_date,
                                quarter=self._get_quarter_from_date(earnings_date),
                                fiscal_year=int(earnings_date.split('-')[0]),
                                estimated_eps=eps_estimate,
                                actual_eps=reported_eps,
                                beat_estimate=self._calculate_beat_estimate(reported_eps, eps_estimate)
                            )
                            
                            events.append(event)
                            
                        except Exception as e:
                            logger.debug(f"解析Yahoo行数据失败: {str(e)}")
                            continue
                            
        except Exception as e:
            logger.warning(f"从Yahoo获取 {symbol} 数据失败: {str(e)}")
            
        return events
    
    def _fetch_seeking_alpha_earnings(self, symbol: str, start_date: str, end_date: str) -> List[EarningsEvent]:
        """从 Seeking Alpha 获取财报数据"""
        events = []
        
        try:
            # Seeking Alpha API (公开API)
            url = f"https://seekingalpha.com/api/v3/earnings_calendar"
            params = {
                'filter[slug]': symbol.lower(),
                'filter[date_from]': start_date,
                'filter[date_to]': end_date,
                'page[size]': 50
            }
            
            response = self._make_request(url, params=params)
            if not response:
                return events
                
            try:
                data = response.json()
                
                if 'data' in data:
                    for item in data['data']:
                        try:
                            attributes = item.get('attributes', {})
                            
                            event = EarningsEvent(
                                symbol=symbol,
                                company_name=attributes.get('company_name', ''),
                                earnings_date=attributes.get('release_date', ''),
                                quarter=attributes.get('period', ''),
                                fiscal_year=attributes.get('fiscal_year', 0),
                                estimated_eps=self._parse_float(attributes.get('eps_estimate')),
                                actual_eps=self._parse_float(attributes.get('eps_actual')),
                                estimated_revenue=self._parse_float(attributes.get('revenue_estimate')),
                                actual_revenue=self._parse_float(attributes.get('revenue_actual')),
                                market_cap=attributes.get('market_cap'),
                                sector=attributes.get('sector')
                            )
                            
                            events.append(event)
                            
                        except Exception as e:
                            logger.debug(f"解析Seeking Alpha数据项失败: {str(e)}")
                            continue
                            
            except json.JSONDecodeError:
                logger.warning(f"Seeking Alpha返回的不是有效JSON: {symbol}")
                
        except Exception as e:
            logger.warning(f"从Seeking Alpha获取 {symbol} 数据失败: {str(e)}")
            
        return events
    
    def get_analyst_comments(self, symbol: str, earnings_date: str) -> List[AnalystComment]:
        """
        获取分析师对特定财报的评论
        
        Args:
            symbol: 股票代码
            earnings_date: 财报日期
            
        Returns:
            分析师评论列表
        """
        cache_key = f"{symbol}_{earnings_date}"
        
        if cache_key in self.analyst_comments:
            return self.analyst_comments[cache_key]
            
        comments = []
        
        try:
            # 从多个来源获取分析师评论
            yahoo_comments = self._fetch_yahoo_analyst_comments(symbol, earnings_date)
            comments.extend(yahoo_comments)
            
            seeking_alpha_comments = self._fetch_seeking_alpha_comments(symbol, earnings_date)
            comments.extend(seeking_alpha_comments)
            
            marketwatch_comments = self._fetch_marketwatch_comments(symbol, earnings_date)
            comments.extend(marketwatch_comments)
            
        except Exception as e:
            logger.error(f"获取 {symbol} 分析师评论失败: {str(e)}")
            
        # 去重并按日期排序
        comments = self._deduplicate_comments(comments)
        comments.sort(key=lambda x: x.publish_date, reverse=True)
        
        # 缓存结果
        self.analyst_comments[cache_key] = comments
        
        return comments
    
    def _fetch_yahoo_analyst_comments(self, symbol: str, earnings_date: str) -> List[AnalystComment]:
        """从Yahoo Finance获取分析师评论"""
        comments = []
        
        try:
            url = f"https://finance.yahoo.com/quote/{symbol}/analysis"
            response = self._make_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找分析师评级和评论区域
                recommendation_elements = soup.find_all('div', class_='recommendation')
                for element in recommendation_elements:
                    try:
                        analyst_name = element.find('span', class_='analyst-name')
                        rating = element.find('span', class_='rating')
                        price_target = element.find('span', class_='price-target')
                        comment_text = element.find('div', class_='comment')
                        
                        if analyst_name and rating:
                            comment = AnalystComment(
                                analyst_name=analyst_name.get_text(strip=True),
                                firm='Yahoo Finance',
                                rating=rating.get_text(strip=True),
                                price_target=self._parse_float(price_target.get_text(strip=True) if price_target else None),
                                comment=comment_text.get_text(strip=True) if comment_text else '',
                                publish_date=datetime.now().strftime('%Y-%m-%d'),
                                source='Yahoo Finance'
                            )
                            comments.append(comment)
                            
                    except Exception as e:
                        logger.debug(f"解析Yahoo分析师评论失败: {str(e)}")
                        continue
                        
        except Exception as e:
            logger.warning(f"从Yahoo获取 {symbol} 分析师评论失败: {str(e)}")
            
        return comments
    
    def _fetch_seeking_alpha_comments(self, symbol: str, earnings_date: str) -> List[AnalystComment]:
        """从Seeking Alpha获取分析师评论"""
        comments = []
        
        try:
            url = f"https://seekingalpha.com/symbol/{symbol}/analysis"
            response = self._make_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找分析师文章和评论
                articles = soup.find_all('article', class_='analysis-article')
                for article in articles[:5]:  # 限制数量
                    try:
                        title = article.find('h3')
                        author = article.find('span', class_='author-name')
                        summary = article.find('p', class_='summary')
                        date_elem = article.find('time')
                        
                        if title and author:
                            comment = AnalystComment(
                                analyst_name=author.get_text(strip=True),
                                firm='Seeking Alpha',
                                rating='Analysis',
                                price_target=None,
                                comment=f"{title.get_text(strip=True)} - {summary.get_text(strip=True) if summary else ''}",
                                publish_date=date_elem.get('datetime', datetime.now().strftime('%Y-%m-%d')) if date_elem else datetime.now().strftime('%Y-%m-%d'),
                                source='Seeking Alpha'
                            )
                            comments.append(comment)
                            
                    except Exception as e:
                        logger.debug(f"解析Seeking Alpha评论失败: {str(e)}")
                        continue
                        
        except Exception as e:
            logger.warning(f"从Seeking Alpha获取 {symbol} 评论失败: {str(e)}")
            
        return comments
    
    def _fetch_marketwatch_comments(self, symbol: str, earnings_date: str) -> List[AnalystComment]:
        """从MarketWatch获取分析师评论"""
        comments = []
        
        try:
            url = f"https://www.marketwatch.com/investing/stock/{symbol}/analystestimates"
            response = self._make_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找分析师预测表格
                tables = soup.find_all('table', class_='table--analyst')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows[1:5]:  # 限制数量
                        cols = row.find_all('td')
                        if len(cols) >= 4:
                            try:
                                analyst_firm = cols[0].get_text(strip=True)
                                rating = cols[1].get_text(strip=True)
                                price_target = self._parse_float(cols[2].get_text(strip=True))
                                last_updated = cols[3].get_text(strip=True)
                                
                                comment = AnalystComment(
                                    analyst_name=analyst_firm.split(' - ')[0] if ' - ' in analyst_firm else analyst_firm,
                                    firm=analyst_firm.split(' - ')[1] if ' - ' in analyst_firm else 'MarketWatch',
                                    rating=rating,
                                    price_target=price_target,
                                    comment=f"Price target: ${price_target}" if price_target else '',
                                    publish_date=self._parse_date(last_updated) or datetime.now().strftime('%Y-%m-%d'),
                                    source='MarketWatch'
                                )
                                comments.append(comment)
                                
                            except Exception as e:
                                logger.debug(f"解析MarketWatch评论失败: {str(e)}")
                                continue
                                
        except Exception as e:
            logger.warning(f"从MarketWatch获取 {symbol} 评论失败: {str(e)}")
            
        return comments
    
    def generate_calendar_html(self, events: List[EarningsEvent], year: int, month: int) -> str:
        """生成HTML日历界面"""
        
        # 创建日历
        cal = calendar.Calendar(firstweekday=6)  # 周日开始
        month_days = cal.monthdayscalendar(year, month)
        
        # 按日期组织事件
        events_by_date = {}
        for event in events:
            event_date = datetime.strptime(event.earnings_date, '%Y-%m-%d').date()
            if event_date.year == year and event_date.month == month:
                date_key = event_date.day
                if date_key not in events_by_date:
                    events_by_date[date_key] = []
                events_by_date[date_key].append(event)
        
        # 生成HTML
        html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>财报日历 - {year}年{month}月</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .calendar-container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .calendar-header {{ text-align: center; margin-bottom: 30px; }}
                .calendar-title {{ font-size: 2em; color: #333; margin-bottom: 10px; }}
                .calendar-nav {{ margin: 20px 0; }}
                .nav-btn {{ padding: 10px 20px; margin: 0 5px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }}
                .nav-btn:hover {{ background: #0056b3; }}
                .calendar-table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
                .calendar-table th, .calendar-table td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; height: 120px; }}
                .calendar-table th {{ background: #f8f9fa; text-align: center; font-weight: bold; height: 40px; }}
                .day-number {{ font-weight: bold; font-size: 1.1em; margin-bottom: 5px; }}
                .earnings-event {{ 
                    background: linear-gradient(135deg, #4CAF50, #45a049); 
                    color: white; 
                    padding: 2px 4px; 
                    margin: 1px 0; 
                    border-radius: 3px; 
                    font-size: 0.8em; 
                    cursor: pointer;
                    transition: transform 0.2s;
                }}
                .earnings-event:hover {{ transform: scale(1.05); background: linear-gradient(135deg, #45a049, #4CAF50); }}
                .today {{ background: #e3f2fd; }}
                .other-month {{ color: #ccc; background: #f8f8f8; }}
                .modal {{ 
                    display: none; 
                    position: fixed; 
                    z-index: 1000; 
                    left: 0; 
                    top: 0; 
                    width: 100%; 
                    height: 100%; 
                    background: rgba(0,0,0,0.5); 
                }}
                .modal-content {{ 
                    background: white; 
                    margin: 5% auto; 
                    padding: 20px; 
                    border-radius: 8px; 
                    width: 80%; 
                    max-width: 800px; 
                    max-height: 80vh; 
                    overflow-y: auto; 
                }}
                .close {{ 
                    color: #aaa; 
                    float: right; 
                    font-size: 28px; 
                    font-weight: bold; 
                    cursor: pointer; 
                }}
                .close:hover {{ color: black; }}
                .event-details {{ margin: 20px 0; }}
                .analyst-comments {{ margin-top: 30px; }}
                .comment-item {{ 
                    border: 1px solid #eee; 
                    padding: 15px; 
                    margin: 10px 0; 
                    border-radius: 5px; 
                    background: #f9f9f9; 
                }}
                .comment-header {{ font-weight: bold; color: #333; margin-bottom: 8px; }}
                .comment-meta {{ color: #666; font-size: 0.9em; margin-bottom: 8px; }}
                .loading {{ text-align: center; padding: 20px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="calendar-container">
                <div class="calendar-header">
                    <h1 class="calendar-title">财报日历</h1>
                    <div class="calendar-nav">
                        <button class="nav-btn" onclick="changeMonth(-1)">← 上月</button>
                        <span style="margin: 0 20px; font-size: 1.2em; font-weight: bold;">{year}年{month}月</span>
                        <button class="nav-btn" onclick="changeMonth(1)">下月 →</button>
                    </div>
                </div>
                
                <table class="calendar-table">
                    <tr>
                        <th>周日</th><th>周一</th><th>周二</th><th>周三</th><th>周四</th><th>周五</th><th>周六</th>
                    </tr>
        """
        
        today = date.today()
        
        for week in month_days:
            html += "<tr>"
            for day in week:
                if day == 0:
                    html += '<td class="other-month"></td>'
                else:
                    day_class = "today" if date(year, month, day) == today else ""
                    html += f'<td class="{day_class}">'
                    html += f'<div class="day-number">{day}</div>'
                    
                    # 添加当天的财报事件
                    if day in events_by_date:
                        for event in events_by_date[day]:
                            html += f'<div class="earnings-event" onclick="showEventDetails(\'{event.symbol}\', \'{event.earnings_date}\')">'
                            html += f'{event.symbol}'
                            if event.estimated_eps:
                                html += f' (预期EPS: ${event.estimated_eps:.2f})'
                            html += '</div>'
                    
                    html += '</td>'
            html += "</tr>"
        
        html += """
                </table>
            </div>
            
            <!-- 模态框 -->
            <div id="eventModal" class="modal">
                <div class="modal-content">
                    <span class="close" onclick="closeModal()">&times;</span>
                    <div id="modalContent">
                        <div class="loading">加载中...</div>
                    </div>
                </div>
            </div>
            
            <script>
                let currentYear = """ + str(year) + """;
                let currentMonth = """ + str(month) + """;
                
                function changeMonth(delta) {
                    currentMonth += delta;
                    if (currentMonth > 12) {
                        currentMonth = 1;
                        currentYear++;
                    } else if (currentMonth < 1) {
                        currentMonth = 12;
                        currentYear--;
                    }
                    
                    // 重新加载页面
                    window.location.href = `?year=${currentYear}&month=${currentMonth}`;
                }
                
                function showEventDetails(symbol, date) {
                    const modal = document.getElementById('eventModal');
                    const content = document.getElementById('modalContent');
                    
                    modal.style.display = 'block';
                    content.innerHTML = '<div class="loading">正在加载财报详情和分析师评论...</div>';
                    
                    // 模拟加载财报详情（实际应该调用后端API）
                    fetch(`/api/earnings_details?symbol=${symbol}&date=${date}`)
                        .then(response => response.json())
                        .then(data => {
                            displayEventDetails(data);
                        })
                        .catch(error => {
                            content.innerHTML = '<p>加载失败，请稍后重试。</p>';
                        });
                }
                
                function displayEventDetails(data) {
                    const content = document.getElementById('modalContent');
                    let html = `
                        <h2>${data.symbol} - ${data.company_name}</h2>
                        <div class="event-details">
                            <p><strong>财报日期:</strong> ${data.earnings_date}</p>
                            <p><strong>季度:</strong> ${data.quarter}</p>
                            <p><strong>财政年度:</strong> ${data.fiscal_year}</p>
                    `;
                    
                    if (data.estimated_eps) {
                        html += `<p><strong>预期EPS:</strong> $${data.estimated_eps.toFixed(2)}</p>`;
                    }
                    if (data.actual_eps) {
                        html += `<p><strong>实际EPS:</strong> $${data.actual_eps.toFixed(2)}</p>`;
                    }
                    if (data.estimated_revenue) {
                        html += `<p><strong>预期营收:</strong> $${(data.estimated_revenue/1000000).toFixed(0)}M</p>`;
                    }
                    if (data.actual_revenue) {
                        html += `<p><strong>实际营收:</strong> $${(data.actual_revenue/1000000).toFixed(0)}M</p>`;
                    }
                    
                    html += '</div>';
                    
                    // 添加分析师评论
                    if (data.analyst_comments && data.analyst_comments.length > 0) {
                        html += '<div class="analyst-comments"><h3>分析师评论</h3>';
                        data.analyst_comments.forEach(comment => {
                            html += `
                                <div class="comment-item">
                                    <div class="comment-header">${comment.analyst_name} - ${comment.firm}</div>
                                    <div class="comment-meta">
                                        评级: ${comment.rating} | 
                                        ${comment.price_target ? '目标价: $' + comment.price_target.toFixed(2) + ' | ' : ''}
                                        日期: ${comment.publish_date} | 
                                        来源: ${comment.source}
                                    </div>
                                    <div class="comment-text">${comment.comment}</div>
                                </div>
                            `;
                        });
                        html += '</div>';
                    }
                    
                    content.innerHTML = html;
                }
                
                function closeModal() {
                    document.getElementById('eventModal').style.display = 'none';
                }
                
                // 点击模态框外部关闭
                window.onclick = function(event) {
                    const modal = document.getElementById('eventModal');
                    if (event.target == modal) {
                        modal.style.display = 'none';
                    }
                }
            </script>
        </body>
        </html>
        """
        
        return html
    
    # 工具方法
    def _parse_float(self, value) -> Optional[float]:
        """解析浮点数"""
        if not value or value in ['N/A', '-', '']:
            return None
        try:
            # 移除货币符号和逗号
            clean_value = str(value).replace('$', '').replace(',', '').replace('%', '').strip()
            return float(clean_value)
        except (ValueError, AttributeError):
            return None
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """解析日期字符串，返回YYYY-MM-DD格式"""
        if not date_str:
            return None
            
        try:
            # 尝试多种日期格式
            date_formats = [
                '%Y-%m-%d',
                '%m/%d/%Y', 
                '%m-%d-%Y',
                '%b %d, %Y',
                '%B %d, %Y',
                '%d %b %Y',
                '%d %B %Y'
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str.strip(), fmt)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
                    
        except Exception:
            pass
            
        return None
    
    def _get_quarter_from_date(self, date_str: str) -> str:
        """根据日期推算季度"""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            month = date_obj.month
            year = date_obj.year
            
            if month in [1, 2, 3]:
                return f"Q1 {year}"
            elif month in [4, 5, 6]:
                return f"Q2 {year}"
            elif month in [7, 8, 9]:
                return f"Q3 {year}"
            else:
                return f"Q4 {year}"
        except:
            return ""
    
    def _calculate_beat_estimate(self, actual: Optional[float], estimate: Optional[float]) -> Optional[bool]:
        """计算是否超出预期"""
        if actual is None or estimate is None:
            return None
        return actual > estimate
    
    def _deduplicate_events(self, events: List[EarningsEvent]) -> List[EarningsEvent]:
        """去除重复的财报事件"""
        seen = set()
        unique_events = []
        
        for event in events:
            key = (event.symbol, event.earnings_date)
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
                
        return unique_events
    
    def _deduplicate_comments(self, comments: List[AnalystComment]) -> List[AnalystComment]:
        """去除重复的分析师评论"""
        seen = set()
        unique_comments = []
        
        for comment in comments:
            key = (comment.analyst_name, comment.firm, comment.comment[:50])  # 用前50字符作为去重key
            if key not in seen:
                seen.add(key)
                unique_comments.append(comment)
                
        return unique_comments
    
    def save_calendar_data(self, events: List[EarningsEvent], filename: str):
        """保存日历数据到文件"""
        data = [asdict(event) for event in events]
        
        filepath = f"data/calendar/{filename}"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"日历数据已保存到: {filepath}")
    
    def load_calendar_data(self, filename: str) -> List[EarningsEvent]:
        """从文件加载日历数据"""
        filepath = f"data/calendar/{filename}"
        
        if not os.path.exists(filepath):
            return []
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            events = []
            for item in data:
                event = EarningsEvent(**item)
                events.append(event)
                
            return events
            
        except Exception as e:
            logger.error(f"加载日历数据失败: {str(e)}")
            return []

if __name__ == "__main__":
    # 测试代码
    calendar_tool = EarningsCalendar()
    
    # 获取一些测试股票的财报日期
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    print("正在获取财报日期数据...")
    events = calendar_tool.get_earnings_dates(test_symbols)
    
    print(f"获取到 {len(events)} 个财报事件")
    for event in events[:5]:  # 显示前5个
        print(f"  {event.symbol}: {event.earnings_date} - {event.quarter}")
    
    if events:
        # 生成当前月份的日历
        now = datetime.now()
        html = calendar_tool.generate_calendar_html(events, now.year, now.month)
        
        # 保存HTML文件
        with open('earnings_calendar.html', 'w', encoding='utf-8') as f:
            f.write(html)
            
        print("财报日历HTML已生成: earnings_calendar.html")
        
        # 保存数据
        calendar_tool.save_calendar_data(events, 'earnings_events.json')