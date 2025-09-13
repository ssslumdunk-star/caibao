#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财报日历演示服务器
使用模拟数据展示完整功能，避免API限制问题
"""

from flask import Flask, render_template_string, request, jsonify
from datetime import datetime, timedelta, date
import json
import random
import calendar as cal
from dataclasses import dataclass, asdict
from typing import List, Dict

@dataclass
class MockEarningsEvent:
    """模拟财报事件数据结构"""
    symbol: str
    company_name: str
    earnings_date: str
    earnings_time: str  # BMO (Before Market Open), AMC (After Market Close)
    quarter: str
    fiscal_year: int
    eps_estimate: float = None
    eps_actual: float = None
    revenue_estimate: float = None
    revenue_actual: float = None
    beat_estimate: bool = None

@dataclass
class MockAnalystComment:
    """模拟分析师评论数据结构"""
    analyst_name: str
    firm: str
    rating: str
    price_target: float = None
    comment: str = ""
    publish_date: str = ""
    source: str = ""

class MockEarningsData:
    """模拟财报数据生成器"""
    
    def __init__(self):
        # 热门股票及其公司名称
        self.companies = {
            'AAPL': ('Apple Inc.', 230.00),
            'MSFT': ('Microsoft Corp.', 415.00),
            'GOOGL': ('Alphabet Inc.', 165.00),
            'AMZN': ('Amazon.com Inc.', 180.00),
            'TSLA': ('Tesla Inc.', 250.00),
            'NVDA': ('NVIDIA Corp.', 450.00),
            'META': ('Meta Platforms Inc.', 510.00),
            'NFLX': ('Netflix Inc.', 485.00),
            'AMD': ('Advanced Micro Devices', 145.00),
            'INTC': ('Intel Corp.', 25.00),
            'ORCL': ('Oracle Corp.', 175.00),
            'CRM': ('Salesforce Inc.', 275.00),
            'UBER': ('Uber Technologies', 75.00),
            'LYFT': ('Lyft Inc.', 15.00),
            'ZM': ('Zoom Video Communications', 70.00)
        }
        
        self.analyst_firms = [
            'Goldman Sachs', 'Morgan Stanley', 'JPMorgan', 'Credit Suisse',
            'Barclays', 'Citigroup', 'Deutsche Bank', 'UBS', 'Bank of America',
            'Wells Fargo', 'Cowen', 'Wedbush', 'Piper Sandler', 'Evercore ISI'
        ]
        
    def generate_mock_earnings_calendar(self, start_date: str, end_date: str) -> List[MockEarningsEvent]:
        """生成模拟财报日历数据"""
        events = []
        
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        # 为每个公司生成财报事件
        symbols = list(self.companies.keys())
        random.shuffle(symbols)
        
        for i, symbol in enumerate(symbols[:12]):  # 限制数量
            company_name, current_price = self.companies[symbol]
            
            # 随机生成财报日期
            days_offset = random.randint(0, (end - start).days)
            earnings_date = (start + timedelta(days=days_offset)).strftime('%Y-%m-%d')
            
            # 随机选择发布时间
            earnings_time = random.choice(['BMO', 'AMC', 'During Market Hours'])
            
            # 计算季度
            date_obj = datetime.strptime(earnings_date, '%Y-%m-%d')
            quarter = f"Q{((date_obj.month - 1) // 3) + 1} {date_obj.year}"
            
            # 生成预期和实际EPS
            base_eps = current_price * 0.01  # 简单估算
            eps_estimate = round(base_eps + random.uniform(-0.5, 0.5), 2)
            
            # 部分事件有实际结果（过去的财报）
            eps_actual = None
            beat_estimate = None
            if random.random() > 0.6:  # 40%的事件有实际结果
                eps_actual = round(eps_estimate + random.uniform(-0.3, 0.4), 2)
                beat_estimate = eps_actual > eps_estimate
            
            # 生成营收数据
            revenue_estimate = random.randint(10000, 100000) * 1000000  # 百万美元
            revenue_actual = None
            if eps_actual:
                revenue_actual = int(revenue_estimate * random.uniform(0.9, 1.15))
            
            event = MockEarningsEvent(
                symbol=symbol,
                company_name=company_name,
                earnings_date=earnings_date,
                earnings_time=earnings_time,
                quarter=quarter,
                fiscal_year=date_obj.year,
                eps_estimate=eps_estimate,
                eps_actual=eps_actual,
                revenue_estimate=revenue_estimate,
                revenue_actual=revenue_actual,
                beat_estimate=beat_estimate
            )
            
            events.append(event)
        
        # 按日期排序
        events.sort(key=lambda x: x.earnings_date)
        return events
    
    def generate_mock_analyst_comments(self, symbol: str) -> List[MockAnalystComment]:
        """生成模拟分析师评论"""
        comments = []
        company_name, current_price = self.companies.get(symbol, (symbol, 100.00))
        
        # 生成3-5个分析师评论
        num_comments = random.randint(3, 5)
        
        for i in range(num_comments):
            firm = random.choice(self.analyst_firms)
            analyst_name = f"分析师{i+1}"
            
            # 随机生成评级
            rating = random.choice(['Strong Buy', 'Buy', 'Hold', 'Sell', 'Strong Sell'])
            
            # 生成目标价格
            price_target = round(current_price * random.uniform(0.8, 1.3), 2)
            
            # 生成评论内容
            comment_templates = [
                f"{company_name}的财报预期表现强劲，预计收入增长将超过市场预期。",
                f"由于市场竞争加剧，{company_name}面临一些挑战，但长期前景依然乐观。",
                f"{company_name}的创新能力和市场地位使其在当前环境下具有竞争优势。",
                f"考虑到宏观经济因素，{company_name}的业绩可能会受到一定影响。",
                f"{company_name}的财务状况稳健，预计将继续保持稳定增长。"
            ]
            
            comment_text = random.choice(comment_templates)
            
            # 随机生成发布日期（过去7天内）
            publish_date = (datetime.now() - timedelta(days=random.randint(1, 7))).strftime('%Y-%m-%d')
            
            comment = MockAnalystComment(
                analyst_name=analyst_name,
                firm=firm,
                rating=rating,
                price_target=price_target,
                comment=comment_text,
                publish_date=publish_date,
                source=firm
            )
            
            comments.append(comment)
        
        return comments
    
    def generate_mock_prediction_comments(self, symbol: str) -> List[MockAnalystComment]:
        """生成模拟的预测性评论（用于未来财报）"""
        comments = []
        company_name, current_price = self.companies.get(symbol, (symbol, 100.00))
        
        # 生成3-5个分析师预测
        num_comments = random.randint(3, 5)
        
        for i in range(num_comments):
            firm = random.choice(self.analyst_firms)
            analyst_name = f"分析师{i+1}"
            
            # 预测性评级
            rating = random.choice(['预期强劲', '谨慎乐观', '维持观望', '预期疲软'])
            
            # 生成目标价格
            price_target = round(current_price * random.uniform(0.9, 1.2), 2)
            
            # 生成预测性评论内容
            prediction_templates = [
                f"预计{company_name}本季度财报将超出市场预期，收入增长强劲。",
                f"基于行业趋势分析，{company_name}本季度业绩可能面临挑战。",
                f"预测{company_name}将在财报中公布积极的前景指引。",
                f"市场对{company_name}本季度EPS预期可能偏保守。",
                f"预计{company_name}将在财报中提及新的增长策略。",
                f"分析师普遍看好{company_name}长期发展前景。",
                f"预测{company_name}本季度营收将创历史新高。"
            ]
            
            comment_text = random.choice(prediction_templates)
            
            # 随机生成发布日期（过去3天内）
            publish_date = (datetime.now() - timedelta(days=random.randint(1, 3))).strftime('%Y-%m-%d')
            
            comment = MockAnalystComment(
                analyst_name=analyst_name,
                firm=firm,
                rating=rating,
                price_target=price_target,
                comment=comment_text,
                publish_date=publish_date,
                source=f"{firm} 预测报告"
            )
            
            comments.append(comment)
        
        return comments

# Flask应用
app = Flask(__name__)
mock_data = MockEarningsData()

@app.route('/')
def index():
    """主页 - 财报日历"""
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))
    
    # 获取当月的财报事件
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year+1}-01-01"
    else:
        end_date = f"{year}-{month+1:02d}-01"
    
    # 生成模拟数据
    events = mock_data.generate_mock_earnings_calendar(start_date, end_date)
    
    # 生成HTML日历
    html = generate_demo_calendar_html(events, year, month)
    return html

@app.route('/api/earnings_details')
def api_earnings_details():
    """API: 获取财报详情和分析师评论"""
    symbol = request.args.get('symbol')
    earnings_date = request.args.get('date')
    
    if not symbol or not earnings_date:
        return jsonify({
            'success': False,
            'error': 'Missing symbol or date parameter'
        }), 400
    
    try:
        # 生成模拟的财报详情
        company_name, current_price = mock_data.companies.get(symbol, (symbol, 100.00))
        
        # 判断是未来还是过去的财报
        date_obj = datetime.strptime(earnings_date, '%Y-%m-%d')
        today = datetime.now().date()
        earnings_date_obj = date_obj.date()
        is_future = earnings_date_obj > today
        
        quarter = f"Q{((date_obj.month - 1) // 3) + 1} {date_obj.year}"
        
        eps_estimate = round(current_price * 0.01 + random.uniform(-0.5, 0.5), 2)
        
        # 根据是否是未来财报决定数据
        if is_future:
            # 未来财报：只有预期数据，没有实际数据
            eps_actual = None
            revenue_actual = None
            beat_estimate = None
        else:
            # 过去财报：可能有实际数据
            eps_actual = round(eps_estimate + random.uniform(-0.3, 0.4), 2) if random.random() > 0.3 else None
            revenue_actual = random.randint(9000, 110000) * 1000000 if eps_actual else None
            beat_estimate = eps_actual > eps_estimate if eps_actual else None
        
        details = {
            'symbol': symbol,
            'company_name': company_name,
            'earnings_date': earnings_date,
            'earnings_time': random.choice(['BMO', 'AMC', 'During Market Hours']),
            'quarter': quarter,
            'fiscal_year': date_obj.year,
            'eps_estimate': eps_estimate,
            'eps_actual': eps_actual,
            'revenue_estimate': random.randint(10000, 100000) * 1000000,
            'revenue_actual': revenue_actual,
            'beat_estimate': beat_estimate,
            'is_future': is_future,
            'analyst_data': {
                'current_price': current_price,
                'target_mean': round(current_price * random.uniform(0.9, 1.2), 2),
                'target_high': round(current_price * random.uniform(1.1, 1.4), 2),
                'target_low': round(current_price * random.uniform(0.7, 0.9), 2),
                'recommendation_key': random.choice(['buy', 'hold', 'sell']),
                'analyst_count': random.randint(10, 25)
            }
        }
        
        # 根据是否是未来财报生成不同的分析师评论
        if is_future:
            # 未来财报：生成预测性评论
            comments = mock_data.generate_mock_prediction_comments(symbol)
        else:
            # 过去财报：生成分析评论
            comments = mock_data.generate_mock_analyst_comments(symbol)
        
        details['analyst_comments'] = [asdict(comment) for comment in comments]
        
        return jsonify({
            'success': True,
            'data': details
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_demo_calendar_html(events: List[MockEarningsEvent], year: int, month: int) -> str:
    """生成演示日历HTML"""
    
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
    
    # 计算上下月
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
        
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    
    # 今日判断
    today = date.today()
    
    def is_today(y, m, d):
        try:
            return date(y, m, d) == today
        except:
            return False
    
    # HTML模板
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>美股财报日历 - {year}年{month}月 (演示版)</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            .demo-banner {{
                background: linear-gradient(135deg, #ff6b6b, #ffd93d);
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
            }}
            .title {{ 
                font-size: 2.5em; 
                font-weight: 300; 
                margin-bottom: 15px; 
                text-shadow: 0 2px 4px rgba(0,0,0,0.2);
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
            
            /* 未来财报事件样式 */
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
            .earnings-event.future:hover {{
                background: linear-gradient(135deg, #6610f2, #6f42c1);
                transform: translateY(-2px) scale(1.05);
            }}
            
            /* 过去财报事件样式 */
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
            
            /* 时间分界线样式 */
            .time-divider {{
                position: relative;
            }}
            .time-divider::after {{
                content: "";
                position: absolute;
                left: 0;
                right: 0;
                bottom: 0;
                height: 4px;
                background: linear-gradient(90deg, transparent, #2196F3, transparent);
                border-radius: 2px;
            }}
            
            /* 模态框样式 */
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
            .event-details {{ 
                margin: 20px 0; 
            }}
            .detail-row {{
                display: flex;
                justify-content: space-between;
                padding: 12px 0;
                border-bottom: 1px solid #e9ecef;
            }}
            .detail-label {{
                font-weight: 600;
                color: #495057;
            }}
            .detail-value {{
                color: #6c757d;
            }}
            .analyst-section {{ 
                margin-top: 30px; 
            }}
            .section-title {{
                font-size: 1.3em;
                font-weight: 600;
                color: #495057;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #007bff;
            }}
            .analyst-card {{ 
                border: 1px solid #dee2e6; 
                border-radius: 10px; 
                padding: 20px; 
                margin: 15px 0; 
                background: #f8f9fa;
                transition: transform 0.2s ease;
            }}
            .analyst-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            .analyst-header {{ 
                font-weight: 600; 
                color: #495057; 
                margin-bottom: 10px; 
                font-size: 1.1em;
            }}
            .analyst-meta {{ 
                color: #6c757d; 
                font-size: 0.9em; 
                margin-bottom: 12px; 
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
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
            
            /* 响应式设计 */
            @media (max-width: 768px) {{
                .container {{ margin: 10px; border-radius: 10px; }}
                .header {{ padding: 20px; }}
                .title {{ font-size: 2em; }}
                .nav {{ flex-direction: column; gap: 10px; }}
                .calendar-day {{ min-height: 80px; padding: 5px; }}
                .earnings-event {{ font-size: 0.7em; padding: 2px 4px; }}
                .modal-content {{ width: 95%; margin: 5% auto; }}
                .modal-body {{ padding: 20px; }}
            }}
        </style>
    </head>
    <body>
        <div class="demo-banner">
            🎯 这是演示版本，使用模拟数据展示财报日历功能
        </div>
        
        <div class="container">
            <div class="header">
                <h1 class="title">美股财报日历</h1>
                <div class="nav">
                    <a href="/?year={prev_year}&month={prev_month}" class="nav-btn">← 上月</a>
                    <span class="current-month">{year}年{month}月</span>
                    <a href="/?year={next_year}&month={next_month}" class="nav-btn">下月 →</a>
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
                        html_content += f'{event.symbol}'
                        if event.eps_estimate:
                            html_content += f'<br><small>{"预期" if is_future else ""}EPS: ${event.eps_estimate:.2f}</small>'
                        html_content += '</div>'
                
                html_content += '</div>'
    
    # 添加模态框和JavaScript
    html_content += f"""
            </div>
        </div>
        
        <!-- 模态框 -->
        <div id="eventModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <div class="modal-title">财报详情</div>
                    <span class="close" onclick="closeModal()">&times;</span>
                </div>
                <div class="modal-body">
                    <div id="modalContent">
                        <div class="loading">
                            <div class="spinner"></div>
                            正在加载财报详情和分析师评论...
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            function showEventDetails(symbol, date) {{
                const modal = document.getElementById('eventModal');
                const content = document.getElementById('modalContent');
                
                modal.style.display = 'block';
                content.innerHTML = `
                    <div class="loading">
                        <div class="spinner"></div>
                        正在加载 ${{symbol}} 的财报详情和分析师评论...
                    </div>
                `;
                
                // 获取财报详情
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
                        content.innerHTML = '<div class="error-message">网络错误，请稍后重试</div>';
                        console.error('Error:', error);
                    }});
            }}
            
            function displayEventDetails(data) {{
                const content = document.getElementById('modalContent');
                
                // 判断是否为未来财报
                const isFuture = data.is_future;
                const statusIcon = isFuture ? '🔮' : '✅';
                const statusText = isFuture ? '未来财报 - 预测数据' : '已发布财报 - 实际数据';
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
                
                // 基本信息
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
                        <div class="detail-row">
                            <span class="detail-label">${{label}}:</span>
                            <span class="detail-value">${{value}}</span>
                        </div>
                    `;
                }});
                
                html += '</div>';
                
                // 分析师数据
                if (data.analyst_data) {{
                    const analyst = data.analyst_data;
                    html += `
                        <div class="analyst-section">
                            <h3 class="section-title">分析师数据</h3>
                            <div class="analyst-card">
                                <div class="detail-row">
                                    <span class="detail-label">当前价格:</span>
                                    <span class="detail-value">$${{analyst.current_price.toFixed(2)}}</span>
                                </div>
                    `;
                    
                    if (analyst.target_mean) {{
                        html += `
                            <div class="detail-row">
                                <span class="detail-label">平均目标价:</span>
                                <span class="detail-value">$${{analyst.target_mean.toFixed(2)}}</span>
                            </div>
                        `;
                    }}
                    
                    if (analyst.target_high && analyst.target_low) {{
                        html += `
                            <div class="detail-row">
                                <span class="detail-label">目标价区间:</span>
                                <span class="detail-value">$${{analyst.target_low.toFixed(2)}} - $${{analyst.target_high.toFixed(2)}}</span>
                            </div>
                        `;
                    }}
                    
                    if (analyst.recommendation_key) {{
                        const ratings = {{
                            'buy': '买入',
                            'hold': '持有', 
                            'sell': '卖出',
                            'strong_buy': '强烈买入',
                            'strong_sell': '强烈卖出'
                        }};
                        html += `
                            <div class="detail-row">
                                <span class="detail-label">推荐等级:</span>
                                <span class="detail-value">${{ratings[analyst.recommendation_key] || analyst.recommendation_key}}</span>
                            </div>
                        `;
                    }}
                    
                    html += '</div></div>';
                }}
                
                // 分析师评论
                if (data.analyst_comments && data.analyst_comments.length > 0) {{
                    const commentTitle = isFuture ? '🔮 分析师预测' : '✅ 分析师评论';
                    html += `
                        <div class="analyst-section">
                            <h3 class="section-title">${{commentTitle}}</h3>
                    `;
                    
                    data.analyst_comments.forEach(comment => {{
                        html += `
                            <div class="analyst-card">
                                <div class="analyst-header">${{comment.analyst_name}} - ${{comment.firm}}</div>
                                <div class="analyst-meta">
                                    <span>评级: ${{comment.rating}}</span>
                                    ${{comment.price_target ? `<span>目标价: $${{comment.price_target.toFixed(2)}}</span>` : ''}}
                                    <span>日期: ${{comment.publish_date}}</span>
                                    <span>来源: ${{comment.source}}</span>
                                </div>
                                <div class="comment-text">${{comment.comment}}</div>
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
            
            // 点击模态框外部关闭
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
    print("🚀 启动财报日历演示服务器...")
    print("📅 访问: http://localhost:5001")
    print("💡 这是演示版本，使用模拟数据展示所有功能")
    print("🔄 点击日历中的股票事件查看详细信息和分析师评论")
    
    app.run(debug=True, host='0.0.0.0', port=5001)