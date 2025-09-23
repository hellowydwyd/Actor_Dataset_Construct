# Conda环境设置指南

## 🎉 环境创建成功！

你的 `actor_face_db` conda环境已经成功创建并配置完成。

## 📦 已安装的核心组件

### ✅ 必需依赖
- **Python 3.9** - 基础运行环境
- **requests** - 网络请求库
- **Pillow** - 图像处理
- **OpenCV** - 计算机视觉
- **NumPy** - 数值计算
- **Flask** - Web框架
- **PyYAML** - 配置文件解析
- **Loguru** - 日志系统

### ✅ 机器学习和人脸识别
- **InsightFace** - 人脸识别核心库
- **ONNX Runtime** - 深度学习推理引擎
- **scikit-learn** - 机器学习工具包
- **Faiss** - 向量数据库

### ⚠️ 可选组件
- **ChromaDB** - 另一个向量数据库选项（未安装，如需要可手动安装）

## 🚀 使用方法

### 1. 激活环境
```bash
conda activate actor_face_db
```

### 2. 配置API密钥
编辑配置文件设置TMDB API密钥：
```bash
# 方法1: 编辑配置文件
nano config/config.yaml
# 在tmdb.api_key处填入你的密钥

# 方法2: 创建环境变量文件
echo "TMDB_API_KEY=你的密钥" > .env
```

### 3. 测试系统
```bash
python test_system.py
```

### 4. 运行示例
```bash
# 构建数据集
python run.py build --movie "复仇者联盟"

# 启动Web界面
python run.py web

# 人脸搜索
python run.py search --image "photo.jpg"
```

## 🔧 环境管理

### 查看已安装的包
```bash
conda list
```

### 安装额外的包
```bash
# 安装ChromaDB（可选）
pip install chromadb==0.4.15

# 安装Selenium（用于高级网页爬取）
pip install selenium==4.15.2
```

### 更新包
```bash
pip install --upgrade insightface
```

### 导出环境配置
```bash
# 导出conda环境
conda env export > environment_backup.yml

# 导出pip需求
pip freeze > requirements_backup.txt
```

## 🎯 下一步操作

1. **获取TMDB API密钥**
   - 访问 https://www.themoviedb.org/settings/api
   - 注册账号并申请API密钥
   - 在配置文件中设置密钥

2. **运行完整测试**
   ```bash
   python test_system.py
   ```

3. **体验Web界面**
   ```bash
   python run.py web
   # 然后访问 http://localhost:5000
   ```

4. **构建你的第一个数据集**
   ```bash
   python run.py build --movie "你喜欢的电影名称"
   ```

## 🐛 故障排除

### InsightFace模型下载
- 首次运行会自动下载模型文件（~280MB）
- 如果下载失败，可以手动下载并放置在 `~/.insightface/models/` 目录

### 内存不足
- 如果遇到内存问题，可以调整配置文件中的 `max_images_per_actor` 参数

### GPU加速（可选）
如果你有NVIDIA GPU，可以安装CUDA版本：
```bash
pip uninstall onnxruntime
pip install onnxruntime-gpu
```

## 📝 环境信息

- **环境名称**: `actor_face_db`
- **Python版本**: 3.9.23
- **环境路径**: `/data/users/wyd/conda/envs/actor_face_db`
- **包管理器**: conda + pip

## 🎉 恭喜！

你的电影演员人脸数据库构建系统环境已经准备就绪！现在可以开始构建你的演员人脸数据库了。
