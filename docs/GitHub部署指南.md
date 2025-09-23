# GitHub 部署指南

## 重要说明

**GitHub Pages 的局限性**: GitHub Pages 只支持静态网站，不能运行 Python Flask 后端服务。您的项目包含复杂的后端逻辑（人脸识别、视频处理、向量数据库等），需要服务器环境支持。

## 部署方案对比

| 方案 | 适用性 | 成本 | 难度 | 推荐度 |
|------|--------|------|------|--------|
| GitHub Pages | ❌ 不适用 | 免费 | 简单 | ⭐ |
| GitHub Codespaces | ✅ 适用 | 有限免费 | 中等 | ⭐⭐⭐ |
| Railway | ✅ 适用 | 有限免费 | 简单 | ⭐⭐⭐⭐ |
| Render | ✅ 适用 | 有限免费 | 简单 | ⭐⭐⭐⭐ |
| Heroku | ✅ 适用 | 付费 | 中等 | ⭐⭐⭐ |
| 自建VPS | ✅ 适用 | 低成本 | 复杂 | ⭐⭐⭐⭐⭐ |

## 推荐方案

### 方案1: GitHub Codespaces (推荐新手)

**优势**: 
- 与GitHub深度集成
- 每月60小时免费
- 开发环境即部署环境
- 支持端口转发

**步骤**:

1. **推送代码到GitHub**:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/your-username/Actor_dataset_construct.git
git push -u origin main
```

2. **创建Codespace**:
   - 进入GitHub仓库页面
   - 点击绿色"Code"按钮
   - 选择"Codespaces"标签
   - 点击"Create codespace on main"

3. **配置环境**:
创建 `.devcontainer/devcontainer.json`:
```json
{
    "name": "Actor Dataset Construct",
    "image": "mcr.microsoft.com/devcontainers/python:3.9",
    "features": {
        "ghcr.io/devcontainers/features/node:1": {}
    },
    "forwardPorts": [5000],
    "postCreateCommand": "pip install -r requirements.txt",
    "customizations": {
        "vscode": {
            "extensions": [
                "ms-python.python"
            ]
        }
    }
}
```

4. **运行应用**:
```bash
python main.py
```

### 方案2: Railway (推荐生产环境)

**优势**:
- 免费套餐支持
- 自动部署
- 支持数据库
- 简单配置

**步骤**:

1. **创建 `railway.json`**:
```json
{
    "build": {
        "builder": "NIXPACKS"
    },
    "deploy": {
        "startCommand": "python main.py",
        "healthcheckPath": "/",
        "healthcheckTimeout": 300
    }
}
```

2. **创建 `Procfile`**:
```
web: python main.py
```

3. **修改配置文件** (`config/config.yaml`):
```yaml
web:
  host: "0.0.0.0"
  port: ${PORT:-5000}
  debug: false

storage:
  images_dir: "./data/images"
  embeddings_dir: "./data/embeddings"
  metadata_dir: "./data/metadata"
  database_file: "./data/metadata/actors.db"
```

4. **部署到Railway**:
   - 访问 [railway.app](https://railway.app)
   - 连接GitHub账户
   - 选择仓库进行部署
   - 配置环境变量

### 方案3: Render (免费替代方案)

**优势**:
- 完全免费
- 自动SSL证书
- 持续部署

**步骤**:

1. **创建 `render.yaml`**:
```yaml
services:
  - type: web
    name: actor-dataset-construct
    runtime: python3
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: PORT
        value: 10000
```

2. **修改主程序**:
```python
# 在 main.py 中添加
import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app = create_app()
    app.run(host='0.0.0.0', port=port, debug=False)
```

## 项目准备工作

### 1. 创建部署配置文件

创建 `deploy/` 目录并添加配置文件：

```bash
mkdir deploy
```

**`deploy/requirements-prod.txt`**:
```txt
# 生产环境依赖 - 移除开发工具
requests==2.31.0
beautifulsoup4==4.12.2
pillow==10.0.1
numpy==1.24.3
opencv-python-headless==4.8.1.78  # 无GUI版本
insightface==0.7.3
onnxruntime==1.16.3
scikit-learn==1.3.0
faiss-cpu==1.7.4
flask==3.0.0
flask-cors==4.0.0
tmdbv3api==1.9.0
wget==3.2
tqdm==4.66.1
python-dotenv==1.0.0
pyyaml==6.0.1
loguru==0.7.2
```

**`deploy/docker/Dockerfile`**:
```dockerfile
FROM python:3.9-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建数据目录
RUN mkdir -p data/images data/embeddings data/metadata logs temp

# 设置环境变量
ENV PYTHONPATH=/app
ENV FLASK_APP=main.py
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["python", "main.py"]
```

### 2. 环境变量配置

**`.env.example`**:
```env
# TMDB API配置
TMDB_API_KEY=your_tmdb_api_key_here

# Web配置
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=false

# 数据路径
IMAGES_DIR=./data/images
EMBEDDINGS_DIR=./data/embeddings
METADATA_DIR=./data/metadata

# 安全密钥
SECRET_KEY=your-secret-key-here
```

### 3. 修改配置加载器

**`src/utils/config_loader.py`** - 添加环境变量支持:
```python
import os
from pathlib import Path

