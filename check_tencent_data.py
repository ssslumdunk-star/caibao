#!/usr/bin/env python3

from data_cache_manager import DataCacheManager

cm = DataCacheManager()

print('📊 检查腾讯8月份财报详情')
print('=' * 40)

events = cm.get_cached_earnings_events()

# 找到腾讯8月份数据
tencent_aug = [e for e in events if e.symbol == '0700.HK' and '2025-08' in e.earnings_date]

if tencent_aug:
    event = tencent_aug[0]
    print(f'腾讯控股 (0700.HK) 8月财报:')
    print(f'  财报日期: {event.earnings_date}')
    print(f'  营收预期: {event.revenue_estimate/100000000:.1f}亿美元')
    rev_actual = event.revenue_actual/100000000 if event.revenue_actual else None
    print(f'  营收实际: {rev_actual:.1f}亿美元' if rev_actual else '  营收实际: 未发布')
    print(f'  EPS预期: {event.eps_estimate}')
    print(f'  EPS实际: {event.eps_actual}' if event.eps_actual else '  EPS实际: 未发布')
    print(f'  数据来源: {event.data_source}')
else:
    print('❌ 没有找到腾讯8月份财报数据')

# 检查分析师数据中的价格信息
try:
    tencent_analyst = cm.get_cached_analyst_data('0700.HK')
    tencent_analyst = [tencent_analyst] if tencent_analyst else []
except:
    tencent_analyst = []

if tencent_analyst:
    data = tencent_analyst[0]
    print(f'\n💰 腾讯价格信息 (来自分析师数据):')
    print(f'  当前价格: ${data.current_price}')
    print(f'  目标价格: ${data.target_mean}')
    print(f'  数据来源: {data.data_source}')
    
    # 腾讯真实股价参考 (2025年9月)
    print(f'\n🔍 真实参考vs系统数据:')
    print(f'  腾讯控股真实价格约: HK$350-400 (约$45-50)')
    print(f'  系统显示价格: ${data.current_price}')
    is_realistic = 15 < data.current_price < 60
    print(f'  是否接近真实: {"✅ 接近" if is_realistic else "❌ 偏差较大"}')
    print(f'\n📝 结论: 当前显示的是模拟价格，不是真实市场价格')
else:
    print('❌ 没有找到腾讯分析师数据')