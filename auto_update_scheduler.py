#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自动更新调度器
定时自动更新股价数据、财报信息和分析师评级
"""

import schedule
import time
import logging
import threading
import subprocess
import os
from datetime import datetime, timedelta
from typing import Dict, List
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AutoUpdateScheduler')

class AutoUpdateScheduler:
    """自动更新调度器"""
    
    def __init__(self):
        self.project_path = os.path.dirname(os.path.abspath(__file__))
        self.update_log_file = os.path.join(self.project_path, 'update_history.json')
        self.is_running = False
        
        # 更新统计
        self.update_stats = {
            'total_updates': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'last_successful_update': None,
            'last_failed_update': None
        }
        
        # 加载历史记录
        self._load_update_history()
    
    def _load_update_history(self):
        """加载更新历史记录"""
        try:
            if os.path.exists(self.update_log_file):
                with open(self.update_log_file, 'r', encoding='utf-8') as f:
                    self.update_stats.update(json.load(f))
                logger.info(f"📊 加载更新历史: {self.update_stats['total_updates']} 次更新")
        except Exception as e:
            logger.error(f"❌ 加载更新历史失败: {e}")
    
    def _save_update_history(self):
        """保存更新历史记录"""
        try:
            with open(self.update_log_file, 'w', encoding='utf-8') as f:
                json.dump(self.update_stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ 保存更新历史失败: {e}")
    
    def _run_script(self, script_name: str, description: str) -> bool:
        """运行Python脚本"""
        try:
            script_path = os.path.join(self.project_path, script_name)
            if not os.path.exists(script_path):
                logger.error(f"❌ 脚本不存在: {script_path}")
                return False
            
            logger.info(f"🚀 开始执行: {description}")
            result = subprocess.run(
                ['python3', script_path],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                logger.info(f"✅ {description} 完成")
                if result.stdout:
                    logger.debug(f"输出: {result.stdout}")
                return True
            else:
                logger.error(f"❌ {description} 失败")
                if result.stderr:
                    logger.error(f"错误: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ {description} 执行超时")
            return False
        except Exception as e:
            logger.error(f"❌ {description} 执行异常: {e}")
            return False
    
    def daily_market_data_update(self):
        """每日市场数据更新"""
        logger.info("📈 开始每日市场数据更新")
        
        update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        success = True
        
        # 更新真实市场数据
        if not self._run_script('real_market_data_fetcher.py', '真实市场数据更新'):
            success = False
        
        # 运行价格验证检查
        if not self._run_script('price_validation_checker.py', '股价数据验证'):
            success = False
            logger.warning("⚠️ 价格验证失败，可能存在数据异常")
        
        # 运行系统验证
        if not self._run_script('verify_release_ready.py', '系统就绪验证'):
            success = False
        
        # 更新统计
        self.update_stats['total_updates'] += 1
        if success:
            self.update_stats['successful_updates'] += 1
            self.update_stats['last_successful_update'] = update_time
            logger.info("✅ 每日数据更新成功完成")
        else:
            self.update_stats['failed_updates'] += 1
            self.update_stats['last_failed_update'] = update_time
            logger.error("❌ 每日数据更新失败")
        
        self._save_update_history()
        return success
    
    def weekly_maintenance(self):
        """每周维护任务"""
        logger.info("🔧 开始每周维护任务")
        
        # 清理旧日志
        self._cleanup_old_logs()
        
        # 数据库清理
        try:
            from data_cache_manager import DataCacheManager
            cache_manager = DataCacheManager()
            cache_manager.cleanup_old_data()
            logger.info("✅ 数据库清理完成")
        except Exception as e:
            logger.error(f"❌ 数据库清理失败: {e}")
        
        # 生成维护报告
        self._generate_maintenance_report()
    
    def _cleanup_old_logs(self):
        """清理旧日志文件"""
        try:
            log_files = ['auto_update.log', 'smart_data_fetcher.log']
            for log_file in log_files:
                log_path = os.path.join(self.project_path, log_file)
                if os.path.exists(log_path):
                    # 保留最近7天的日志
                    file_time = datetime.fromtimestamp(os.path.getmtime(log_path))
                    if datetime.now() - file_time > timedelta(days=7):
                        # 重命名旧日志
                        backup_name = f"{log_file}.{file_time.strftime('%Y%m%d')}"
                        os.rename(log_path, os.path.join(self.project_path, backup_name))
            logger.info("✅ 日志清理完成")
        except Exception as e:
            logger.error(f"❌ 日志清理失败: {e}")
    
    def _generate_maintenance_report(self):
        """生成维护报告"""
        try:
            report = {
                'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'update_stats': self.update_stats,
                'system_status': 'running',
                'next_maintenance': (datetime.now() + timedelta(weeks=1)).strftime('%Y-%m-%d')
            }
            
            report_file = os.path.join(self.project_path, 'maintenance_report.json')
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info("📊 维护报告已生成")
        except Exception as e:
            logger.error(f"❌ 维护报告生成失败: {e}")
    
    def is_trading_day(self) -> bool:
        """判断是否为交易日"""
        now = datetime.now()
        # 简单判断：周一到周五
        # 实际应用中可以集成假期日历
        return now.weekday() < 5
    
    def setup_schedule(self):
        """设置定时任务"""
        logger.info("⚙️ 设置自动更新定时任务")
        
        # 每个交易日晚上10点更新数据
        schedule.every().monday.at("22:00").do(self._safe_daily_update)
        schedule.every().tuesday.at("22:00").do(self._safe_daily_update)
        schedule.every().wednesday.at("22:00").do(self._safe_daily_update)
        schedule.every().thursday.at("22:00").do(self._safe_daily_update)
        schedule.every().friday.at("22:00").do(self._safe_daily_update)
        
        # 每周日上午9点执行维护任务
        schedule.every().sunday.at("09:00").do(self.weekly_maintenance)
        
        # 每天检查一次是否需要紧急更新
        schedule.every().hour.do(self._check_emergency_update)
        
        logger.info("✅ 定时任务设置完成")
        logger.info("📅 交易日更新时间: 每日22:00")
        logger.info("🔧 维护时间: 每周日09:00")
    
    def _safe_daily_update(self):
        """安全的每日更新（带异常处理）"""
        try:
            if self.is_trading_day():
                self.daily_market_data_update()
            else:
                logger.info("📅 非交易日，跳过数据更新")
        except Exception as e:
            logger.error(f"❌ 每日更新异常: {e}")
    
    def _check_emergency_update(self):
        """检查是否需要紧急更新"""
        try:
            # 如果上次更新超过48小时，进行紧急更新
            if self.update_stats['last_successful_update']:
                last_update = datetime.strptime(
                    self.update_stats['last_successful_update'], 
                    '%Y-%m-%d %H:%M:%S'
                )
                if datetime.now() - last_update > timedelta(hours=48):
                    logger.warning("⚠️ 检测到数据过期，执行紧急更新")
                    self.daily_market_data_update()
        except Exception as e:
            logger.error(f"❌ 紧急更新检查失败: {e}")
    
    def start_scheduler(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("⚠️ 调度器已在运行中")
            return
        
        self.is_running = True
        logger.info("🚀 自动更新调度器启动")
        logger.info(f"📊 历史更新统计: 总计{self.update_stats['total_updates']}次, 成功{self.update_stats['successful_updates']}次")
        
        self.setup_schedule()
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            logger.info("⏹️ 收到停止信号")
        finally:
            self.stop_scheduler()
    
    def stop_scheduler(self):
        """停止调度器"""
        self.is_running = False
        logger.info("⏹️ 自动更新调度器已停止")
        self._save_update_history()
    
    def run_manual_update(self):
        """手动运行一次更新"""
        logger.info("🖱️ 手动触发数据更新")
        return self.daily_market_data_update()
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        return {
            'is_running': self.is_running,
            'update_stats': self.update_stats,
            'next_run': schedule.next_run().strftime('%Y-%m-%d %H:%M:%S') if schedule.jobs else None,
            'scheduled_jobs': len(schedule.jobs)
        }

def main():
    """主函数"""
    scheduler = AutoUpdateScheduler()
    
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'start':
            # 启动定时调度器
            scheduler.start_scheduler()
        elif command == 'update':
            # 手动执行一次更新
            success = scheduler.run_manual_update()
            sys.exit(0 if success else 1)
        elif command == 'status':
            # 显示状态
            status = scheduler.get_status()
            print(json.dumps(status, ensure_ascii=False, indent=2))
        elif command == 'maintenance':
            # 执行维护任务
            scheduler.weekly_maintenance()
        else:
            print("用法:")
            print("  python3 auto_update_scheduler.py start      # 启动定时调度器")
            print("  python3 auto_update_scheduler.py update     # 手动执行一次更新")
            print("  python3 auto_update_scheduler.py status     # 查看状态")
            print("  python3 auto_update_scheduler.py maintenance # 执行维护")
    else:
        # 默认启动调度器
        scheduler.start_scheduler()

if __name__ == "__main__":
    main()