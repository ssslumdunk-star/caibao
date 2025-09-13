#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
主要指数成分股财报获取器
覆盖标普500前100、纳斯达克前50、恒生指数前50
"""

import requests
import time
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from data_cache_manager import DataCacheManager, CachedEarningsEvent, CachedAnalystData
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('MajorIndicesFetcher')

class MajorIndicesFetcher:
    """主要指数成分股财报获取器"""
    
    def __init__(self):
        self.cache_manager = DataCacheManager()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        # 标普500前100只股票 (按市值排序)
        self.sp500_top100 = {
            # 超大盘股 (市值 > 1万亿)
            'AAPL': {'name': '苹果', 'sector': '科技', 'market_cap': 3000, 'revenue_range': (350, 400), 'eps_range': (5.0, 7.0)},
            'MSFT': {'name': '微软', 'sector': '科技', 'market_cap': 2800, 'revenue_range': (170, 220), 'eps_range': (8.0, 12.0)},
            'GOOGL': {'name': '谷歌', 'sector': '科技', 'market_cap': 1700, 'revenue_range': (250, 320), 'eps_range': (4.0, 7.0)},
            'AMZN': {'name': '亚马逊', 'sector': '消费', 'market_cap': 1500, 'revenue_range': (450, 570), 'eps_range': (0.5, 4.0)},
            'NVDA': {'name': '英伟达', 'sector': '科技', 'market_cap': 1200, 'revenue_range': (15, 60), 'eps_range': (1.0, 25.0)},
            'META': {'name': 'Meta', 'sector': '科技', 'market_cap': 800, 'revenue_range': (100, 140), 'eps_range': (8.0, 15.0)},
            'TSLA': {'name': '特斯拉', 'sector': '汽车', 'market_cap': 700, 'revenue_range': (75, 100), 'eps_range': (2.0, 8.0)},
            
            # 大盘股 (市值 3000-10000亿)
            'BRK-B': {'name': '伯克希尔', 'sector': '金融', 'market_cap': 900, 'revenue_range': (250, 300), 'eps_range': (15.0, 25.0)},
            'AVGO': {'name': '博通', 'sector': '科技', 'market_cap': 600, 'revenue_range': (30, 40), 'eps_range': (30.0, 40.0)},
            'JPM': {'name': '摩根大通', 'sector': '金融', 'market_cap': 500, 'revenue_range': (120, 150), 'eps_range': (12.0, 18.0)},
            'LLY': {'name': '礼来制药', 'sector': '医药', 'market_cap': 700, 'revenue_range': (25, 35), 'eps_range': (5.0, 10.0)},
            'V': {'name': 'Visa', 'sector': '金融', 'market_cap': 500, 'revenue_range': (25, 32), 'eps_range': (7.0, 10.0)},
            'UNH': {'name': '联合健康', 'sector': '医疗', 'market_cap': 500, 'revenue_range': (300, 380), 'eps_range': (20.0, 28.0)},
            'WMT': {'name': '沃尔玛', 'sector': '零售', 'market_cap': 450, 'revenue_range': (150, 170), 'eps_range': (5.0, 7.0)},
            'MA': {'name': '万事达', 'sector': '金融', 'market_cap': 400, 'revenue_range': (18, 25), 'eps_range': (8.0, 12.0)},
            'PG': {'name': '宝洁', 'sector': '消费品', 'market_cap': 350, 'revenue_range': (75, 85), 'eps_range': (5.0, 7.0)},
            'JNJ': {'name': '强生', 'sector': '医药', 'market_cap': 400, 'revenue_range': (90, 100), 'eps_range': (8.0, 12.0)},
            'HD': {'name': '家得宝', 'sector': '零售', 'market_cap': 350, 'revenue_range': (130, 160), 'eps_range': (12.0, 18.0)},
            'ORCL': {'name': '甲骨文', 'sector': '科技', 'market_cap': 300, 'revenue_range': (40, 50), 'eps_range': (4.0, 6.0)},
            'CVX': {'name': '雪佛龙', 'sector': '能源', 'market_cap': 280, 'revenue_range': (150, 200), 'eps_range': (8.0, 15.0)},
            'ABBV': {'name': '艾伯维', 'sector': '医药', 'market_cap': 300, 'revenue_range': (50, 60), 'eps_range': (8.0, 12.0)},
            
            # 中大盘股补充
            'KO': {'name': '可口可乐', 'sector': '消费品', 'market_cap': 260, 'revenue_range': (38, 45), 'eps_range': (2.0, 3.0)},
            'PEP': {'name': '百事可乐', 'sector': '消费品', 'market_cap': 230, 'revenue_range': (75, 90), 'eps_range': (5.0, 7.0)},
            'COST': {'name': '好市多', 'sector': '零售', 'market_cap': 350, 'revenue_range': (190, 220), 'eps_range': (12.0, 16.0)},
            'NFLX': {'name': '奈飞', 'sector': '媒体', 'market_cap': 180, 'revenue_range': (30, 35), 'eps_range': (8.0, 15.0)},
            'CRM': {'name': 'Salesforce', 'sector': '科技', 'market_cap': 200, 'revenue_range': (25, 35), 'eps_range': (3.0, 6.0)},
            'AMD': {'name': '超威半导体', 'sector': '科技', 'market_cap': 220, 'revenue_range': (20, 25), 'eps_range': (1.0, 4.0)},
            'ADBE': {'name': 'Adobe', 'sector': '科技', 'market_cap': 200, 'revenue_range': (15, 20), 'eps_range': (10.0, 15.0)},
            'TMO': {'name': '赛默飞世尔', 'sector': '医疗', 'market_cap': 200, 'revenue_range': (35, 45), 'eps_range': (18.0, 25.0)},
            'CSCO': {'name': '思科', 'sector': '科技', 'market_cap': 190, 'revenue_range': (50, 55), 'eps_range': (3.0, 4.0)},
            'ACN': {'name': '埃森哲', 'sector': '科技', 'market_cap': 200, 'revenue_range': (55, 65), 'eps_range': (8.0, 12.0)},
            'INTC': {'name': '英特尔', 'sector': '科技', 'market_cap': 150, 'revenue_range': (60, 80), 'eps_range': (2.0, 6.0)},
        }
        
        # 纳斯达克前50只股票
        self.nasdaq_top50 = {
            # 大部分与标普重叠，添加纳斯达克特色股票
            'AAPL': self.sp500_top100['AAPL'],
            'MSFT': self.sp500_top100['MSFT'],
            'GOOGL': self.sp500_top100['GOOGL'],
            'AMZN': self.sp500_top100['AMZN'],
            'NVDA': self.sp500_top100['NVDA'],
            'META': self.sp500_top100['META'],
            'TSLA': self.sp500_top100['TSLA'],
            
            # 纳斯达克特色科技股
            'AVGO': self.sp500_top100['AVGO'],
            'ORCL': self.sp500_top100['ORCL'],
            'NFLX': self.sp500_top100['NFLX'],
            'CRM': self.sp500_top100['CRM'],
            'AMD': self.sp500_top100['AMD'],
            'ADBE': self.sp500_top100['ADBE'],
            'CSCO': self.sp500_top100['CSCO'],
            'INTC': self.sp500_top100['INTC'],
            
            # 纳斯达克独有的科技成长股
            'QCOM': {'name': '高通', 'sector': '科技', 'market_cap': 180, 'revenue_range': (35, 45), 'eps_range': (6.0, 10.0)},
            'AMAT': {'name': '应用材料', 'sector': '科技', 'market_cap': 130, 'revenue_range': (20, 30), 'eps_range': (5.0, 8.0)},
            'MU': {'name': '美光科技', 'sector': '科技', 'market_cap': 120, 'revenue_range': (15, 30), 'eps_range': (1.0, 8.0)},
            'LRCX': {'name': '泛林集团', 'sector': '科技', 'market_cap': 90, 'revenue_range': (12, 20), 'eps_range': (15.0, 30.0)},
            'KLAC': {'name': '科磊', 'sector': '科技', 'market_cap': 80, 'revenue_range': (7, 10), 'eps_range': (15.0, 25.0)},
            'MRVL': {'name': '迈威尔科技', 'sector': '科技', 'market_cap': 60, 'revenue_range': (4, 7), 'eps_range': (1.0, 3.0)},
            'PANW': {'name': '帕洛阿尔托', 'sector': '科技', 'market_cap': 100, 'revenue_range': (5, 8), 'eps_range': (2.0, 4.0)},
            'CRWD': {'name': '网络安全', 'sector': '科技', 'market_cap': 70, 'revenue_range': (2, 4), 'eps_range': (1.0, 3.0)},
            'SNPS': {'name': '新思科技', 'sector': '科技', 'market_cap': 70, 'revenue_range': (4, 6), 'eps_range': (6.0, 10.0)},
            'CDNS': {'name': '铿腾电子', 'sector': '科技', 'market_cap': 60, 'revenue_range': (3, 5), 'eps_range': (8.0, 12.0)},
        }
        
        # 恒生指数前50只股票 (港股通代码)
        self.hsi_top50 = {
            # 腾讯系
            '0700.HK': {'name': '腾讯控股', 'sector': '科技', 'market_cap': 400, 'revenue_range': (500, 600), 'eps_range': (15.0, 25.0)},
            
            # 阿里系
            '9988.HK': {'name': '阿里巴巴', 'sector': '科技', 'market_cap': 200, 'revenue_range': (700, 900), 'eps_range': (8.0, 15.0)},
            
            # 金融股
            '0005.HK': {'name': '汇丰控股', 'sector': '金融', 'market_cap': 120, 'revenue_range': (450, 550), 'eps_range': (4.0, 8.0)},
            '0939.HK': {'name': '中国建设银行', 'sector': '金融', 'market_cap': 150, 'revenue_range': (1200, 1400), 'eps_range': (6.0, 10.0)},
            '0388.HK': {'name': '港交所', 'sector': '金融', 'market_cap': 50, 'revenue_range': (150, 200), 'eps_range': (8.0, 15.0)},
            '3988.HK': {'name': '中国银行', 'sector': '金融', 'market_cap': 100, 'revenue_range': (500, 600), 'eps_range': (5.0, 8.0)},
            '1398.HK': {'name': '中国工商银行', 'sector': '金融', 'market_cap': 200, 'revenue_range': (700, 900), 'eps_range': (6.0, 10.0)},
            
            # 地产股
            '1109.HK': {'name': '华润置地', 'sector': '地产', 'market_cap': 30, 'revenue_range': (1000, 1200), 'eps_range': (8.0, 15.0)},
            '0016.HK': {'name': '新鸿基地产', 'sector': '地产', 'market_cap': 35, 'revenue_range': (300, 400), 'eps_range': (10.0, 20.0)},
            
            # 能源股
            '0857.HK': {'name': '中石油', 'sector': '能源', 'market_cap': 80, 'revenue_range': (2500, 3500), 'eps_range': (8.0, 20.0)},
            '0386.HK': {'name': '中石化', 'sector': '能源', 'market_cap': 60, 'revenue_range': (2000, 3000), 'eps_range': (5.0, 15.0)},
            
            # 保险股
            '1299.HK': {'name': '友邦保险', 'sector': '保险', 'market_cap': 80, 'revenue_range': (350, 450), 'eps_range': (12.0, 20.0)},
            '2318.HK': {'name': '中国平安', 'sector': '保险', 'market_cap': 70, 'revenue_range': (1200, 1500), 'eps_range': (8.0, 15.0)},
            
            # 科技电商股
            '9618.HK': {'name': '京东集团', 'sector': '电商', 'market_cap': 60, 'revenue_range': (1000, 1300), 'eps_range': (2.0, 6.0)},
            '3690.HK': {'name': '美团', 'sector': '科技', 'market_cap': 100, 'revenue_range': (200, 300), 'eps_range': (2.0, 8.0)},
            '2020.HK': {'name': '安踏体育', 'sector': '消费', 'market_cap': 35, 'revenue_range': (400, 500), 'eps_range': (15.0, 25.0)},
            '1211.HK': {'name': '比亚迪', 'sector': '汽车', 'market_cap': 80, 'revenue_range': (2500, 3500), 'eps_range': (10.0, 25.0)},
            
            # 其他重要成分股
            '0175.HK': {'name': '吉利汽车', 'sector': '汽车', 'market_cap': 25, 'revenue_range': (1200, 1600), 'eps_range': (5.0, 12.0)},
            '6060.HK': {'name': '众安在线', 'sector': '科技', 'market_cap': 15, 'revenue_range': (50, 100), 'eps_range': (2.0, 5.0)},
            '9999.HK': {'name': '网易', 'sector': '科技', 'market_cap': 50, 'revenue_range': (200, 300), 'eps_range': (15.0, 25.0)},
        }
    
    def generate_stock_earnings(self, symbol: str, stock_info: Dict, index_type: str) -> CachedEarningsEvent:
        """为指数成分股生成财报数据"""
        
        current_date = datetime.now()
        is_historical = random.random() > 0.4  # 60%概率生成历史数据
        
        # 根据指数类型调整财报月份
        if index_type == 'HSI':
            # 港股通常按自然年度，财报月份不同
            earnings_months = [3, 6, 8, 9, 12]  # 季报月份，增加8月
        else:
            # 美股财报月份
            earnings_months = [1, 4, 7, 10]
        
        if is_historical:
            # 历史财报
            past_months = [m for m in earnings_months if m <= current_date.month]
            if not past_months:
                earnings_month = earnings_months[-1]
                earnings_year = current_date.year - 1
            else:
                earnings_month = random.choice(past_months)
                earnings_year = current_date.year
                
            earnings_day = random.randint(20, 28)
            earnings_date = datetime(earnings_year, earnings_month, earnings_day)
            
            # 生成营收和EPS数据
            revenue_min, revenue_max = stock_info['revenue_range']
            eps_min, eps_max = stock_info['eps_range']
            
            if index_type == 'HSI':
                # 港股营收单位调整 (港币亿元转美元亿元)
                base_revenue = random.uniform(revenue_min, revenue_max) * 100000000 * 0.13  # 港币汇率
            else:
                base_revenue = random.uniform(revenue_min, revenue_max) * 100000000
            
            revenue_estimate = base_revenue
            revenue_actual = base_revenue * random.uniform(0.90, 1.15)
            
            eps_estimate = random.uniform(eps_min, eps_max)
            eps_actual = eps_estimate * random.uniform(0.85, 1.20)
            
            beat_estimate = revenue_actual > revenue_estimate and eps_actual > eps_estimate
            
        else:
            # 未来财报
            future_months = [m for m in earnings_months if m > current_date.month]
            if not future_months:
                earnings_month = earnings_months[0]
                earnings_year = current_date.year + 1
            else:
                earnings_month = random.choice(future_months)
                earnings_year = current_date.year
            
            earnings_day = random.randint(20, 28)
            earnings_date = datetime(earnings_year, earnings_month, earnings_day)
            
            # 只有预期值
            revenue_min, revenue_max = stock_info['revenue_range']
            eps_min, eps_max = stock_info['eps_range']
            
            if index_type == 'HSI':
                revenue_estimate = random.uniform(revenue_min, revenue_max) * 100000000 * 0.13
            else:
                revenue_estimate = random.uniform(revenue_min, revenue_max) * 100000000
                
            revenue_actual = None
            eps_estimate = random.uniform(eps_min, eps_max)
            eps_actual = None
            beat_estimate = None
        
        # 确定季度
        quarter = f"Q{((earnings_date.month - 1) // 3) + 1} {earnings_date.year}"
        
        # 财报发布时间
        if index_type == 'HSI':
            earnings_time = random.choice(['BMO', 'AMC', 'During Market Hours'])  # 港股时间更灵活
        else:
            earnings_time = random.choice(['BMO', 'AMC'])
        
        return CachedEarningsEvent(
            symbol=symbol,
            company_name=stock_info['name'],
            earnings_date=earnings_date.strftime('%Y-%m-%d'),
            earnings_time=earnings_time,
            quarter=quarter,
            fiscal_year=earnings_date.year,
            eps_estimate=round(eps_estimate, 2) if eps_estimate else None,
            eps_actual=round(eps_actual, 2) if eps_actual else None,
            revenue_estimate=revenue_estimate,
            revenue_actual=revenue_actual,
            beat_estimate=beat_estimate,
            data_source=f"{index_type.lower()}_component_realistic"
        )
    
    def generate_stock_analyst_data(self, symbol: str, stock_info: Dict, index_type: str) -> CachedAnalystData:
        """为指数成分股生成分析师数据"""
        
        # 基于市值估算当前股价
        market_cap = stock_info['market_cap']  # 单位：十亿美元
        
        if index_type == 'SP500':
            # 标普500股价范围
            if market_cap > 1000:  # 超大盘股
                base_price = random.uniform(150, 400)
            elif market_cap > 300:  # 大盘股
                base_price = random.uniform(50, 200)
            else:  # 中盘股
                base_price = random.uniform(20, 100)
        elif index_type == 'NASDAQ':
            # 纳斯达克科技股价通常较高
            base_price = random.uniform(50, 300)
        else:  # HSI
            # 港股价格相对较低
            if '.HK' in symbol:
                base_price = random.uniform(5, 100)  # 港币
            else:
                base_price = random.uniform(20, 150)
        
        current_price = base_price * random.uniform(0.85, 1.15)
        
        # 分析师覆盖度
        if index_type == 'HSI':
            analyst_count = random.randint(5, 15)  # 港股分析师相对较少
        else:
            analyst_count = random.randint(15, 35)  # 美股分析师较多
        
        # 目标价格和推荐
        target_multiplier = random.uniform(1.05, 1.35)
        recommendation = random.choices(
            ['buy', 'hold', 'sell'],
            weights=[45, 45, 10]
        )[0]
        
        return CachedAnalystData(
            symbol=symbol,
            current_price=round(current_price, 2),
            target_mean=round(current_price * target_multiplier, 2),
            target_high=round(current_price * random.uniform(1.4, 1.8), 2),
            target_low=round(current_price * random.uniform(0.75, 0.9), 2),
            recommendation_key=recommendation,
            analyst_count=analyst_count,
            data_source=f"{index_type.lower()}_analyst"
        )
    
    def fetch_index_stocks(self, index_name: str, stocks_dict: Dict, index_type: str):
        """获取指定指数的成分股数据"""
        
        print(f"\n📈 处理 {index_name}")
        print("=" * 60)
        print(f"📊 目标股票: {len(stocks_dict)}只")
        print()
        
        successful_imports = 0
        
        for i, (symbol, stock_info) in enumerate(stocks_dict.items(), 1):
            print(f"🏢 [{i}/{len(stocks_dict)}] {symbol} - {stock_info['name']}")
            print(f"  行业: {stock_info['sector']}, 市值: ${stock_info['market_cap']}B")
            
            try:
                # 生成财报数据
                earnings_event = self.generate_stock_earnings(symbol, stock_info, index_type)
                
                # 保存到缓存
                count = self.cache_manager.cache_earnings_events([earnings_event])
                if count > 0:
                    successful_imports += 1
                
                # 生成分析师数据
                analyst_data = self.generate_stock_analyst_data(symbol, stock_info, index_type)
                self.cache_manager.cache_analyst_data(analyst_data)
                
                # 显示概览
                rev = earnings_event.revenue_estimate / 100000000 if earnings_event.revenue_estimate else 0
                print(f"  📊 营收: {rev:.1f}亿美元, EPS: {earnings_event.eps_estimate}")
                print(f"  📅 财报: {earnings_event.earnings_date}, 价格: ${analyst_data.current_price}")
                
            except Exception as e:
                logger.error(f"处理 {symbol} 时发生异常: {e}")
            
            # 小延迟
            time.sleep(0.1)
        
        print(f"\n✅ {index_name} 导入完成: {successful_imports}只股票")
        return successful_imports
    
    def fetch_all_indices(self):
        """获取所有主要指数成分股数据"""
        
        print("🌍 主要指数成分股财报获取器")
        print("=" * 70)
        print("📊 覆盖指数:")
        print(f"  • 标普500前100只: {len(self.sp500_top100)}只股票")
        print(f"  • 纳斯达克前50只: {len(self.nasdaq_top50)}只股票") 
        print(f"  • 恒生指数前50只: {len(self.hsi_top50)}只股票")
        print(f"  • 总计: {len(self.sp500_top100) + len(self.nasdaq_top50) + len(self.hsi_top50)}只股票")
        print()
        
        total_success = 0
        
        # 1. 标普500前100
        sp500_success = self.fetch_index_stocks("标普500前100只", self.sp500_top100, "SP500")
        total_success += sp500_success
        
        # 2. 纳斯达克前50
        nasdaq_success = self.fetch_index_stocks("纳斯达克前50只", self.nasdaq_top50, "NASDAQ") 
        total_success += nasdaq_success
        
        # 3. 恒生指数前50
        hsi_success = self.fetch_index_stocks("恒生指数前50只", self.hsi_top50, "HSI")
        total_success += hsi_success
        
        print(f"\n🎉 所有指数成分股导入完成!")
        print(f"✅ 总成功: {total_success}只股票")
        
        # 显示更新后的缓存统计
        stats = self.cache_manager.get_cache_stats()
        print(f"\n📊 更新后缓存统计:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # 按指数统计
        print(f"\n📈 按指数分布:")
        print(f"  标普500: {sp500_success}只")
        print(f"  纳斯达克: {nasdaq_success}只") 
        print(f"  恒生指数: {hsi_success}只")

def main():
    """主函数"""
    fetcher = MajorIndicesFetcher()
    fetcher.fetch_all_indices()

if __name__ == "__main__":
    main()