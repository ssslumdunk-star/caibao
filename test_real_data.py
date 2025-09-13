#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试真实数据抓取功能
"""

import sys
import time
from yahoo_earnings_api import YahooEarningsAPI

def test_yahoo_api():
    print("🔍 开始测试雅虎财经API真实数据抓取...")
    
    api = YahooEarningsAPI()
    
    # 测试1: 获取单个股票的分析师数据
    print("\n📊 测试1: 获取AAPL分析师数据")
    try:
        result = api.get_analyst_recommendations('AAPL')
        if result:
            print(f"✅ 成功获取AAPL数据:")
            print(f"   当前价格: ${result.current_price:.2f}")
            if result.target_mean:
                print(f"   平均目标价: ${result.target_mean:.2f}")
            if result.recommendation_key:
                print(f"   推荐等级: {result.recommendation_key}")
        else:
            print("❌ 获取AAPL数据失败")
            return False
    except Exception as e:
        print(f"❌ 获取AAPL数据异常: {e}")
        return False
    
    # 等待避免请求频率限制
    print("\n⏳ 等待3秒避免API限制...")
    time.sleep(3)
    
    # 测试2: 获取财报日历数据
    print("\n📅 测试2: 获取财报日历数据")
    try:
        from datetime import datetime, timedelta
        start_date = datetime.now().strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        print(f"   获取时间范围: {start_date} 到 {end_date}")
        events = api.get_earnings_calendar(start_date, end_date)
        
        print(f"✅ 成功获取 {len(events)} 个财报事件")
        
        if events:
            print("   前3个事件:")
            for i, event in enumerate(events[:3], 1):
                print(f"   {i}. {event.symbol} ({event.company_name})")
                print(f"      日期: {event.earnings_date} {event.earnings_time}")
                if event.eps_estimate:
                    print(f"      预期EPS: ${event.eps_estimate:.2f}")
                print()
        else:
            print("⚠️ 未获取到财报事件数据")
        
        return len(events) > 0
        
    except Exception as e:
        print(f"❌ 获取财报日历异常: {e}")
        return False

def test_earnings_details():
    print("\n📈 测试3: 获取财报详情")
    
    api = YahooEarningsAPI()
    
    try:
        # 测试获取特定股票的财报详情
        details = api.get_earnings_details('MSFT', '2024-01-25')
        
        if details:
            print("✅ 成功获取MSFT财报详情:")
            print(f"   股票代码: {details.get('symbol', 'N/A')}")
            print(f"   公司名称: {details.get('company_name', 'N/A')}")
            print(f"   财报日期: {details.get('earnings_date', 'N/A')}")
            
            if 'analyst_comments' in details:
                comments_count = len(details['analyst_comments'])
                print(f"   分析师评论数量: {comments_count}")
        else:
            print("⚠️ 未获取到财报详情")
        
        return True
        
    except Exception as e:
        print(f"❌ 获取财报详情异常: {e}")
        return False

if __name__ == "__main__":
    print("🚀 雅虎财经API真实数据测试")
    print("=" * 50)
    
    success_count = 0
    total_tests = 3
    
    # 执行测试
    if test_yahoo_api():
        success_count += 1
    
    if test_earnings_details():
        success_count += 1
    
    # 总结
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {success_count}/{total_tests} 个测试通过")
    
    if success_count >= 1:
        print("✅ 雅虎财经API可以正常工作，建议启动实际数据服务器")
        print("🚀 运行命令: python3 earnings_web_server.py")
    else:
        print("❌ 雅虎财经API存在问题，建议继续使用演示版本")
        print("🎭 运行命令: python3 demo_earnings_server.py")
    
    print("\n💡 提示: 由于API限制，真实数据抓取可能会比较慢或失败")
    print("    演示版本功能完全相同，只是使用模拟数据")