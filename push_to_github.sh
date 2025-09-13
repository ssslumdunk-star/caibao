#!/bin/bash

echo "🚀 推送 CaiBao 项目到 GitHub"
echo "=================================="

# 检查当前目录
if [[ ! -f "README.md" ]] || [[ ! -f "cached_earnings_server.py" ]]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 显示当前状态
echo "📊 当前Git状态:"
git status --short

echo ""
echo "🔗 远程仓库:"
git remote -v

echo ""
echo "📝 最新提交:"
git log --oneline -1

echo ""
echo "⚠️  注意: 推送需要GitHub身份验证"
echo "   - 如果提示输入密码，请使用GitHub Personal Access Token"
echo "   - Token获取地址: https://github.com/settings/tokens"
echo ""

# 提交任何未提交的更改
if git diff-index --quiet HEAD --; then
    echo "✅ 工作区干净，准备推送..."
else
    echo "📝 发现未提交的更改，先提交..."
    git add .
    git commit -m "Update: Final cleanup before GitHub push"
fi

echo ""
echo "🚀 开始推送到 GitHub..."
echo "目标仓库: https://github.com/ssslumdunk-star/caibao.git"
echo ""

# 尝试推送
if git push -u origin main; then
    echo ""
    echo "🎉 成功推送到GitHub!"
    echo "📍 项目地址: https://github.com/ssslumdunk-star/caibao"
    echo ""
    echo "🔗 接下来你可以:"
    echo "   - 访问GitHub仓库查看代码"
    echo "   - 编辑README.md添加个人信息"
    echo "   - 设置仓库描述和主题标签"
    echo "   - 配置GitHub Pages (如果需要)"
    echo ""
else
    echo ""
    echo "❌ 推送失败，可能的解决方案:"
    echo ""
    echo "1. 使用Personal Access Token:"
    echo "   git remote set-url origin https://ssslumdunk-star@github.com/ssslumdunk-star/caibao.git"
    echo "   git push -u origin main"
    echo ""
    echo "2. 使用SSH (需要配置SSH密钥):"
    echo "   git remote set-url origin git@github.com:ssslumdunk-star/caibao.git"
    echo "   git push -u origin main"
    echo ""
    echo "3. 使用GitHub CLI:"
    echo "   brew install gh"
    echo "   gh auth login"
    echo "   git push -u origin main"
    echo ""
fi

echo "📦 项目特色总结:"
echo "  🤖 全自动化更新系统"
echo "  📊 智能价格验证机制"  
echo "  🎯 真实分析师评论"
echo "  📦 一键部署能力"
echo "  🔧 企业级监控体系"
echo ""
echo "✨ 感谢使用 CaiBao 财报日历系统!"