class ConfigLoader:
    def __init__(self):
        # 优先使用环境变量
        self.tmdb_api_key = os.getenv('TMDB_API_KEY', 'default_key')
        self.web_host = os.getenv('WEB_HOST', '0.0.0.0')
        self.web_port = int(os.getenv('WEB_PORT', 5000))
        self.web_debug = os.getenv('WEB_DEBUG', 'false').lower() == 'true'
        
    def get_web_config(self):
        return {
            'host': self.web_host,
            'port': self.web_port,
            'debug': self.web_debug
        }
```

### 4. 数据持久化方案

对于生产环境，需要考虑数据存储：

**选项1: 云存储 (推荐)**
```python
# 使用 AWS S3 或类似服务
import boto3

class CloudStorage:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
    
    def upload_image(self, local_path, remote_path):
        self.s3.upload_file(local_path, self.bucket_name, remote_path)
```

**选项2: 本地存储 + 定期备份**
```bash
# 使用 cron 定期备份
0 2 * * * tar -czf /backup/data-$(date +\%Y\%m\%d).tar.gz /app/data/
```

## 部署流程

### 完整部署流程 (以Railway为例)

1. **准备代码**:
```bash
# 克隆或创建项目
git clone your-repo-url
cd Actor_dataset_construct

# 创建生产环境配置
cp config/config.yaml config/config.prod.yaml
# 编辑配置文件，调整为生产环境设置
```

2. **推送到GitHub**:
```bash
git add .
git commit -m "Prepare for deployment"
git push origin main
```

3. **部署到Railway**:
   - 登录 [railway.app](https://railway.app)
   - 点击 "New Project"
   - 选择 "Deploy from GitHub repo"
   - 选择您的仓库
   - 配置环境变量
   - 等待部署完成

4. **配置域名** (可选):
   - 在Railway控制台配置自定义域名
   - 或使用提供的 `.railway.app` 子域名

## 静态版本方案 (仅用于演示)

如果您只想在GitHub Pages展示项目，可以创建一个静态演示版本：

### 创建静态演示页面

**`docs/index.html`**:
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>电影演员人脸数据库构建系统 - 项目展示</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
</head>
<body>
    <div class="container my-5">
        <div class="row">
            <div class="col-lg-8 mx-auto">
                <h1 class="text-center mb-4">🎬 电影演员人脸数据库构建系统</h1>
                
                <div class="alert alert-info">
                    <h5><i class="bi bi-info-circle"></i> 项目展示</h5>
                    <p>这是一个静态展示页面。完整的应用包含Python后端服务，需要在支持服务器端的环境中运行。</p>
                </div>
                
                <h2>功能特性</h2>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5><i class="bi bi-search"></i> 演员搜索</h5>
                                <p>基于TMDB API搜索电影演员信息</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5><i class="bi bi-image"></i> 图片收集</h5>
                                <p>自动收集高质量演员图片</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5><i class="bi bi-cpu"></i> 人脸识别</h5>
                                <p>基于InsightFace的高精度人脸识别</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5><i class="bi bi-play-circle"></i> 视频处理</h5>
                                <p>实时视频人脸识别和标注</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <h2>技术栈</h2>
                <ul>
                    <li><strong>后端</strong>: Python Flask</li>
                    <li><strong>前端</strong>: Bootstrap 5 + JavaScript</li>
                    <li><strong>人脸识别</strong>: InsightFace</li>
                    <li><strong>向量数据库</strong>: Faiss</li>
                    <li><strong>图像处理</strong>: OpenCV</li>
                </ul>
                
                <div class="text-center mt-4">
                    <a href="https://github.com/your-username/Actor_dataset_construct" class="btn btn-primary">
                        <i class="bi bi-github"></i> 查看源码
                    </a>
                    <a href="#" class="btn btn-success">
                        <i class="bi bi-play"></i> 在线演示 (需要服务器环境)
                    </a>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
```

**启用GitHub Pages**:
1. 进入仓库设置
2. 找到"Pages"选项
3. 选择源为"Deploy from a branch"
4. 选择分支和`/docs`文件夹
5. 保存设置

## 最佳实践建议

### 1. 开发环境
- 使用GitHub Codespaces进行开发和测试
- 配置自动化测试和代码质量检查

### 2. 生产环境
- 使用Railway或Render进行生产部署
- 配置监控和日志记录
- 设置自动备份

### 3. 安全考虑
- 使用环境变量管理敏感信息
- 配置HTTPS和安全头
- 限制API访问频率

### 4. 性能优化
- 使用CDN加速静态资源
- 配置缓存策略
- 优化图片和视频处理性能

## 成本估算

| 服务 | 免费额度 | 付费价格 | 适用场景 |
|------|----------|----------|----------|
| GitHub Codespaces | 60小时/月 | $0.18/小时 | 开发测试 |
| Railway | $5月度额度 | $0.01/GB-hour | 中小型应用 |
| Render | 750小时/月 | $7/月起 | 个人项目 |
| Heroku | 无免费额度 | $7/月起 | 企业应用 |

**推荐配置**: GitHub Codespaces (开发) + Railway (生产)

这样可以在保持低成本的同时获得良好的开发和部署体验。

