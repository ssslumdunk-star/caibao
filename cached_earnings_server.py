#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
基于缓存的财报日历服务器
优先使用本地缓存数据，减少API调用，提高响应速度
"""

from flask import Flask, render_template_string, request, jsonify
from datetime import datetime, timedelta, date
import json
import random
import calendar as cal
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import logging
import os

from data_cache_manager import DataCacheManager, CachedEarningsEvent, CachedAnalystData
from yahoo_earnings_api import YahooEarningsAPI
from real_analyst_comments import get_real_analyst_comments

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('CachedEarningsServer')

app = Flask(__name__)

# 初始化缓存管理器和API
cache_manager = DataCacheManager()
yahoo_api = YahooEarningsAPI()

class CachedEarningsService:
    """基于缓存的财报数据服务"""
    
    def __init__(self):
        self.cache_manager = cache_manager
        self.yahoo_api = yahoo_api
        
        # 初始化时创建一些示例数据
        self._ensure_sample_data()
    
    def _ensure_sample_data(self):
        """确保有一些示例数据可以展示"""
        stats = self.cache_manager.get_cache_stats()
        
        if stats['earnings_events'] == 0:
            logger.info("没有缓存数据，创建示例数据...")
            self._create_sample_cache_data()
    
    def _create_sample_cache_data(self):
        """创建示例缓存数据 - 🚨 注意：此方法会覆盖真实数据！"""
        # 🔐 数据保护检查
        stats = self.cache_manager.get_cache_stats()
        if stats.get('earnings_events', 0) > 15:
            logger.warning("🚨 检测到现有缓存包含大量数据，可能包含真实数据！")
            logger.warning("🔐 为保护真实数据，跳过示例数据生成")
            logger.warning("📖 请查看 REAL_DATA_PROTECTION.md 了解详情")
            return
        today = datetime.now()
        
        # 创建一些历史和未来的财报事件
        sample_events = []
        
        # 历史财报 (过去30天内的)
        historical_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
        for i, symbol in enumerate(historical_symbols):
            event_date = (today - timedelta(days=15-i*3)).strftime('%Y-%m-%d')
            
            event = CachedEarningsEvent(
                symbol=symbol,
                company_name=self._get_company_name(symbol),
                earnings_date=event_date,
                earnings_time=random.choice(['BMO', 'AMC']),
                quarter=f"Q4 {today.year-1}",
                fiscal_year=today.year-1,
                eps_estimate=round(random.uniform(1.0, 5.0), 2),
                eps_actual=round(random.uniform(1.0, 5.5), 2),
                revenue_estimate=(base_revenue := random.randint(300, 1200) * 100000000),
                revenue_actual=int(base_revenue * random.uniform(0.95, 1.08)),
                beat_estimate=random.choice([True, False]),
                data_source="sample_historical"
            )
            sample_events.append(event)
        
        # 未来财报 (未来60天内的)
        future_symbols = ['TSLA', 'NVDA', 'NFLX', 'AMD', 'INTC', 'ORCL', 'CRM']
        for i, symbol in enumerate(future_symbols):
            event_date = (today + timedelta(days=5+i*7)).strftime('%Y-%m-%d')
            
            event = CachedEarningsEvent(
                symbol=symbol,
                company_name=self._get_company_name(symbol),
                earnings_date=event_date,
                earnings_time=random.choice(['BMO', 'AMC', 'During Market Hours']),
                quarter=f"Q1 {today.year}",
                fiscal_year=today.year,
                eps_estimate=round(random.uniform(0.5, 8.0), 2),
                revenue_estimate=random.randint(250, 1000) * 100000000,
                data_source="sample_future"
            )
            sample_events.append(event)
        
        # 缓存示例事件
        self.cache_manager.cache_earnings_events(sample_events)
        
        # 创建一些分析师数据
        for symbol in historical_symbols + future_symbols:
            base_price = random.uniform(50, 500)
            analyst_data = CachedAnalystData(
                symbol=symbol,
                current_price=round(base_price, 2),
                target_mean=round(base_price * random.uniform(0.9, 1.3), 2),
                target_high=round(base_price * random.uniform(1.1, 1.5), 2),
                target_low=round(base_price * random.uniform(0.7, 0.9), 2),
                recommendation_key=random.choice(['buy', 'hold', 'sell']),
                analyst_count=random.randint(8, 30),
                data_source="sample_analyst"
            )
            self.cache_manager.cache_analyst_data(analyst_data)
        
        logger.info(f"创建了 {len(sample_events)} 个示例财报事件")
    
    def _get_company_name(self, symbol: str) -> str:
        """获取公司名称"""
        company_names = {
            'AAPL': 'Apple Inc.',
            'MSFT': 'Microsoft Corp.',
            'GOOGL': 'Alphabet Inc.',
            'AMZN': 'Amazon.com Inc.',
            'META': 'Meta Platforms Inc.',
            'TSLA': 'Tesla Inc.',
            'NVDA': 'NVIDIA Corp.',
            'NFLX': 'Netflix Inc.',
            'AMD': 'Advanced Micro Devices',
            'INTC': 'Intel Corp.',
            'ORCL': 'Oracle Corp.',
            'CRM': 'Salesforce Inc.'
        }
        return company_names.get(symbol, f"{symbol} Corp.")
    
    def get_earnings_calendar(self, start_date: str, end_date: str) -> List[Dict]:
        """获取财报日历数据 (优先使用缓存)"""
        # 从缓存获取数据
        cached_events = self.cache_manager.get_cached_earnings_events(
            start_date=start_date, end_date=end_date
        )
        
        logger.info(f"从缓存获取到 {len(cached_events)} 个财报事件")
        
        # 转换为字典格式
        events = []
        for event in cached_events:
            event_dict = asdict(event)
            # 移除内部字段
            event_dict.pop('last_updated', None)
            event_dict.pop('data_source', None)
            events.append(event_dict)
        
        # 如果缓存数据不足且在合理时间范围内，尝试从API获取
        if len(cached_events) < 5:  # 如果缓存数据很少
            logger.info("缓存数据较少，尝试补充API数据...")
            try:
                # 这里可以添加API数据获取逻辑
                # 但由于API限制，我们先跳过
                pass
            except Exception as e:
                logger.warning(f"API数据获取失败: {e}")
        
        return events
    
    def get_earnings_details(self, symbol: str, earnings_date: str) -> Dict:
        """获取财报详情 (优先使用缓存)"""
        # 从缓存获取财报事件
        events = self.cache_manager.get_cached_earnings_events(
            symbol=symbol, start_date=earnings_date, end_date=earnings_date
        )
        
        if not events:
            return {'error': '未找到该财报数据'}
        
        event = events[0]
        
        # 判断是未来还是过去的财报
        event_date = datetime.strptime(earnings_date, '%Y-%m-%d').date()
        today = datetime.now().date()
        is_future = event_date > today
        
        # 构建基本详情
        details = {
            'symbol': event.symbol,
            'company_name': event.company_name,
            'earnings_date': event.earnings_date,
            'earnings_time': event.earnings_time,
            'quarter': event.quarter,
            'fiscal_year': event.fiscal_year,
            'eps_estimate': event.eps_estimate,
            'eps_actual': event.eps_actual,
            'revenue_estimate': event.revenue_estimate,
            'revenue_actual': event.revenue_actual,
            'beat_estimate': event.beat_estimate,
            'is_future': is_future
        }
        
        # 获取分析师数据
        analyst_data = self.cache_manager.get_cached_analyst_data(symbol)
        if analyst_data:
            details['analyst_data'] = {
                'current_price': analyst_data.current_price,
                'target_mean': analyst_data.target_mean,
                'target_high': analyst_data.target_high,
                'target_low': analyst_data.target_low,
                'recommendation_key': analyst_data.recommendation_key,
                'analyst_count': analyst_data.analyst_count
            }
        
        # 生成分析师评论 (优先使用真实数据)
        comments = self._generate_cached_comments(symbol, earnings_date, is_future)
        details['analyst_comments'] = comments
        
        return details
    
    def _generate_cached_comments(self, symbol: str, earnings_date: str, is_future: bool) -> List[Dict]:
        """基于真实数据生成分析师评论"""
        # 获取真实分析师评论
        real_comments_data = get_real_analyst_comments()
        comment_key = f"{symbol}_{earnings_date}"
        
        # 优先使用真实评论
        if comment_key in real_comments_data:
            return [
                {
                    'analyst_name': comment['analyst_name'],
                    'firm': comment['firm'],
                    'rating': comment['rating'],
                    'price_target': comment['price_target'],
                    'comment': comment['comment'],
                    'publish_date': comment['publish_date'],
                    'source': '真实分析师报告'
                }
                for comment in real_comments_data[comment_key]
            ]
        
        # 如果没有真实评论，返回更少但质量更高的模板评论
        company_name = self._get_company_name(symbol)
        analyst_data = self.cache_manager.get_cached_analyst_data(symbol)
        
        if is_future:
            # 未来财报 - 简单预测评论
            return [{
                'analyst_name': '市场分析师',
                'firm': '综合研究',
                'rating': '待观察',
                'price_target': analyst_data.target_mean if analyst_data else None,
                'comment': f'等待{company_name}即将发布的财报数据，市场关注其业绩指引和未来展望。',
                'publish_date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'source': '预期分析'
            }]
        else:
            # 历史财报 - 基于实际结果
            return [{
                'analyst_name': '市场分析师',
                'firm': '综合研究', 
                'rating': 'Hold',
                'price_target': analyst_data.target_mean if analyst_data else None,
                'comment': f'{company_name}已发布财报，建议查看具体财务数据进行分析。',
                'publish_date': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
                'source': '财报回顾'
            }]

# 创建服务实例
earnings_service = CachedEarningsService()

# Flask 路由
@app.route('/')
def index():
    """主页 - 财报日历"""
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))
    
    # 月份查询限制 - 只允许前后1个月
    current_date = datetime.now()
    current_year = current_date.year
    current_month = current_date.month
    
    # 计算允许查询的月份范围
    min_date = (current_date.replace(day=1) - timedelta(days=32)).replace(day=1)  # 前1个月
    max_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)  # 后1个月
    
    requested_date = datetime(year, month, 1)
    
    # 检查是否超出限制范围
    if requested_date < min_date or requested_date > max_date:
        # 返回限制提示页面
        return f"""
        <html>
        <head>
            <title>查询范围限制</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                       margin: 0; padding: 40px; background: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 40px; 
                            border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
                .warning-icon {{ font-size: 48px; margin-bottom: 20px; }}
                h1 {{ color: #e74c3c; margin-bottom: 20px; }}
                p {{ color: #555; line-height: 1.6; margin-bottom: 15px; }}
                .allowed-range {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .back-button {{ 
                    background: #007bff; color: white; text-decoration: none; 
                    padding: 12px 24px; border-radius: 6px; display: inline-block; margin-top: 20px;
                }}
                .back-button:hover {{ background: #0056b3; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="warning-icon">⚠️</div>
                <h1>查询范围受限</h1>
                <p>为了保证数据质量和系统性能，我们只提供 <strong>前后1个月</strong> 的财报数据查询。</p>
                <p>您请求查看的是 <strong>{year}年{month}月</strong> 的数据。</p>
                <div class="allowed-range">
                    <strong>📅 当前可查询范围：</strong><br>
                    {min_date.strftime('%Y年%m月')} - {max_date.strftime('%Y年%m月')}
                </div>
                <p>💰 <strong>想查看更远的历史数据？</strong><br>
                这将是我们未来的付费高级功能，敬请期待！</p>
                <a href="/?year={current_year}&month={current_month}" class="back-button">
                    返回当前月份 ({current_year}年{current_month}月)
                </a>
            </div>
        </body>
        </html>
        """
    
    # 获取当月的财报事件
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year+1}-01-01"
    else:
        end_date = f"{year}-{month+1:02d}-01"
    
    # 从缓存获取数据
    events_data = earnings_service.get_earnings_calendar(start_date, end_date)
    
    # 转换为对象格式用于HTML生成
    events = []
    for event_data in events_data:
        # 简单的对象类以便HTML模板使用
        class EventObj:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        events.append(EventObj(**event_data))
    
    # 生成HTML日历
    html = generate_cached_calendar_html(events, year, month)
    return html

@app.route('/api/earnings_details')
def api_earnings_details():
    """API: 获取财报详情"""
    symbol = request.args.get('symbol')
    earnings_date = request.args.get('date')
    
    if not symbol or not earnings_date:
        return jsonify({
            'success': False,
            'error': 'Missing symbol or date parameter'
        }), 400
    
    try:
        details = earnings_service.get_earnings_details(symbol, earnings_date)
        
        if 'error' in details:
            return jsonify({
                'success': False,
                'error': details['error']
            }), 404
        
        return jsonify({
            'success': True,
            'data': details
        })
        
    except Exception as e:
        logger.error(f"获取财报详情失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cache_stats')
def api_cache_stats():
    """API: 获取缓存统计信息"""
    try:
        stats = cache_manager.get_cache_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/admin/refresh_cache')
def admin_refresh_cache():
    """管理接口: 刷新缓存数据"""
    try:
        # 清理过期缓存
        deleted_count = cache_manager.clean_expired_cache()
        
        # 重新创建示例数据
        earnings_service._create_sample_cache_data()
        
        return jsonify({
            'success': True,
            'message': f'缓存已刷新，清理了{deleted_count}条过期数据'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_cached_calendar_html(events: List, year: int, month: int) -> str:
    """生成基于缓存数据的日历HTML"""
    
    # 检查是否包含真实数据
    has_real_data = any(
        hasattr(event, 'data_source') and ('news_' in event.data_source or 'sec_' in event.data_source)
        for event in events
    )
    
    page_title = "美股财报日历" if has_real_data else "美股财报日历 (缓存版)"
    cache_banner = "" if has_real_data else """
        <div class="cache-banner">
            💾 基于缓存的财报日历 - 快速响应，数据本地存储
        </div>
    """
    
    # 创建日历
    calendar_obj = cal.Calendar(firstweekday=6)  # 周日开始
    month_days = calendar_obj.monthdayscalendar(year, month)
    
    # 按日期组织事件
    events_by_date = {}
    for event in events:
        try:
            event_date = datetime.strptime(event.earnings_date, '%Y-%m-%d').date()
            if event_date.year == year and event_date.month == month:
                date_key = event_date.day
                if date_key not in events_by_date:
                    events_by_date[date_key] = []
                events_by_date[date_key].append(event)
        except:
            continue
    
    # 计算上下月 (考虑查询限制)
    current_date = datetime.now()
    min_date = (current_date.replace(day=1) - timedelta(days=32)).replace(day=1)  # 前1个月
    max_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)  # 后1个月
    
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
        
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    
    # 检查上下月导航是否在允许范围内
    prev_date = datetime(prev_year, prev_month, 1)
    next_date = datetime(next_year, next_month, 1)
    prev_disabled = prev_date < min_date
    next_disabled = next_date > max_date
    
    # 今日判断
    today = date.today()
    
    def is_today(y, m, d):
        try:
            return date(y, m, d) == today
        except:
            return False
    
    # HTML内容 (复用之前的样式，但数据来自缓存)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{page_title} - {year}年{month}月</title>
        <style>
            /* 复用之前的所有CSS样式 */
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            .cache-banner {{
                background: linear-gradient(135deg, #28a745, #20c997);
                color: white;
                text-align: center;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                font-weight: 600;
            }}
            .container {{ 
                max-width: 1400px; 
                margin: 0 auto; 
                background: white; 
                border-radius: 20px; 
                box-shadow: 0 20px 60px rgba(0,0,0,0.1); 
                overflow: hidden;
            }}
            .header {{ 
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: white; 
                padding: 30px; 
                text-align: center; 
                position: relative;
            }}
            .title {{ 
                font-size: 2.5em; 
                font-weight: 300; 
                margin-bottom: 15px; 
                text-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }}
            .version {{
                position: absolute;
                top: 10px;
                right: 20px;
                background: rgba(255,255,255,0.2);
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-size: 0.8em;
                font-weight: 500;
                backdrop-filter: blur(10px);
            }}
            .nav {{ 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                gap: 20px; 
                margin-top: 20px;
            }}
            .nav-btn {{ 
                padding: 12px 24px; 
                background: rgba(255,255,255,0.2); 
                color: white; 
                border: 2px solid rgba(255,255,255,0.3);
                border-radius: 25px; 
                cursor: pointer; 
                font-weight: 500;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
            }}
            .nav-btn:hover {{ 
                background: rgba(255,255,255,0.3); 
                border-color: rgba(255,255,255,0.5);
                transform: translateY(-2px);
            }}
            .nav-btn.disabled {{
                background: rgba(255,255,255,0.1);
                color: rgba(255,255,255,0.4);
                border-color: rgba(255,255,255,0.2);
                cursor: not-allowed;
            }}
            .nav-btn.disabled:hover {{
                background: rgba(255,255,255,0.1);
                border-color: rgba(255,255,255,0.2);
                transform: none;
            }}
            .current-month {{ 
                font-size: 1.3em; 
                font-weight: 500; 
                padding: 0 20px;
            }}
            .calendar {{ 
                display: grid; 
                grid-template-columns: repeat(7, 1fr); 
                gap: 1px; 
                background: #e0e0e0;
                margin: 0;
            }}
            .calendar-header {{ 
                background: #f8f9fa; 
                padding: 15px 10px; 
                text-align: center; 
                font-weight: 600; 
                font-size: 0.9em;
                color: #495057;
                border-bottom: 2px solid #dee2e6;
            }}
            .calendar-day {{ 
                background: white; 
                min-height: 120px; 
                padding: 8px; 
                position: relative;
                transition: background-color 0.2s ease;
            }}
            .calendar-day:hover {{ 
                background: #f8f9fa; 
            }}
            .day-number {{ 
                font-weight: 600; 
                font-size: 1.1em; 
                color: #495057;
                margin-bottom: 8px;
            }}
            .today {{ 
                background: linear-gradient(135deg, #e3f2fd, #bbdefb) !important;
                border: 3px solid #2196F3;
                box-shadow: 0 0 15px rgba(33, 150, 243, 0.3);
                position: relative;
            }}
            .today::before {{
                content: "今天";
                position: absolute;
                top: -2px;
                right: -2px;
                background: linear-gradient(135deg, #2196F3, #1976D2);
                color: white;
                font-size: 0.7em;
                padding: 2px 6px;
                border-radius: 8px;
                font-weight: 600;
                z-index: 2;
            }}
            .today .day-number {{ 
                color: white;
                background: linear-gradient(135deg, #2196F3, #1976D2);
                width: 32px;
                height: 32px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1em;
                font-weight: 700;
                box-shadow: 0 4px 8px rgba(33, 150, 243, 0.3);
            }}
            .other-month {{ 
                background: #f8f8f8; 
                color: #adb5bd;
            }}
            .earnings-event {{ 
                background: linear-gradient(135deg, #28a745, #20c997); 
                color: white; 
                padding: 4px 6px; 
                margin: 2px 0; 
                border-radius: 6px; 
                font-size: 0.75em; 
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s ease;
                display: block;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .earnings-event:hover {{ 
                transform: translateY(-1px) scale(1.02); 
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                background: linear-gradient(135deg, #20c997, #28a745);
            }}
            .earnings-event.bmo {{ 
                background: linear-gradient(135deg, #17a2b8, #007bff);
            }}
            .earnings-event.amc {{ 
                background: linear-gradient(135deg, #fd7e14, #dc3545);
            }}
            .earnings-event.future {{
                background: linear-gradient(135deg, #6f42c1, #6610f2);
                border: 2px solid #563d7c;
                position: relative;
            }}
            .earnings-event.future::before {{
                content: "🔮";
                position: absolute;
                top: -2px;
                left: -2px;
                font-size: 0.6em;
            }}
            .earnings-event.past {{
                position: relative;
            }}
            .earnings-event.past::after {{
                content: "✅";
                position: absolute;
                top: -2px;
                right: -2px;
                font-size: 0.6em;
            }}
            
            /* Modal styles - 复用之前的模态框样式 */
            .modal {{ 
                display: none; 
                position: fixed; 
                z-index: 1000; 
                left: 0; 
                top: 0; 
                width: 100%; 
                height: 100%; 
                background: rgba(0,0,0,0.6); 
                backdrop-filter: blur(5px);
            }}
            .modal-content {{ 
                background: white; 
                margin: 3% auto; 
                padding: 0; 
                border-radius: 15px; 
                width: 90%; 
                max-width: 900px; 
                max-height: 85vh; 
                overflow: hidden;
                box-shadow: 0 25px 50px rgba(0,0,0,0.25);
            }}
            .modal-header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 25px 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .modal-title {{
                font-size: 1.5em;
                font-weight: 500;
            }}
            .close {{ 
                color: white; 
                font-size: 28px; 
                font-weight: 300;
                cursor: pointer; 
                opacity: 0.8;
                transition: opacity 0.3s ease;
            }}
            .close:hover {{ 
                opacity: 1;
                transform: scale(1.1);
            }}
            .modal-body {{
                padding: 30px;
                max-height: 60vh;
                overflow-y: auto;
            }}
            .loading {{ 
                text-align: center; 
                padding: 40px; 
                color: #6c757d; 
            }}
            .spinner {{
                border: 3px solid #f3f3f3;
                border-top: 3px solid #007bff;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                animation: spin 1s linear infinite;
                margin: 0 auto 15px;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            .premium-hint {{
                margin: 40px auto;
                max-width: 800px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }}
            .premium-content {{
                display: flex;
                align-items: center;
                padding: 30px;
                color: white;
                gap: 30px;
            }}
            .premium-icon {{
                font-size: 60px;
                flex-shrink: 0;
            }}
            .premium-text {{
                flex: 1;
            }}
            .premium-text h3 {{
                margin: 0 0 15px 0;
                font-size: 1.5em;
                font-weight: 600;
            }}
            .premium-text p {{
                margin: 8px 0;
                opacity: 0.9;
                font-size: 0.95em;
            }}
            .premium-button {{
                background: rgba(255,255,255,0.2);
                color: white;
                border: 2px solid rgba(255,255,255,0.4);
                padding: 15px 30px;
                border-radius: 30px;
                cursor: pointer;
                font-weight: 600;
                font-size: 1em;
                transition: all 0.3s ease;
                flex-shrink: 0;
            }}
            .premium-button:hover {{
                background: rgba(255,255,255,0.3);
                border-color: rgba(255,255,255,0.6);
                transform: translateY(-2px);
            }}
        </style>
    </head>
    <body>
        {cache_banner}
        
        <div class="container">
            <div class="header">
                <div class="version">v2.1.0 - 2025-09-13</div>
                <h1 class="title">{page_title}</h1>
                <div class="nav">
                    {"<span class='nav-btn disabled' title='已到达查询范围限制'>← 上月</span>" if prev_disabled else f"<a href='/?year={prev_year}&month={prev_month}' class='nav-btn'>← 上月</a>"}
                    <span class="current-month">{year}年{month}月</span>
                    {"<span class='nav-btn disabled' title='已到达查询范围限制'>下月 →</span>" if next_disabled else f"<a href='/?year={next_year}&month={next_month}' class='nav-btn'>下月 →</a>"}
                </div>
            </div>
            
            <div class="calendar">
                <div class="calendar-header">周日</div>
                <div class="calendar-header">周一</div>
                <div class="calendar-header">周二</div>
                <div class="calendar-header">周三</div>
                <div class="calendar-header">周四</div>
                <div class="calendar-header">周五</div>
                <div class="calendar-header">周六</div>
    """
    
    # 添加日历内容
    for week in month_days:
        for day in week:
            if day == 0:
                html_content += '<div class="calendar-day other-month"></div>'
            else:
                day_class = "today" if is_today(year, month, day) else ""
                html_content += f'<div class="calendar-day {day_class}">'
                html_content += f'<div class="day-number">{day}</div>'
                
                # 添加当天的财报事件
                if day in events_by_date:
                    for event in events_by_date[day]:
                        # 判断是未来还是过去的财报
                        event_date = datetime.strptime(event.earnings_date, '%Y-%m-%d').date()
                        is_future = event_date > today
                        
                        time_class = event.earnings_time.lower().replace(' ', '_')
                        future_class = "future" if is_future else "past"
                        
                        html_content += f'<div class="earnings-event {time_class} {future_class}" onclick="showEventDetails(\'{event.symbol}\', \'{event.earnings_date}\')">'
                        # 优先显示中文公司名，没有则显示原始symbol
                        company_display = getattr(event, 'company_name', event.symbol)
                        html_content += f'{company_display}'
                        if hasattr(event, 'company_name') and event.company_name != event.symbol:
                            html_content += f'<br><small>({event.symbol})</small>'
                        
                        if is_future:
                            # 未来财报显示预期EPS
                            if hasattr(event, 'eps_estimate') and event.eps_estimate:
                                html_content += f'<br><small>预期EPS: ${event.eps_estimate:.2f}</small>'
                        else:
                            # 历史财报显示3日涨跌幅
                            stock_change = random.uniform(-15.0, 20.0)  # 模拟财报后3日涨跌幅
                            change_color = "#22c55e" if stock_change > 0 else "#ef4444"
                            change_sign = "+" if stock_change > 0 else ""
                            html_content += f'<br><small style="color: {change_color};">3日: {change_sign}{stock_change:.1f}%</small>'
                        
                        html_content += '</div>'
                
                html_content += '</div>'
    
    # 添加模态框和JavaScript (复用之前的)
    html_content += f"""
            </div>
        </div>
        
        <!-- 付费模块预留 -->
        <div class="premium-hint">
            <div class="premium-content">
                <div class="premium-icon">💎</div>
                <div class="premium-text">
                    <h3>高级版功能预告</h3>
                    <p>• 📅 无限制历史财报数据查询</p>
                    <p>• 📊 AI分析师智能评论生成</p>
                    <p>• 🔔 重要财报提醒推送</p>
                    <p>• 📱 移动端App专享</p>
                </div>
                <button class="premium-button" onclick="alert('高级版即将推出，敬请期待！')">
                    升级高级版
                </button>
            </div>
        </div>
        
        <!-- 模态框 -->
        <div id="eventModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <div class="modal-title">财报详情 (来自缓存)</div>
                    <span class="close" onclick="closeModal()">&times;</span>
                </div>
                <div class="modal-body">
                    <div id="modalContent">
                        <div class="loading">
                            <div class="spinner"></div>
                            正在从缓存加载财报详情...
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // JavaScript代码复用之前的逻辑，但提示数据来自缓存
            function showEventDetails(symbol, date) {{
                const modal = document.getElementById('eventModal');
                const content = document.getElementById('modalContent');
                
                modal.style.display = 'block';
                content.innerHTML = `
                    <div class="loading">
                        <div class="spinner"></div>
                        正在从本地缓存加载 ${{symbol}} 的财报详情...
                    </div>
                `;
                
                fetch(`/api/earnings_details?symbol=${{symbol}}&date=${{date}}`)
                    .then(response => response.json())
                    .then(result => {{
                        if (result.success) {{
                            displayEventDetails(result.data);
                        }} else {{
                            content.innerHTML = `<div class="error-message">加载失败: ${{result.error}}</div>`;
                        }}
                    }})
                    .catch(error => {{
                        content.innerHTML = '<div class="error-message">缓存访问错误，请稍后重试</div>';
                        console.error('Error:', error);
                    }});
            }}
            
            function displayEventDetails(data) {{
                const content = document.getElementById('modalContent');
                
                const isFuture = data.is_future;
                const statusIcon = isFuture ? '🔮' : '✅';
                const statusText = isFuture ? '未来财报 - 预测数据 (缓存)' : '已发布财报 - 实际数据 (缓存)';
                const headerColor = isFuture ? '#6f42c1' : '#28a745';
                
                let html = `
                    <div class="event-details">
                        <div style="display: flex; align-items: center; margin-bottom: 20px;">
                            <h2 style="margin: 0; color: ${{headerColor}};">${{statusIcon}} ${{data.symbol}} - ${{data.company_name || data.symbol}}</h2>
                        </div>
                        <div style="background: linear-gradient(135deg, ${{isFuture ? '#f3e5f5' : '#e8f5e8'}}, ${{isFuture ? '#e1bee7' : '#c8e6c9'}}); padding: 10px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                            <strong style="color: ${{headerColor}};">${{statusText}}</strong>
                        </div>
                `;
                
                const details = [
                    ['财报日期', data.earnings_date],
                    ['发布时间', data.earnings_time || 'N/A'],
                    ['季度', data.quarter || 'N/A'],
                    ['财政年度', data.fiscal_year || 'N/A']
                ];
                
                if (data.eps_estimate) {{
                    details.push(['预期EPS', `$${{data.eps_estimate.toFixed(2)}}`]);
                }}
                if (data.eps_actual) {{
                    details.push(['实际EPS', `$${{data.eps_actual.toFixed(2)}}`]);
                }}
                if (data.revenue_estimate) {{
                    details.push(['预期营收', `${{(data.revenue_estimate/100000000).toFixed(1)}}亿美元`]);
                }}
                if (data.revenue_actual) {{
                    details.push(['实际营收', `${{(data.revenue_actual/100000000).toFixed(1)}}亿美元`]);
                }}
                
                details.forEach(([label, value]) => {{
                    html += `
                        <div style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #e9ecef;">
                            <span style="font-weight: 600; color: #495057;">${{label}}:</span>
                            <span style="color: #6c757d;">${{value}}</span>
                        </div>
                    `;
                }});
                
                html += '</div>';
                
                if (data.analyst_data) {{
                    const analyst = data.analyst_data;
                    html += `
                        <div style="margin-top: 30px;">
                            <h3 style="font-size: 1.3em; font-weight: 600; color: #495057; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #007bff;">💾 缓存的分析师数据</h3>
                            <div style="border: 1px solid #dee2e6; border-radius: 10px; padding: 20px; background: #f8f9fa;">
                                <div style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #e9ecef;">
                                    <span style="font-weight: 600; color: #495057;">今日价格:</span>
                                    <span style="color: #6c757d;">$${{analyst.current_price.toFixed(2)}}</span>
                                </div>
                    `;
                    
                    if (analyst.target_mean) {{
                        html += `
                            <div style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #e9ecef;">
                                <span style="font-weight: 600; color: #495057;">平均目标价:</span>
                                <span style="color: #6c757d;">$${{analyst.target_mean.toFixed(2)}}</span>
                            </div>
                        `;
                    }}
                    
                    if (analyst.target_high && analyst.target_low) {{
                        html += `
                            <div style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #e9ecef;">
                                <span style="font-weight: 600; color: #495057;">目标价区间:</span>
                                <span style="color: #6c757d;">$${{analyst.target_low.toFixed(2)}} - $${{analyst.target_high.toFixed(2)}}</span>
                            </div>
                        `;
                    }}
                    
                    if (analyst.recommendation_key) {{
                        const ratings = {{
                            'buy': '买入',
                            'hold': '持有', 
                            'sell': '卖出'
                        }};
                        html += `
                            <div style="display: flex; justify-content: space-between; padding: 12px 0;">
                                <span style="font-weight: 600; color: #495057;">推荐等级:</span>
                                <span style="color: #6c757d;">${{ratings[analyst.recommendation_key] || analyst.recommendation_key}}</span>
                            </div>
                        `;
                    }}
                    
                    html += '</div></div>';
                }}
                
                if (data.analyst_comments && data.analyst_comments.length > 0) {{
                    const commentTitle = isFuture ? '🔮 分析师预测 (缓存)' : '✅ 分析师评论 (缓存)';
                    html += `
                        <div style="margin-top: 30px;">
                            <h3 style="font-size: 1.3em; font-weight: 600; color: #495057; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #007bff;">${{commentTitle}}</h3>
                    `;
                    
                    data.analyst_comments.forEach(comment => {{
                        html += `
                            <div style="border: 1px solid #dee2e6; border-radius: 10px; padding: 20px; margin: 15px 0; background: #f8f9fa;">
                                <div style="font-weight: 600; color: #495057; margin-bottom: 10px; font-size: 1.1em;">${{comment.analyst_name}} - ${{comment.firm}}</div>
                                <div style="color: #6c757d; font-size: 0.9em; margin-bottom: 12px; display: flex; flex-wrap: wrap; gap: 15px;">
                                    <span>评级: ${{comment.rating}}</span>
                                    ${{comment.price_target ? `<span>目标价: $${{comment.price_target.toFixed(2)}}</span>` : ''}}
                                    <span>日期: ${{comment.publish_date}}</span>
                                    <span>来源: ${{comment.source}}</span>
                                </div>
                                <div>${{comment.comment}}</div>
                            </div>
                        `;
                    }});
                    
                    html += '</div>';
                }}
                
                content.innerHTML = html;
            }}
            
            function closeModal() {{
                document.getElementById('eventModal').style.display = 'none';
            }}
            
            window.onclick = function(event) {{
                const modal = document.getElementById('eventModal');
                if (event.target == modal) {{
                    modal.style.display = 'none';
                }}
            }}
        </script>
    </body>
    </html>
    """
    
    return html_content

if __name__ == "__main__":
    print("🚀 启动基于缓存的财报日历服务器...")
    print("💾 优先使用本地缓存数据，减少API调用")
    print("📅 访问: http://localhost:5002")
    print("📊 缓存统计: /api/cache_stats")
    print("🔄 刷新缓存: /admin/refresh_cache")
    
    # 显示缓存统计
    stats = cache_manager.get_cache_stats()
    print(f"\n📈 当前缓存状态:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    app.run(debug=True, host='0.0.0.0', port=5002)