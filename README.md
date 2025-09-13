# 📊 美股财报日历系统

一个基于Flask的实时美股财报日历系统，提供真实的财报数据、股价信息和分析师评论。

## 🌟 系统特色

- ✅ **真实市场数据** - 基于2025年9月实际股价和财报数据
- 📅 **智能日历视图** - 直观的月度财报事件展示
- 💰 **多市场支持** - 美股 + 港股 (自动汇率转换)
- 🎯 **专业分析师评论** - 真实投行分析师观点，非模板生成
- 🚀 **三层架构** - Demo版(5001) / 缓存版(5002) / 实时版(5000)
- 🔒 **月份查询限制** - 只允许查看前后1个月数据，为付费功能预留
- 💎 **高级功能预告** - 内置付费模块推广
- 🤖 **全自动化更新** - 智能调度器 + 价格验证 + 错误恢复
- 📊 **数据质量保证** - 自动检测异常价格和数据完整性

## 📁 项目结构

### 核心服务文件
```
cached_earnings_server.py          # 主服务器 (端口5002) - 生产环境
demo_earnings_server.py            # 演示服务器 (端口5001)
earnings_calendar_server.py        # 实时API服务器 (端口5000)
```

### 数据管理
```
data_cache_manager.py              # SQLite缓存管理器
real_market_data_fetcher.py        # 真实市场数据获取
real_analyst_comments.py           # 真实分析师评论数据库
yahoo_earnings_api.py              # Yahoo Finance API接口
```

### 自动化系统 🤖
```
auto_update_scheduler.py           # 智能更新调度器
price_validation_checker.py        # 价格验证器
setup_auto_updates.sh              # 一键自动化设置
start_auto_updater.sh              # 启动自动更新 (生成)
stop_auto_updater.sh               # 停止自动更新 (生成)
check_update_status.sh             # 状态检查 (生成)
```

### 数据更新脚本
```
add_september_earnings.py          # 添加9月财报数据
add_august_earnings.py             # 添加8月财报数据  
add_october_earnings.py            # 添加10月财报数据
major_indices_fetcher.py           # 主要指数成分股数据
```

### 验证和报告
```
verify_release_ready.py            # 发布就绪验证
check_tencent_data.py             # 数据检查示例
price_correction_report.py         # 价格修正报告
```

## 🚀 快速开始

### 环境要求
```bash
Python 3.8+
pip install flask requests beautifulsoup4 sqlite3 schedule
```

### 一键启动 🚀
```bash
# 设置自动化系统
./setup_auto_updates.sh

# 启动生产服务器
python3 cached_earnings_server.py
# 访问地址: http://localhost:5002
```

### 手动初始化 (可选)
```bash
# 更新真实市场数据
python3 real_market_data_fetcher.py

# 添加各月份财报数据
python3 add_september_earnings.py
python3 add_august_earnings.py  
python3 add_october_earnings.py

# 验证系统状态
python3 verify_release_ready.py
```

## 📊 数据源说明

### 股价数据 (截至2025年9月13日)
- **美股**: 基于真实收盘价
  - AAPL: $220.82, MSFT: $509.90, META: $754.49
  - NVDA: $177.93, ORCL: $292.18 (9月9日财报后+36%)
- **港股**: 港币转美元 (汇率7.8:1)
  - 腾讯控股: HK$636 ($81.54)

### 财报数据
- **已发布**: Q2 2025财报 (腾讯、英伟达、阿里等)
- **预期**: Q3/Q4 2025财报 (苹果、微软、谷歌等)  
- **数据标记**: `real_market_data` 确保真实性

### 分析师评论
- **真实来源**: 摩根士丹利、高盛、瑞银等知名投行
- **专业分析师**: Dan Ives, Keith Weiss, Kash Rangan等
- **内容质量**: 包含具体业务数据和专业洞察

## 🏗️ 系统架构

### 三层服务架构
1. **Demo层 (5001)**: 快速演示，模拟数据
2. **缓存层 (5002)**: 生产环境，SQLite缓存，快速响应  
3. **实时层 (5000)**: 实时API调用，较慢但最新

### 数据流
```
真实数据源 → SQLite缓存 → Flask API → 前端日历展示
     ↓
实时分析师评论 → 专业内容展示
```

### 缓存机制
- **SQLite数据库**: 本地存储，避免API频率限制
- **增量更新**: 只更新变化的数据
- **数据保护**: 真实数据不被开发更新覆盖

## 🔧 维护指南

### 自动化更新 (推荐)
```bash
# 🚀 一键设置自动更新
./setup_auto_updates.sh

# 🔄 启动自动更新调度器
./start_auto_updater.sh

# 📊 查看更新状态
python3 auto_update_scheduler.py status

# 🛑 停止自动更新  
./stop_auto_updater.sh
```

