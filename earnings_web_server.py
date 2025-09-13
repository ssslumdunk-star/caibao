#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财报日历Web服务器
提供HTTP API和Web界面
"""

from flask import Flask, render_template_string, request, jsonify
from datetime import datetime, timedelta
import json
import os
import logging
from yahoo_earnings_api import YahooEarningsAPI, YahooEarningsEvent, YahooAnalystData
from dataclasses import asdict

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('EarningsWebServer')

app = Flask(__name__)
yahoo_api = YahooEarningsAPI()

# 缓存
earnings_cache = {}
analyst_cache = {}

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
    
    # 从缓存或API获取数据
    cache_key = f"{start_date}_{end_date}"
    if cache_key in earnings_cache:
        events = earnings_cache[cache_key]
    else:
        events = yahoo_api.get_earnings_calendar(start_date, end_date)
        earnings_cache[cache_key] = events
    
    # 生成HTML日历
    html = generate_calendar_html(events, year, month)
    return html

@app.route('/api/earnings_calendar')
def api_earnings_calendar():
    """API: 获取财报日历数据"""
    start_date = request.args.get('start_date', datetime.now().strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'))
    
    try:
        events = yahoo_api.get_earnings_calendar(start_date, end_date)
        events_data = [asdict(event) for event in events]
        
        return jsonify({
            'success': True,
            'data': events_data,
            'count': len(events_data)
        })
        
    except Exception as e:
        logger.error(f"API获取财报日历失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
        # 获取详情数据
        details = yahoo_api.get_earnings_details(symbol, earnings_date)
        
        return jsonify({
            'success': True,
            'data': details
        })
        
    except Exception as e:
        logger.error(f"API获取财报详情失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analyst_data/<symbol>')
def api_analyst_data(symbol):
    """API: 获取分析师数据"""
    try:
        # 从缓存获取或请求新数据
        if symbol in analyst_cache:
            analyst_data = analyst_cache[symbol]
        else:
            analyst_data = yahoo_api.get_analyst_recommendations(symbol)
            if analyst_data:
                analyst_cache[symbol] = analyst_data
        
        if analyst_data:
            return jsonify({
                'success': True,
                'data': asdict(analyst_data)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No analyst data found'
            }), 404
            
    except Exception as e:
        logger.error(f"API获取分析师数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_calendar_html(events, year, month):
    """生成日历HTML"""
    import calendar as cal
    
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
    
    # HTML模板
    html_template = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>美股财报日历 - {{ year }}年{{ month }}月</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { 
                max-width: 1400px; 
                margin: 0 auto; 
                background: white; 
                border-radius: 20px; 
                box-shadow: 0 20px 60px rgba(0,0,0,0.1); 
                overflow: hidden;
            }
            .header { 
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: white; 
                padding: 30px; 
                text-align: center; 
            }
            .title { 
                font-size: 2.5em; 
                font-weight: 300; 
                margin-bottom: 15px; 
                text-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            .nav { 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                gap: 20px; 
                margin-top: 20px;
            }
            .nav-btn { 
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
            }
            .nav-btn:hover { 
                background: rgba(255,255,255,0.3); 
                border-color: rgba(255,255,255,0.5);
                transform: translateY(-2px);
            }
            .current-month { 
                font-size: 1.3em; 
                font-weight: 500; 
                padding: 0 20px;
            }
            .calendar { 
                display: grid; 
                grid-template-columns: repeat(7, 1fr); 
                gap: 1px; 
                background: #e0e0e0;
                margin: 0;
            }
            .calendar-header { 
                background: #f8f9fa; 
                padding: 15px 10px; 
                text-align: center; 
                font-weight: 600; 
                font-size: 0.9em;
                color: #495057;
                border-bottom: 2px solid #dee2e6;
            }
            .calendar-day { 
                background: white; 
                min-height: 120px; 
                padding: 8px; 
                position: relative;
                transition: background-color 0.2s ease;
            }
            .calendar-day:hover { 
                background: #f8f9fa; 
            }
            .day-number { 
                font-weight: 600; 
                font-size: 1.1em; 
                color: #495057;
                margin-bottom: 8px;
            }
            .today .day-number { 
                color: white;
                background: #007bff;
                width: 28px;
                height: 28px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.9em;
            }
            .other-month { 
                background: #f8f8f8; 
                color: #adb5bd;
            }
            .earnings-event { 
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
            }
            .earnings-event:hover { 
                transform: translateY(-1px) scale(1.02); 
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                background: linear-gradient(135deg, #20c997, #28a745);
            }
            .earnings-event.bmo { 
                background: linear-gradient(135deg, #17a2b8, #007bff);
            }
            .earnings-event.amc { 
                background: linear-gradient(135deg, #fd7e14, #dc3545);
            }
            
            /* 模态框样式 */
            .modal { 
                display: none; 
                position: fixed; 
                z-index: 1000; 
                left: 0; 
                top: 0; 
                width: 100%; 
                height: 100%; 
                background: rgba(0,0,0,0.6); 
                backdrop-filter: blur(5px);
            }
            .modal-content { 
                background: white; 
                margin: 3% auto; 
                padding: 0; 
                border-radius: 15px; 
                width: 90%; 
                max-width: 900px; 
                max-height: 85vh; 
                overflow: hidden;
                box-shadow: 0 25px 50px rgba(0,0,0,0.25);
            }
            .modal-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 25px 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .modal-title {
                font-size: 1.5em;
                font-weight: 500;
            }
            .close { 
                color: white; 
                font-size: 28px; 
                font-weight: 300;
                cursor: pointer; 
                opacity: 0.8;
                transition: opacity 0.3s ease;
            }
            .close:hover { 
                opacity: 1;
                transform: scale(1.1);
            }
            .modal-body {
                padding: 30px;
                max-height: 60vh;
                overflow-y: auto;
            }
            .event-details { 
                margin: 20px 0; 
            }
            .detail-row {
                display: flex;
                justify-content: space-between;
                padding: 12px 0;
                border-bottom: 1px solid #e9ecef;
            }
            .detail-label {
                font-weight: 600;
                color: #495057;
            }
            .detail-value {
                color: #6c757d;
            }
            .analyst-section { 
                margin-top: 30px; 
            }
            .section-title {
                font-size: 1.3em;
                font-weight: 600;
                color: #495057;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #007bff;
            }
            .analyst-card { 
                border: 1px solid #dee2e6; 
                border-radius: 10px; 
                padding: 20px; 
                margin: 15px 0; 
                background: #f8f9fa;
                transition: transform 0.2s ease;
            }
            .analyst-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            .analyst-header { 
                font-weight: 600; 
                color: #495057; 
                margin-bottom: 10px; 
                font-size: 1.1em;
            }
            .analyst-meta { 
                color: #6c757d; 
                font-size: 0.9em; 
                margin-bottom: 12px; 
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
            }
            .loading { 
                text-align: center; 
                padding: 40px; 
                color: #6c757d; 
            }
            .spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #007bff;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                animation: spin 1s linear infinite;
                margin: 0 auto 15px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .error-message {
                text-align: center;
                padding: 40px;
                color: #dc3545;
            }
            
            /* 响应式设计 */
            @media (max-width: 768px) {
                .container { margin: 10px; border-radius: 10px; }
                .header { padding: 20px; }
                .title { font-size: 2em; }
                .nav { flex-direction: column; gap: 10px; }
                .calendar-day { min-height: 80px; padding: 5px; }
                .earnings-event { font-size: 0.7em; padding: 2px 4px; }
                .modal-content { width: 95%; margin: 5% auto; }
                .modal-body { padding: 20px; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 class="title">美股财报日历</h1>
                <div class="nav">
                    <a href="/?year={{ prev_year }}&month={{ prev_month }}" class="nav-btn">← 上月</a>
                    <span class="current-month">{{ year }}年{{ month }}月</span>
                    <a href="/?year={{ next_year }}&month={{ next_month }}" class="nav-btn">下月 →</a>
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
                
                {% for week in month_days %}
                    {% for day in week %}
                        {% if day == 0 %}
                            <div class="calendar-day other-month"></div>
                        {% else %}
                            <div class="calendar-day {{ 'today' if is_today(year, month, day) else '' }}">
                                <div class="day-number">{{ day }}</div>
                                {% if day in events_by_date %}
                                    {% for event in events_by_date[day] %}
                                        <div class="earnings-event {{ event.earnings_time.lower() if event.earnings_time else '' }}" 
                                             onclick="showEventDetails('{{ event.symbol }}', '{{ event.earnings_date }}')">
                                            {{ event.symbol }}
                                            {% if event.eps_estimate %}
                                                <br><small>EPS: ${{ "%.2f"|format(event.eps_estimate) }}</small>
                                            {% endif %}
                                        </div>
                                    {% endfor %}
                                {% endif %}
                            </div>
                        {% endif %}
                    {% endfor %}
                {% endfor %}
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
            function showEventDetails(symbol, date) {
                const modal = document.getElementById('eventModal');
                const content = document.getElementById('modalContent');
                
                modal.style.display = 'block';
                content.innerHTML = `
                    <div class="loading">
                        <div class="spinner"></div>
                        正在加载 ${symbol} 的财报详情和分析师评论...
                    </div>
                `;
                
                // 获取财报详情
                fetch(`/api/earnings_details?symbol=${symbol}&date=${date}`)
                    .then(response => response.json())
                    .then(result => {
                        if (result.success) {
                            displayEventDetails(result.data);
                        } else {
                            content.innerHTML = `<div class="error-message">加载失败: ${result.error}</div>`;
                        }
                    })
                    .catch(error => {
                        content.innerHTML = '<div class="error-message">网络错误，请稍后重试</div>';
                        console.error('Error:', error);
                    });
            }
            
            function displayEventDetails(data) {
                const content = document.getElementById('modalContent');
                
                let html = `
                    <div class="event-details">
                        <h2>${data.symbol} - ${data.company_name || data.symbol}</h2>
                `;
                
                // 基本信息
                const details = [
                    ['财报日期', data.earnings_date],
                    ['发布时间', data.earnings_time || 'N/A'],
                    ['季度', data.quarter || 'N/A'],
                    ['财政年度', data.fiscal_year || 'N/A']
                ];
                
                if (data.eps_estimate) {
                    details.push(['预期EPS', `$${data.eps_estimate.toFixed(2)}`]);
                }
                if (data.eps_actual) {
                    details.push(['实际EPS', `$${data.eps_actual.toFixed(2)}`]);
                }
                if (data.revenue_estimate) {
                    details.push(['预期营收', `$${(data.revenue_estimate/1000000).toFixed(0)}M`]);
                }
                if (data.revenue_actual) {
                    details.push(['实际营收', `$${(data.revenue_actual/1000000).toFixed(0)}M`]);
                }
                
                details.forEach(([label, value]) => {
                    html += `
                        <div class="detail-row">
                            <span class="detail-label">${label}:</span>
                            <span class="detail-value">${value}</span>
                        </div>
                    `;
                });
                
                html += '</div>';
                
                // 分析师数据
                if (data.analyst_data) {
                    const analyst = data.analyst_data;
                    html += `
                        <div class="analyst-section">
                            <h3 class="section-title">分析师数据</h3>
                            <div class="analyst-card">
                                <div class="detail-row">
                                    <span class="detail-label">当前价格:</span>
                                    <span class="detail-value">$${analyst.current_price.toFixed(2)}</span>
                                </div>
                    `;
                    
                    if (analyst.target_mean) {
                        html += `
                            <div class="detail-row">
                                <span class="detail-label">平均目标价:</span>
                                <span class="detail-value">$${analyst.target_mean.toFixed(2)}</span>
                            </div>
                        `;
                    }
                    
                    if (analyst.target_high && analyst.target_low) {
                        html += `
                            <div class="detail-row">
                                <span class="detail-label">目标价区间:</span>
                                <span class="detail-value">$${analyst.target_low.toFixed(2)} - $${analyst.target_high.toFixed(2)}</span>
                            </div>
                        `;
                    }
                    
                    if (analyst.recommendation_key) {
                        const ratings = {
                            'buy': '买入',
                            'hold': '持有', 
                            'sell': '卖出',
                            'strong_buy': '强烈买入',
                            'strong_sell': '强烈卖出'
                        };
                        html += `
                            <div class="detail-row">
                                <span class="detail-label">推荐等级:</span>
                                <span class="detail-value">${ratings[analyst.recommendation_key] || analyst.recommendation_key}</span>
                            </div>
                        `;
                    }
                    
                    html += '</div></div>';
                }
                
                // 分析师评论
                if (data.analyst_comments && data.analyst_comments.length > 0) {
                    html += `
                        <div class="analyst-section">
                            <h3 class="section-title">分析师评论</h3>
                    `;
                    
                    data.analyst_comments.forEach(comment => {
                        html += `
                            <div class="analyst-card">
                                <div class="analyst-header">${comment.analyst_name} - ${comment.firm}</div>
                                <div class="analyst-meta">
                                    <span>评级: ${comment.rating}</span>
                                    ${comment.price_target ? `<span>目标价: $${comment.price_target.toFixed(2)}</span>` : ''}
                                    <span>日期: ${comment.publish_date}</span>
                                    <span>来源: ${comment.source}</span>
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
    
    # 计算上下月
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
        
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    
    # 今日判断函数
    from datetime import date
    today = date.today()
    
    def is_today(y, m, d):
        return date(y, m, d) == today
    
    # 使用Jinja2渲染
    from jinja2 import Template
    template = Template(html_template)
    
    return template.render(
        year=year,
        month=month,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        month_days=month_days,
        events_by_date=events_by_date,
        is_today=is_today
    )

if __name__ == "__main__":
    print("启动财报日历Web服务器...")
    print("访问: http://localhost:5000")
    
    # 确保数据目录存在
    os.makedirs('data/calendar', exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)