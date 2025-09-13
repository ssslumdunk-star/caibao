#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据缓存管理器
实现财报数据的本地缓存存储，减少API调用频率
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from pathlib import Path

logger = logging.getLogger('DataCacheManager')

@dataclass
class CachedEarningsEvent:
    """缓存的财报事件"""
    symbol: str
    company_name: str
    earnings_date: str
    earnings_time: str
    quarter: str
    fiscal_year: int
    eps_estimate: Optional[float] = None
    eps_actual: Optional[float] = None
    revenue_estimate: Optional[float] = None
    revenue_actual: Optional[float] = None
    beat_estimate: Optional[bool] = None
    last_updated: str = ""
    data_source: str = "yahoo_finance"

@dataclass
class CachedAnalystData:
    """缓存的分析师数据"""
    symbol: str
    current_price: float
    target_mean: Optional[float] = None
    target_high: Optional[float] = None
    target_low: Optional[float] = None
    recommendation_key: Optional[str] = None
    analyst_count: Optional[int] = None
    last_updated: str = ""
    data_source: str = "yahoo_finance"

class DataCacheManager:
    """数据缓存管理器"""
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据库文件路径
        self.db_path = self.cache_dir / "earnings_cache.db"
        
        # 初始化数据库
        self._init_database()
        
        # 缓存配置
        self.cache_config = {
            'earnings_cache_days': 1,      # 财报数据缓存1天
            'analyst_cache_hours': 6,      # 分析师数据缓存6小时  
            'prediction_cache_days': 7,    # 预测数据缓存7天
            'max_cache_entries': 10000     # 最大缓存条目数
        }
    
    def _init_database(self):
        """初始化SQLite数据库"""
        with sqlite3.connect(self.db_path) as conn:
            # 财报事件表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS earnings_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    company_name TEXT,
                    earnings_date TEXT NOT NULL,
                    earnings_time TEXT,
                    quarter TEXT,
                    fiscal_year INTEGER,
                    eps_estimate REAL,
                    eps_actual REAL,
                    revenue_estimate REAL,
                    revenue_actual REAL,
                    beat_estimate INTEGER,
                    last_updated TEXT NOT NULL,
                    data_source TEXT NOT NULL,
                    UNIQUE(symbol, earnings_date)
                )
            ''')
            
            # 分析师数据表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS analyst_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    current_price REAL NOT NULL,
                    target_mean REAL,
                    target_high REAL,
                    target_low REAL,
                    recommendation_key TEXT,
                    analyst_count INTEGER,
                    last_updated TEXT NOT NULL,
                    data_source TEXT NOT NULL,
                    UNIQUE(symbol)
                )
            ''')
            
            # 创建索引
            conn.execute('CREATE INDEX IF NOT EXISTS idx_earnings_symbol_date ON earnings_events(symbol, earnings_date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_analyst_symbol ON analyst_data(symbol)')
            
            conn.commit()
            logger.info("数据库初始化完成")
    
    def cache_earnings_events(self, events: List[CachedEarningsEvent]) -> int:
        """缓存财报事件数据"""
        if not events:
            return 0
            
        cached_count = 0
        current_time = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            for event in events:
                event.last_updated = current_time
                
                try:
                    # 使用 INSERT OR REPLACE 来处理重复数据
                    conn.execute('''
                        INSERT OR REPLACE INTO earnings_events 
                        (symbol, company_name, earnings_date, earnings_time, quarter, 
                         fiscal_year, eps_estimate, eps_actual, revenue_estimate, 
                         revenue_actual, beat_estimate, last_updated, data_source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        event.symbol, event.company_name, event.earnings_date,
                        event.earnings_time, event.quarter, event.fiscal_year,
                        event.eps_estimate, event.eps_actual, event.revenue_estimate,
                        event.revenue_actual, event.beat_estimate, event.last_updated,
                        event.data_source
                    ))
                    cached_count += 1
                    
                except sqlite3.Error as e:
                    logger.error(f"缓存财报事件失败 {event.symbol}: {e}")
                    
            conn.commit()
        
        logger.info(f"成功缓存 {cached_count} 个财报事件")
        return cached_count
    
    def get_cached_earnings_events(self, symbol: str = None, start_date: str = None, 
                                 end_date: str = None) -> List[CachedEarningsEvent]:
        """获取缓存的财报事件"""
        query = "SELECT * FROM earnings_events WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
            
        if start_date:
            query += " AND earnings_date >= ?"
            params.append(start_date)
            
        if end_date:
            query += " AND earnings_date <= ?"
            params.append(end_date)
            
        query += " ORDER BY earnings_date"
        
        events = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            for row in cursor.fetchall():
                event = CachedEarningsEvent(
                    symbol=row['symbol'],
                    company_name=row['company_name'],
                    earnings_date=row['earnings_date'],
                    earnings_time=row['earnings_time'],
                    quarter=row['quarter'],
                    fiscal_year=row['fiscal_year'],
                    eps_estimate=row['eps_estimate'],
                    eps_actual=row['eps_actual'],
                    revenue_estimate=row['revenue_estimate'],
                    revenue_actual=row['revenue_actual'],
                    beat_estimate=bool(row['beat_estimate']) if row['beat_estimate'] is not None else None,
                    last_updated=row['last_updated'],
                    data_source=row['data_source']
                )
                events.append(event)
        
        return events
    
    def cache_analyst_data(self, analyst_data: CachedAnalystData) -> bool:
        """缓存分析师数据"""
        current_time = datetime.now().isoformat()
        analyst_data.last_updated = current_time
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute('''
                    INSERT OR REPLACE INTO analyst_data 
                    (symbol, current_price, target_mean, target_high, target_low,
                     recommendation_key, analyst_count, last_updated, data_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    analyst_data.symbol, analyst_data.current_price,
                    analyst_data.target_mean, analyst_data.target_high,
                    analyst_data.target_low, analyst_data.recommendation_key,
                    analyst_data.analyst_count, analyst_data.last_updated,
                    analyst_data.data_source
                ))
                
                conn.commit()
                logger.info(f"成功缓存 {analyst_data.symbol} 分析师数据")
                return True
                
            except sqlite3.Error as e:
                logger.error(f"缓存分析师数据失败 {analyst_data.symbol}: {e}")
                return False
    
    def get_cached_analyst_data(self, symbol: str) -> Optional[CachedAnalystData]:
        """获取缓存的分析师数据"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM analyst_data WHERE symbol = ?", (symbol,)
            )
            
            row = cursor.fetchone()
            if row:
                return CachedAnalystData(
                    symbol=row['symbol'],
                    current_price=row['current_price'],
                    target_mean=row['target_mean'],
                    target_high=row['target_high'],
                    target_low=row['target_low'],
                    recommendation_key=row['recommendation_key'],
                    analyst_count=row['analyst_count'],
                    last_updated=row['last_updated'],
                    data_source=row['data_source']
                )
        
        return None
    
    def is_cache_valid(self, last_updated: str, cache_hours: int = 24) -> bool:
        """检查缓存是否仍然有效"""
        try:
            cached_time = datetime.fromisoformat(last_updated)
            current_time = datetime.now()
            time_diff = current_time - cached_time
            
            return time_diff < timedelta(hours=cache_hours)
            
        except Exception as e:
            logger.error(f"检查缓存有效性失败: {e}")
            return False
    
    def clean_expired_cache(self):
        """清理过期的缓存数据"""
        current_time = datetime.now()
        
        # 清理过期的财报事件 (超过30天)
        cutoff_date = (current_time - timedelta(days=30)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # 清理财报事件
            cursor = conn.execute(
                "DELETE FROM earnings_events WHERE last_updated < ?", (cutoff_date,)
            )
            earnings_deleted = cursor.rowcount
            
            # 清理分析师数据 (超过7天)
            analyst_cutoff = (current_time - timedelta(days=7)).isoformat()
            cursor = conn.execute(
                "DELETE FROM analyst_data WHERE last_updated < ?", (analyst_cutoff,)
            )
            analyst_deleted = cursor.rowcount
            
            conn.commit()
            
        logger.info(f"清理过期缓存: 财报事件 {earnings_deleted} 条, 分析师数据 {analyst_deleted} 条")
        
        return earnings_deleted + analyst_deleted
    
    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        stats = {}
        
        with sqlite3.connect(self.db_path) as conn:
            # 财报事件统计
            cursor = conn.execute("SELECT COUNT(*) FROM earnings_events")
            stats['earnings_events'] = cursor.fetchone()[0]
            
            # 分析师数据统计
            cursor = conn.execute("SELECT COUNT(*) FROM analyst_data")
            stats['analyst_data'] = cursor.fetchone()[0]
            
            # 最新更新时间
            cursor = conn.execute(
                "SELECT MAX(last_updated) FROM earnings_events"
            )
            result = cursor.fetchone()[0]
            stats['last_earnings_update'] = result or "无数据"
            
            cursor = conn.execute(
                "SELECT MAX(last_updated) FROM analyst_data"
            )
            result = cursor.fetchone()[0]
            stats['last_analyst_update'] = result or "无数据"
        
        return stats
    
    def export_cache_to_json(self, output_file: str = None) -> str:
        """导出缓存数据到JSON文件"""
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = self.cache_dir / f"cache_export_{timestamp}.json"
        
        # 获取所有数据
        earnings_events = self.get_cached_earnings_events()
        
        # 构建导出数据
        export_data = {
            'export_time': datetime.now().isoformat(),
            'earnings_events': [asdict(event) for event in earnings_events],
            'cache_stats': self.get_cache_stats()
        }
        
        # 写入JSON文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"缓存数据已导出到: {output_file}")
        return str(output_file)
    
    def import_cache_from_json(self, input_file: str) -> bool:
        """从JSON文件导入缓存数据"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 导入财报事件
            if 'earnings_events' in data:
                events = []
                for event_data in data['earnings_events']:
                    event = CachedEarningsEvent(**event_data)
                    events.append(event)
                
                count = self.cache_earnings_events(events)
                logger.info(f"从 {input_file} 导入了 {count} 个财报事件")
            
            return True
            
        except Exception as e:
            logger.error(f"导入缓存数据失败: {e}")
            return False

