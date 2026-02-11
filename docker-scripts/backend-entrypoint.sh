#!/bin/bash
set -e

echo "============================================"
echo "🚀 启动DeepTutor后端服务"
echo "============================================"

# 设置环境变量
export BACKEND_PORT=${BACKEND_PORT:-8001}
export PYTHONPATH="/app"

echo "📌 后端端口: ${BACKEND_PORT}"

# 安装系统依赖
echo "🔧 安装系统依赖..."
apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装Rust（某些Python包需要）
if ! command -v rustc &> /dev/null; then
    echo "🔧 安装Rust环境..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# 升级pip并安装依赖
echo "🐍 安装Python依赖..."
pip install --upgrade pip
pip install -r /app/requirements.txt

# 初始化用户目录
echo "📁 初始化用户数据目录..."
python -c "
from pathlib import Path
from src.services.setup import init_user_directories
try:
    init_user_directories(Path('/app'))
    print('✅ 用户目录初始化完成')
except Exception as e:
    print(f'⚠️ 目录初始化跳过: {e}')
"

# 检查必要环境变量
echo "🔍 检查配置..."
if [ -z "$LLM_API_KEY" ]; then
    echo "⚠️ 警告: 未设置LLM_API_KEY"
    echo "   请在.env文件中配置LLM相关参数"
fi

if [ -z "$LLM_MODEL" ]; then
    echo "⚠️ 警告: 未设置LLM_MODEL"
    echo "   请在.env文件中配置LLM模型"
fi

echo "============================================"
echo "🚀 启动FastAPI服务..."
echo "============================================"

# 启动后端服务
exec python -m uvicorn src.api.main:app --host 0.0.0.0 --port ${BACKEND_PORT}