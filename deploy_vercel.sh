#!/bin/bash
# Vercel部署脚本

echo "🚀 开始Vercel部署..."

# 检查是否已安装Vercel CLI
if ! command -v vercel &> /dev/null; then
    echo "📦 安装Vercel CLI..."
    npm install -g vercel
fi

# 登录Vercel
echo "🔐 登录Vercel..."
vercel login

# 设置项目名称（避免冲突）
PROJECT_NAME="actor-face-recognition-$(date +%s)"
echo "📝 使用项目名称: $PROJECT_NAME"

# 部署到生产环境
echo "🌐 部署到生产环境..."
vercel --prod --name $PROJECT_NAME

echo "✅ 部署完成！"
echo "🔗 请查看Vercel控制台获取访问地址"
