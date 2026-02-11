#!/bin/bash
set -e

# 进入前端目录
cd /app/web

# 设置基础环境变量
export FRONTEND_PORT=${FRONTEND_PORT:-3782}
export BACKEND_PORT=${BACKEND_PORT:-8001}
export NODE_ENV=production

echo "============================================"
echo "🚀 启动DeepTutor前端服务"
echo "============================================"
echo "📌 前端端口: ${FRONTEND_PORT}"
echo "📌 后端地址: ${NEXT_PUBLIC_API_BASE:-http://localhost:${BACKEND_PORT}}"

# 安装依赖（如果node_modules不存在）
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    # 尝试使用npm ci，如果失败则使用npm install
    npm ci --include=dev --legacy-peer-deps 2>/dev/null || npm install --include=dev --legacy-peer-deps
fi

# 确保node_modules/.bin在PATH中
export PATH="/app/web/node_modules/.bin:$PATH"

# 验证next命令是否可用
type next >/dev/null 2>&1 || {
    echo "❌ next命令不可用，重新安装依赖..."
    npm install --include=dev --legacy-peer-deps
    export PATH="/app/web/node_modules/.bin:$PATH"
    type next >/dev/null 2>&1 || {
        echo "❌ next命令仍然不可用，退出"
        exit 1
    }
}

echo "✅ next命令可用"

# 进入前端目录
cd /app/web

# 安装依赖（如果node_modules不存在）
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm ci --include=dev --legacy-peer-deps
fi

# 构建应用（检查必要的构建文件）
BUILD_COMPLETE=false
if [ -d ".next" ]; then
    if [ -f ".next/BUILD_ID" ] && [ -f ".next/routes-manifest.json" ]; then
        echo "✅ 检测到完整的构建文件"
        BUILD_COMPLETE=true
    else
        echo "⚠️ 检测到不完整的构建文件，重新构建..."
        rm -rf .next
    fi
fi

if [ "$BUILD_COMPLETE" = false ]; then
    echo "🔨 构建前端应用..."
    npm run build
    
    # 验证构建是否成功
    if [ ! -f ".next/BUILD_ID" ] || [ ! -f ".next/routes-manifest.json" ]; then
        echo "❌ 构建失败，缺少必要的构建文件"
        exit 1
    fi
    echo "✅ 构建完成"
fi

# 创建环境配置文件（如果不存在）
if [ ! -f ".env.local" ]; then
    cat > .env.local << EOF
NEXT_PUBLIC_API_BASE=http://localhost:${BACKEND_PORT}
EOF
    echo "✅ 创建 .env.local 配置文件"
else
    echo "✅ 使用现有的 .env.local 配置文件"
fi

echo "============================================"
echo "🚀 启动Next.js服务..."
echo "============================================"

# 启动前端服务
if [ "$NODE_ENV" = "development" ]; then
    echo "🚀 以开发模式启动Next.js..."
    exec npm run dev -- -H 0.0.0.0 -p ${FRONTEND_PORT}
else
    echo "🚀 以生产模式启动Next.js..."
    exec npm run start -- -H 0.0.0.0 -p ${FRONTEND_PORT}
fi