# 使用示例和工具函数
def create_sample_data():
    """创建一些示例缓存数据"""
    cache_manager = DataCacheManager()
    
    # 创建示例财报事件
    sample_events = [
        CachedEarningsEvent(
            symbol="AAPL",
            company_name="Apple Inc.",
            earnings_date="2024-01-25",
            earnings_time="AMC",
            quarter="Q1 2024",
            fiscal_year=2024,
            eps_estimate=2.10,
            eps_actual=2.18,
            revenue_estimate=117500000000,
            revenue_actual=119575000000,
            beat_estimate=True,
            data_source="manual_input"
        ),
        CachedEarningsEvent(
            symbol="MSFT", 
            company_name="Microsoft Corp.",
            earnings_date="2024-01-24",
            earnings_time="AMC",
            quarter="Q2 2024",
            fiscal_year=2024,
            eps_estimate=11.05,
            revenue_estimate=60000000000,
            data_source="manual_input"
        )
    ]
    
    # 缓存示例数据
    cache_manager.cache_earnings_events(sample_events)
    
    # 创建分析师数据示例
    analyst_data = CachedAnalystData(
        symbol="AAPL",
        current_price=230.50,
        target_mean=250.00,
        target_high=280.00,
        target_low=220.00,
        recommendation_key="buy",
        analyst_count=25,
        data_source="manual_input"
    )
    
    cache_manager.cache_analyst_data(analyst_data)
    
    return cache_manager

if __name__ == "__main__":
    # 演示缓存管理器功能
    print("🗄️ 数据缓存管理器演示")
    print("=" * 50)
    
    # 创建缓存管理器
    cache_manager = create_sample_data()
    
    # 显示统计信息
    stats = cache_manager.get_cache_stats()
    print("📊 缓存统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print()
    
    # 获取缓存数据示例
    print("📅 获取AAPL财报事件:")
    events = cache_manager.get_cached_earnings_events(symbol="AAPL")
    for event in events:
        print(f"  {event.earnings_date}: EPS预期={event.eps_estimate}, 实际={event.eps_actual}")
    
    print()
    
    # 获取分析师数据示例
    print("📈 获取AAPL分析师数据:")
    analyst = cache_manager.get_cached_analyst_data("AAPL")
    if analyst:
        print(f"  当前价格: ${analyst.current_price}")
        print(f"  目标价格: ${analyst.target_mean}")
        print(f"  推荐等级: {analyst.recommendation_key}")
    
    print()
    
    # 导出数据
    export_file = cache_manager.export_cache_to_json()
    print(f"📤 数据已导出到: {export_file}")
    
    print("\n✅ 缓存管理器功能正常")