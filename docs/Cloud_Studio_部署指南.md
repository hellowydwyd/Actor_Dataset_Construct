# 腾讯云 Cloud Studio 部署指南

## 🌟 为什么选择 Cloud Studio

- ✅ **完全免费**: 无时间限制，无隐藏费用
- ✅ **即开即用**: 浏览器直接访问，零配置
- ✅ **AI友好**: 2GB内存足够运行InsightFace
- ✅ **公网访问**: 自动分配公网地址
- ✅ **中国网络**: 国内访问速度快

## 🚀 详细部署步骤

### 步骤1: 访问 Cloud Studio
1. 打开浏览器访问：https://cloudstudio.net/
2. 使用微信扫码或QQ登录

### 步骤2: 创建工作空间
1. 点击 **"创建工作空间"**
2. 选择 **"从Git仓库导入"**
3. 输入仓库地址：`https://github.com/hellowydwyd/Actor-Dataset-Construct`
4. 选择配置：
   - **模板**: `Python 3.9`
   - **规格**: `基础版 (1核2G)` - 免费
   - **存储**: `10GB` - 免费
5. 点击 **"创建"**

### 步骤3: 等待环境初始化
- 系统会自动克隆您的GitHub仓库
- 预装Python 3.9环境
- 大约需要2-3分钟

### 步骤4: 安装项目依赖
在Cloud Studio终端中执行：

```bash
# 使用国内镜像源安装依赖 (推荐)
pip install -r requirements-china.txt

# 或者使用标准源
pip install -r requirements.txt
```

### 步骤5: 配置TMDB API密钥
```bash
# 创建环境变量文件
cp config/env_example .env

# 编辑环境变量文件
nano .env
```

在.env文件中添加：
```bash
TMDB_API_KEY=your_tmdb_api_key_here
```

**获取TMDB API密钥**:
1. 访问：https://www.themoviedb.org/settings/api
2. 注册账号
3. 申请API密钥
4. 复制到.env文件中

### 步骤6: 启动应用
```bash
# 启动Web应用
python main.py web --host 0.0.0.0 --port 8080

# 或者使用快速启动
python run.py web
```

### 步骤7: 访问应用
1. Cloud Studio会自动检测到端口8080
2. 点击 **"预览"** 按钮
3. 选择 **"在新标签页打开"**
4. 🎉 您的应用现在可以通过公网访问！

## 🔧 高级配置

### 自定义端口配置
如果需要使用特定端口：

```bash
# 在Cloud Studio中启动应用
python main.py web --host 0.0.0.0 --port 8080
```

### 环境变量配置
创建`.env`文件：
```bash
# TMDB API配置
TMDB_API_KEY=your_api_key_here

# Web配置
WEB_HOST=0.0.0.0
WEB_PORT=8080
WEB_DEBUG=false

# 数据路径 (Cloud Studio环境)
IMAGES_DIR=./data/images
EMBEDDINGS_DIR=./data/embeddings
METADATA_DIR=./data/metadata
```

### 数据持久化
Cloud Studio会自动保存您的数据，但建议：

1. **定期备份重要数据**:
```bash
# 下载数据库文件
zip -r database_backup.zip data/
```

2. **提交重要更改**:
```bash
git add .
git commit -m "更新数据集"
git push origin main
```

## 🌐 公网访问特性

### 自动公网地址
- Cloud Studio会为您的应用分配类似 `xxx.cloudstudio.net` 的公网地址
- 支持HTTPS访问
- 全球可访问

### 域名配置 (可选)
如果需要自定义域名：
1. 在Cloud Studio设置中配置
2. 或使用反向代理服务

## 🔍 故障排除

### 常见问题

#### 1. 依赖安装失败
```bash
# 清理pip缓存
pip cache purge

# 使用国内镜像源重新安装
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements-china.txt
```

#### 2. 内存不足
```bash
# 减少并发处理
# 编辑 config/config.yaml
crawler:
  concurrent_downloads: 2  # 降低并发数
  max_images_per_actor: 10  # 减少图片数量
```

#### 3. TMDB API访问慢
```bash
# 在config/config.yaml中增加超时时间
tmdb:
  timeout: 30
  retry_count: 3
```

#### 4. 端口访问问题
- 确保使用 `--host 0.0.0.0`
- 端口推荐使用 8080 或 3000
- 检查Cloud Studio的端口转发设置

### 性能优化建议

1. **内存优化**:
```yaml
# 在config/config.yaml中配置
face_recognition:
  model_cache: true
  lazy_loading: true
```

2. **存储优化**:
```bash
# 定期清理临时文件
rm -rf temp/*
```

3. **网络优化**:
```yaml
# 使用较小的图片尺寸
crawler:
  max_images_per_actor: 10
  image_quality_threshold: 0.6
```

## 🎯 完整部署命令

一键复制执行：
```bash
# 1. 安装依赖 (选择其一)
pip install -r requirements-china.txt  # 推荐：国内镜像源
# pip install -r requirements.txt      # 备选：标准源

# 2. 配置API密钥
cp config/env_example .env
nano .env  # 添加 TMDB_API_KEY=your_key_here

# 3. 启动应用
python main.py web --host 0.0.0.0 --port 8080

# 4. 点击Cloud Studio的"预览"按钮访问应用
```

## 📱 访问应用功能

部署成功后，您可以通过公网地址使用：
- 🎬 **电影数据集构建**: 输入电影名自动构建演员数据库
- 👤 **人脸识别搜索**: 上传照片识别相似演员
- 🎥 **视频人脸标注**: 上传视频实时识别演员
- 📊 **数据库管理**: 查看和管理已构建的数据

## 🔐 安全注意事项

1. **API密钥保护**: 不要在公开场合分享您的TMDB API密钥
2. **数据隐私**: 上传的图片和视频会临时存储在服务器
3. **访问控制**: Cloud Studio环境默认是私有的，只有您可以访问

## 💡 使用技巧

1. **快速测试**: 先用"肖申克的救赎"等知名电影测试
2. **分批构建**: 大型电影建议分批处理演员
3. **定期保存**: 重要数据及时提交到GitHub
4. **监控资源**: 注意内存和存储使用情况

部署完成后，您就拥有了一个运行在公网的AI人脸识别应用！🎉
