#!/bin/bash

# 自动更新定时任务设置脚本
# 设置系统级的cron定时任务来自动更新财报数据

set -e

echo "🚀 财报系统自动更新设置向导"
echo "=================================="

# 获取项目路径
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH=$(which python3)

echo "📁 项目路径: $PROJECT_DIR"
echo "🐍 Python路径: $PYTHON_PATH"
echo ""

# 检查必要文件
echo "🔍 检查必要文件..."
REQUIRED_FILES=(
    "auto_update_scheduler.py"
    "real_market_data_fetcher.py" 
    "price_validation_checker.py"
    "verify_release_ready.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$PROJECT_DIR/$file" ]]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (缺失)"
        exit 1
    fi
done

echo ""
echo "🕐 设置定时任务选项:"
echo "1. 使用Python调度器 (推荐)"
echo "2. 使用系统cron任务"
echo "3. 只创建手动更新脚本"
echo ""

read -p "请选择 (1-3): " choice

case $choice in
    1)
        echo ""
        echo "📦 设置Python调度器..."
        
        # 安装schedule库
        echo "安装依赖库..."
        pip3 install schedule requests beautifulsoup4 sqlite3
        
        # 创建服务脚本
        cat > "$PROJECT_DIR/start_auto_updater.sh" << 'EOF'
#!/bin/bash

# 启动自动更新调度器守护进程
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 检查是否已经在运行
if pgrep -f "auto_update_scheduler.py" > /dev/null; then
    echo "⚠️ 自动更新调度器已在运行中"
    exit 1
fi

# 启动调度器
echo "🚀 启动自动更新调度器..."
nohup python3 auto_update_scheduler.py start > auto_updater.log 2>&1 &
echo $! > auto_updater.pid

echo "✅ 调度器已启动，PID: $(cat auto_updater.pid)"
echo "📄 日志文件: auto_updater.log"
echo ""
echo "使用以下命令管理:"
echo "  查看状态: python3 auto_update_scheduler.py status"
echo "  停止服务: kill \$(cat auto_updater.pid)"
echo "  查看日志: tail -f auto_updater.log"
EOF
        
        # 创建停止脚本
        cat > "$PROJECT_DIR/stop_auto_updater.sh" << 'EOF'
#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [[ -f "auto_updater.pid" ]]; then
    PID=$(cat auto_updater.pid)
    if kill "$PID" 2>/dev/null; then
        echo "✅ 自动更新调度器已停止 (PID: $PID)"
        rm auto_updater.pid
    else
        echo "⚠️ 进程已不存在，清理PID文件"
        rm auto_updater.pid
    fi
else
    echo "⚠️ PID文件不存在，尝试查找进程..."
    pkill -f "auto_update_scheduler.py" && echo "✅ 进程已终止" || echo "❌ 未找到运行的进程"
fi
EOF
        
        chmod +x "$PROJECT_DIR/start_auto_updater.sh"
        chmod +x "$PROJECT_DIR/stop_auto_updater.sh"
        
        echo "✅ Python调度器设置完成!"
        echo ""
        echo "使用方法:"
        echo "  启动: ./start_auto_updater.sh"
        echo "  停止: ./stop_auto_updater.sh"
        echo "  状态: python3 auto_update_scheduler.py status"
        echo "  手动更新: python3 auto_update_scheduler.py update"
        ;;
        
    2)
        echo ""
        echo "⏰ 设置系统cron任务..."
        
        # 创建cron任务配置
        CRON_JOB="# 财报系统自动更新
# 每个工作日晚上10点更新数据  
0 22 * * 1-5 cd $PROJECT_DIR && $PYTHON_PATH auto_update_scheduler.py update >> auto_update_cron.log 2>&1

# 每周日上午9点执行维护
0 9 * * 0 cd $PROJECT_DIR && $PYTHON_PATH auto_update_scheduler.py maintenance >> maintenance_cron.log 2>&1"

        echo "$CRON_JOB" > "$PROJECT_DIR/crontab_entries.txt"
        
        echo "📄 cron任务配置已生成: crontab_entries.txt"
        echo ""
        echo "手动安装步骤:"
        echo "1. 编辑crontab: crontab -e"
        echo "2. 添加以下内容:"
        echo "$CRON_JOB"
        echo ""
        echo "或者自动安装:"
        read -p "是否现在安装到crontab? (y/N): " install_cron
        
        if [[ "$install_cron" =~ ^[Yy]$ ]]; then
            # 备份现有crontab
            crontab -l > "$PROJECT_DIR/crontab_backup_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true
            
            # 添加新任务
            (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
            
            echo "✅ cron任务已安装!"
            echo "📄 备份文件: crontab_backup_*.txt"
        fi
        ;;
        
    3)
        echo ""
        echo "📝 创建手动更新脚本..."
        
        # 创建手动更新脚本
        cat > "$PROJECT_DIR/manual_update.sh" << 'EOF'
#!/bin/bash

# 手动数据更新脚本
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "🚀 开始手动数据更新..."
echo "时间: $(date)"
echo "=================================="

