# 🚀 部署指南

快速部署美股财报日历系统的完整指南。

## 📦 快速部署

### 1. 环境准备
```bash
# 确保Python 3.8+
python3 --version

# 克隆项目
git clone <your-repo-url>
cd caibao

# 安装依赖
pip3 install flask requests beautifulsoup4 sqlite3 schedule
```

### 2. 一键启动 ⚡
```bash
# 设置自动化系统（选择选项1：Python调度器）
./setup_auto_updates.sh

# 启动自动更新调度器
./start_auto_updater.sh

# 启动Web服务器
python3 cached_earnings_server.py
```

### 3. 访问系统 🌐
```
主服务: http://localhost:5002
Demo版: http://localhost:5001 (如需要)
API状态: http://localhost:5002/api/cache_stats
```

## 🔧 维护操作

### 日常管理
```bash
# 查看系统状态
./check_update_status.sh

# 手动更新数据
python3 auto_update_scheduler.py update

# 查看更新日志
tail -f auto_update.log

# 停止自动更新
./stop_auto_updater.sh
```

### 价格验证
```bash
# 检查股价数据
python3 price_validation_checker.py

# 查看验证报告
ls price_validation_report_*.json
```

## 🎯 核心功能确认

运行以下命令确认系统正常：

```bash
# 1. 数据完整性
python3 verify_release_ready.py

# 2. 价格合理性  
python3 price_validation_checker.py

# 3. 服务器状态
curl http://localhost:5002/api/cache_stats

# 4. 自动更新状态
python3 auto_update_scheduler.py status
```

## 🔄 自动更新时间表

- **工作日22:00**: 自动更新股价和财报数据
- **周日09:00**: 系统维护和日志清理
- **数据过期检查**: 每小时自动检查，超过48小时自动更新

## 🆘 故障排除

### 常见问题
1. **端口被占用**: `lsof -ti:5002` 检查占用进程
2. **数据更新失败**: 查看 `auto_update.log` 日志
3. **价格异常**: 检查 `price_validation_report_*.json` 报告
4. **调度器停止**: 运行 `./start_auto_updater.sh` 重启

### 重置系统
```bash
# 停止所有服务
./stop_auto_updater.sh
pkill -f "cached_earnings_server.py"

# 清理数据库（谨慎操作）
rm earnings_cache.db

# 重新初始化
python3 real_market_data_fetcher.py
./start_auto_updater.sh
python3 cached_earnings_server.py
```

## 🌐 生产部署建议

### 反向代理 (Nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 进程守护 (systemd)
```ini
[Unit]
Description=Earnings Calendar System
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/caibao
ExecStart=/usr/bin/python3 cached_earnings_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 监控脚本
```bash
#!/bin/bash
# 添加到crontab: */5 * * * * /path/to/monitor.sh
if ! pgrep -f "cached_earnings_server.py" > /dev/null; then
    echo "$(date): Server down, restarting..." >> /var/log/earnings_monitor.log
    cd /path/to/caibao && python3 cached_earnings_server.py &
fi
```

## 📊 性能优化

### 数据库优化
```sql
-- 添加索引（如需要）
CREATE INDEX idx_earnings_date ON earnings_events(earnings_date);
CREATE INDEX idx_symbol ON earnings_events(symbol);
```

### 缓存优化
- SQLite数据库自动缓存
- 静态文件缓存（CSS/JS）
- API响应缓存（24小时）

---

🎉 **部署完成！** 

系统现在应该可以自动运行，提供实时的美股财报数据和分析师评论。

📧 如有问题，请检查日志文件或参考主README.md文档。