FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    libfontconfig1 \
    libgtk-3-0 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建数据目录
RUN mkdir -p data/images data/embeddings data/metadata logs temp && \
    chmod -R 755 data logs temp

# 设置环境变量
ENV PYTHONPATH=/app
ENV FLASK_APP=main.py
ENV FLASK_ENV=production
ENV WEB_HOST=0.0.0.0
ENV WEB_PORT=5000
ENV WEB_DEBUG=false

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# 暴露端口
EXPOSE 5000

# 启动应用
CMD ["python", "main.py"]