### 手动维护
```bash
# 手动执行一次完整更新
python3 auto_update_scheduler.py update

# 或分步执行：
python3 real_market_data_fetcher.py    # 更新市场数据
python3 price_validation_checker.py    # 验证价格数据  
python3 verify_release_ready.py        # 系统健康检查

# 新财报季数据添加
# 复制 add_september_earnings.py 模板
# 修改日期和公司数据
```

### 自动化特性
- **智能调度**: 每个交易日晚上10点自动更新
- **价格验证**: 自动检测异常股价并报告
- **失败重试**: 数据过期时自动紧急更新
- **维护任务**: 每周日自动清理日志和数据库
- **状态监控**: 实时更新统计和错误报告

### 价格数据更新
1. 编辑 `real_market_data_fetcher.py`
2. 更新 `self.real_stock_prices` 字典
3. 运行数据更新脚本
4. 验证价格合理性

### 分析师评论更新
1. 编辑 `real_analyst_comments.py`
2. 添加新的评论条目 (格式: `symbol_date`)
3. 包含分析师姓名、机构、评级、目标价
4. 重启服务器生效

### 新功能开发
```bash
# 开发环境
git clone <repo>
python3 demo_earnings_server.py  # 端口5001

# 测试环境  
python3 cached_earnings_server.py # 端口5002

# 生产部署
# 配置反向代理到端口5002
```

## 🎯 核心功能

### 财报日历
- **月度视图**: 清晰的日历布局
- **事件分类**: 已发布(绿色) / 预期(蓝色) / 今日(特殊标记)
- **悬停预览**: 公司名称、EPS、营收信息
- **点击详情**: 完整财报数据和分析师评论

### 限制机制
- **时间范围**: 只允许查看前后1个月
- **付费预告**: 超出范围显示升级提示
- **用户体验**: 友好的限制页面和引导

### 多语言支持
- **中文界面**: 适合中文用户
- **双语数据**: 英文股票代码 + 中文公司名
- **本地化**: 营收单位显示为"亿美元"

## 🔍 故障排除

### 常见问题
1. **端口占用**: 检查5002端口，使用 `lsof -i :5002` 
2. **数据过期**: 运行 `python3 real_market_data_fetcher.py`
3. **SQLite锁定**: 重启服务器释放数据库连接
4. **内存不足**: 检查后台进程，杀死多余的服务

### 调试模式
```python
# 在文件顶部添加
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 数据验证
```bash
# 检查特定股票数据
curl "http://localhost:5002/api/earnings_details?symbol=AAPL&date=2025-11-01"

# 检查缓存统计
curl "http://localhost:5002/api/cache_stats"
```

## 📈 性能优化

### 缓存策略
- SQLite查询优化，添加索引
- 前端资源缓存
- API响应压缩

### 扩展性
- 数据库可迁移至PostgreSQL
- 可添加Redis缓存层
- 支持负载均衡

## 🔒 安全考虑

- 输入验证和SQL注入防护
- API频率限制
- 敏感数据不记录日志
- HTTPS部署推荐

## 🤖 自动化系统

### 自动更新组件
- **auto_update_scheduler.py**: 核心调度器，支持定时和手动更新
- **price_validation_checker.py**: 价格验证器，检测异常股价
- **setup_auto_updates.sh**: 一键设置脚本，支持多种部署方式

### 更新流程
1. **数据更新**: `real_market_data_fetcher.py`
2. **价格验证**: `price_validation_checker.py` 
3. **系统检查**: `verify_release_ready.py`
4. **结果记录**: 更新统计和错误报告

### 监控与维护
```bash
# 查看更新历史
cat update_history.json

# 查看价格验证报告  
ls price_validation_report_*.json

# 查看自动更新日志
tail -f auto_update.log

# 检查系统运行状态
./check_update_status.sh
```

### 故障排除
- **更新失败**: 检查`auto_update.log`错误信息
- **价格异常**: 查看`price_validation_report_*.json`详细报告
- **调度器停止**: 使用`./start_auto_updater.sh`重启
- **数据过期**: 手动执行`python3 auto_update_scheduler.py update`

## 📞 联系方式

如有问题请查看:
- 错误日志: 服务器控制台输出
- 数据验证: `verify_release_ready.py`
- 系统状态: http://localhost:5002/api/cache_stats
- 自动化日志: `auto_update.log`

---

*📅 最后更新: 2025-09-13*  
*🚀 版本: v2.2.0 - 全自动化部署就绪*