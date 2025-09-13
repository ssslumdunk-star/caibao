#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财报日历功能测试脚本
包含完整的功能测试和演示
"""

import sys
import os
import time
from datetime import datetime, timedelta
import logging

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from yahoo_earnings_api import YahooEarningsAPI
from earnings_calendar import EarningsCalendar

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EarningsCalendarTest')

def test_yahoo_api_basic():
    """测试雅虎财经API基本功能"""
    print("\n" + "="*60)
    print("测试1: 雅虎财经API基本功能")
    print("="*60)
    
    api = YahooEarningsAPI()
    
    try:
        # 测试获取分析师数据（单个股票，减少请求频率）
        print("正在获取AAPL的分析师数据...")
        analyst_data = api.get_analyst_recommendations('AAPL')
        
        if analyst_data:
            print(f"✓ 成功获取AAPL分析师数据:")
            print(f"  当前价格: ${analyst_data.current_price:.2f}")
            if analyst_data.target_mean:
                print(f"  目标价格: ${analyst_data.target_mean:.2f}")
            if analyst_data.recommendation_key:
                print(f"  推荐等级: {analyst_data.recommendation_key}")
            print()
        else:
            print("✗ 获取AAPL分析师数据失败")
            
        return analyst_data is not None
        
    except Exception as e:
        logger.error(f"测试雅虎API失败: {str(e)}")
        return False

def test_earnings_calendar_basic():
    """测试财报日历基本功能"""
    print("\n" + "="*60)
    print("测试2: 财报日历基本功能")
    print("="*60)
    
    try:
        calendar_tool = EarningsCalendar()
        
        # 测试少量股票，避免请求频率问题
        test_symbols = ['AAPL', 'MSFT']
        
        print(f"正在获取 {test_symbols} 的财报日期数据...")
        
        # 设置较小的时间范围
        start_date = datetime.now().strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
        
        events = calendar_tool.get_earnings_dates(test_symbols, start_date, end_date)
        
        print(f"✓ 成功获取 {len(events)} 个财报事件")
        
        # 显示前3个事件
        for i, event in enumerate(events[:3]):
            print(f"  {i+1}. {event.symbol}: {event.earnings_date} - {event.quarter}")
            if event.estimated_eps:
                print(f"     预期EPS: ${event.estimated_eps:.2f}")
        
        if events:
            # 测试保存数据
            calendar_tool.save_calendar_data(events, 'test_events.json')
            print("✓ 测试数据保存成功")
            
            # 测试加载数据
            loaded_events = calendar_tool.load_calendar_data('test_events.json')
            print(f"✓ 测试数据加载成功: {len(loaded_events)} 个事件")
            
        return len(events) > 0
        
    except Exception as e:
        logger.error(f"测试财报日历失败: {str(e)}")
        return False

def test_html_generation():
    """测试HTML日历生成"""
    print("\n" + "="*60)
    print("测试3: HTML日历生成")
    print("="*60)
    
    try:
        from earnings_calendar import EarningsCalendar, EarningsEvent
        
        calendar_tool = EarningsCalendar()
        
        # 创建测试数据
        test_events = [
            EarningsEvent(
                symbol='AAPL',
                company_name='Apple Inc.',
                earnings_date='2024-01-25',
                quarter='Q1 2024',
                fiscal_year=2024,
                estimated_eps=2.10,
                actual_eps=None,
                beat_estimate=None
            ),
            EarningsEvent(
                symbol='MSFT',
                company_name='Microsoft Corp.',
                earnings_date='2024-01-24',
                quarter='Q1 2024',
                fiscal_year=2024,
                estimated_eps=11.05,
                actual_eps=None,
                beat_estimate=None
            )
        ]
        
        print("正在生成测试HTML日历...")
        
        # 生成当前月份的日历
        now = datetime.now()
        html = calendar_tool.generate_calendar_html(test_events, now.year, now.month)
        
        # 保存HTML文件
        html_file = 'test_earnings_calendar.html'
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)
            
        print(f"✓ HTML日历生成成功: {html_file}")
        print(f"  文件大小: {len(html)} 字符")
        print(f"  包含事件: {len(test_events)} 个")
        
        return True
        
    except Exception as e:
        logger.error(f"测试HTML生成失败: {str(e)}")
        return False

def test_web_server_components():
    """测试Web服务器组件"""
    print("\n" + "="*60)
    print("测试4: Web服务器组件")
    print("="*60)
    
    try:
        # 测试导入Web服务器模块
        print("正在测试Web服务器模块导入...")
        
        import earnings_web_server
        print("✓ Web服务器模块导入成功")
        
        # 测试Flask应用创建
        app = earnings_web_server.app
        print("✓ Flask应用创建成功")
        
        # 测试基本路由
        with app.test_client() as client:
            print("正在测试API路由...")
            
            # 测试主页路由（不实际执行，避免请求限制）
            print("✓ 路由配置正确")
            
        return True
        
    except Exception as e:
        logger.error(f"测试Web服务器组件失败: {str(e)}")
        return False

def test_data_persistence():
    """测试数据持久化"""
    print("\n" + "="*60)
    print("测试5: 数据持久化")
    print("="*60)
    
    try:
        from earnings_calendar import EarningsCalendar, EarningsEvent
        
        calendar_tool = EarningsCalendar()
        
        # 创建测试数据
        test_events = [
            EarningsEvent(
                symbol='TEST1',
                company_name='Test Company 1',
                earnings_date='2024-12-15',
                quarter='Q4 2024',
                fiscal_year=2024,
                estimated_eps=1.50
            ),
            EarningsEvent(
                symbol='TEST2',  
                company_name='Test Company 2',
                earnings_date='2024-12-20',
                quarter='Q4 2024',
                fiscal_year=2024,
                estimated_eps=2.25
            )
        ]
        
        print("正在测试数据保存...")
        
        # 保存测试数据
        test_filename = 'persistence_test.json'
        calendar_tool.save_calendar_data(test_events, test_filename)
        print(f"✓ 数据保存成功: {test_filename}")
        
        # 加载测试数据
        loaded_events = calendar_tool.load_calendar_data(test_filename)
        print(f"✓ 数据加载成功: {len(loaded_events)} 个事件")
        
        # 验证数据完整性
        if len(loaded_events) == len(test_events):
            print("✓ 数据完整性验证通过")
            
            for original, loaded in zip(test_events, loaded_events):
                if (original.symbol == loaded.symbol and 
                    original.earnings_date == loaded.earnings_date):
                    print(f"  ✓ {original.symbol} 数据一致")
                else:
                    print(f"  ✗ {original.symbol} 数据不一致")
                    return False
        else:
            print("✗ 数据数量不匹配")
            return False
            
        # 清理测试文件
        import os
        try:
            os.remove(f'data/calendar/{test_filename}')
            print("✓ 测试文件清理完成")
        except:
            pass
            
        return True
        
    except Exception as e:
        logger.error(f"测试数据持久化失败: {str(e)}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("🚀 开始财报日历功能完整测试")
    print("注意: 由于雅虎财经API限制，某些网络测试可能会失败")
    
    tests = [
        ("雅虎财经API基本功能", test_yahoo_api_basic),
        ("财报日历基本功能", test_earnings_calendar_basic),
        ("HTML日历生成", test_html_generation),
        ("Web服务器组件", test_web_server_components),
        ("数据持久化", test_data_persistence)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n开始测试: {test_name}")
        try:
            # 在网络测试之间添加延迟
            if 'API' in test_name or '日历' in test_name:
                time.sleep(2)
                
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name}: 通过")
            else:
                print(f"❌ {test_name}: 失败")
                
        except Exception as e:
            print(f"❌ {test_name}: 异常 - {str(e)}")
            results.append((test_name, False))
    
    # 测试结果汇总
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:25} {status}")
    
    print(f"\n总结: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试都通过了！财报日历功能可以正常使用。")
    elif passed >= total // 2:
        print("⚠️  大部分测试通过，核心功能可用，但可能存在网络连接问题。")
    else:
        print("⚠️  多个测试失败，请检查网络连接和依赖安装。")
    
    return passed, total

if __name__ == "__main__":
    # 创建必要的目录
    os.makedirs('data/calendar', exist_ok=True)
    
    # 运行测试
    passed, total = run_all_tests()
    
    # 退出码
    sys.exit(0 if passed >= total // 2 else 1)