# 更新市场数据
echo "📊 更新市场数据..."
python3 real_market_data_fetcher.py
UPDATE_RESULT=$?

if [[ $UPDATE_RESULT -eq 0 ]]; then
    echo "✅ 市场数据更新完成"
    
    # 验证价格数据
    echo ""
    echo "🔍 验证价格数据..."
    python3 price_validation_checker.py
    VALIDATION_RESULT=$?
    
    if [[ $VALIDATION_RESULT -eq 0 ]]; then
        echo "✅ 价格验证通过"
    else
        echo "⚠️ 价格验证发现异常，请检查报告文件"
    fi
    
    # 系统就绪检查
    echo ""
    echo "🔧 系统就绪检查..."
    python3 verify_release_ready.py
    VERIFY_RESULT=$?
    
    if [[ $VERIFY_RESULT -eq 0 ]]; then
        echo "✅ 系统验证通过"
    else
        echo "⚠️ 系统验证发现问题"
    fi
    
else
    echo "❌ 市场数据更新失败"
    exit 1
fi

echo ""
echo "🎉 手动更新完成!"
echo "时间: $(date)"
EOF
        
        chmod +x "$PROJECT_DIR/manual_update.sh"
        
        echo "✅ 手动更新脚本创建完成!"
        echo ""
        echo "使用方法:"
        echo "  执行更新: ./manual_update.sh"
        ;;
        
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

# 创建状态检查脚本
cat > "$PROJECT_DIR/check_update_status.sh" << 'EOF'
#!/bin/bash

# 检查更新状态脚本
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "📊 财报系统状态检查"
echo "==================="
echo "时间: $(date)"
echo ""

# 检查Python调度器状态
if [[ -f "auto_updater.pid" ]]; then
    PID=$(cat auto_updater.pid)
    if kill -0 "$PID" 2>/dev/null; then
        echo "✅ Python调度器运行中 (PID: $PID)"
        echo "📊 调度器状态:"
        python3 auto_update_scheduler.py status 2>/dev/null || echo "  获取状态失败"
    else
        echo "❌ Python调度器未运行 (PID文件存在但进程不存在)"
    fi
else
    echo "⚪ Python调度器未启动"
fi

echo ""

# 检查最近的更新日志
echo "📄 最近的更新记录:"
if [[ -f "auto_update.log" ]]; then
    tail -5 auto_update.log | sed 's/^/  /'
elif [[ -f "auto_update_cron.log" ]]; then
    tail -5 auto_update_cron.log | sed 's/^/  /'
else
    echo "  未找到更新日志"
fi

echo ""

# 检查数据新鲜度
echo "🔍 数据新鲜度检查:"
if [[ -f "earnings_cache.db" ]]; then
    DB_TIME=$(stat -f %m earnings_cache.db 2>/dev/null || stat -c %Y earnings_cache.db 2>/dev/null || echo 0)
    CURRENT_TIME=$(date +%s)
    AGE_HOURS=$(((CURRENT_TIME - DB_TIME) / 3600))
    
    if [[ $AGE_HOURS -lt 24 ]]; then
        echo "  ✅ 数据较新 ($AGE_HOURS 小时前)"
    elif [[ $AGE_HOURS -lt 48 ]]; then
        echo "  ⚠️ 数据稍旧 ($AGE_HOURS 小时前)"
    else
        echo "  ❌ 数据过期 ($AGE_HOURS 小时前)"
    fi
else
    echo "  ❌ 数据库文件不存在"
fi

echo ""

# 检查服务器状态
echo "🌐 服务器状态:"
SERVER_PORTS=(5000 5001 5002)
for port in "${SERVER_PORTS[@]}"; do
    if lsof -ti:$port >/dev/null 2>&1; then
        echo "  ✅ 端口 $port 正在运行"
    else
        echo "  ⚪ 端口 $port 未运行"
    fi
done
EOF

chmod +x "$PROJECT_DIR/check_update_status.sh"

echo ""
echo "🎉 自动更新系统设置完成!"
echo ""
echo "📋 可用脚本:"
echo "  check_update_status.sh  - 检查系统状态"

if [[ $choice -eq 1 ]]; then
    echo "  start_auto_updater.sh   - 启动自动更新调度器"
    echo "  stop_auto_updater.sh    - 停止自动更新调度器"
fi

if [[ $choice -eq 3 ]]; then
    echo "  manual_update.sh        - 手动执行更新"
fi

echo ""
echo "📖 说明文档已在README.md中更新"
echo "🔧 如需修改更新时间，请编辑 auto_update_scheduler.py"
echo ""
echo "立即测试更新功能？"
read -p "执行一次测试更新? (y/N): " test_update

if [[ "$test_update" =~ ^[Yy]$ ]]; then
    echo ""
    echo "🧪 执行测试更新..."
    python3 auto_update_scheduler.py update
    
    echo ""
    echo "📊 检查更新状态..."
    ./check_update_status.sh
fi

echo ""
echo "✅ 设置完成! 🎉"