# 🎬 电影演员人脸数据库构建系统 (Actor Dataset Construct)

> 🇨🇳 A comprehensive movie actor face recognition database construction system | 基于AI的电影演员人脸识别数据库构建系统

## 🌟 项目简介

这是一个自动化的电影演员人脸数据库构建系统，能够：

- 🎭 **智能演员识别**: 基于TMDB API获取电影演员信息
- 📸 **自动图片收集**: 多源爬取演员高质量人脸图片  
- 🧠 **AI人脸识别**: 使用InsightFace提取高精度人脸特征
- 🔍 **向量化检索**: 构建可搜索的Faiss向量数据库
- 🎥 **实时视频识别**: 支持视频中人脸实时识别和标注
- 🌐 **现代化界面**: 响应式Web管理界面
- 🇨🇳 **中文支持**: 完美支持中文演员名字显示

## 🏗️ 系统架构

```
Actor_dataset_contruct/
├── 📁 src/                    # 核心源代码
│   ├── 🔌 api/               # TMDB API接口模块
│   ├── 🕷️ crawler/           # 图片爬取模块
│   ├── 👤 face_recognition/   # 人脸识别和特征提取
│   ├── 🗄️ database/          # 向量数据库管理
│   ├── 🎥 video_recognition/ # 视频识别处理
│   └── 🛠️ utils/             # 工具函数
├── 📁 web/                   # Web界面
├── 📁 config/                # 配置文件
├── 📁 data/                  # 数据存储
│   ├── 🖼️ images/           # 按电影分类的图片
│   ├── 🧮 embeddings/       # 人脸向量数据
│   └── 📊 metadata/         # 元数据信息
├── 📁 scripts/              # 工具脚本
├── 📁 examples/             # 使用示例
├── 📁 tests/                # 测试文件
└── 📁 docs/                 # 项目文档
```

## ✨ 核心功能

### 🎬 电影数据集构建
- 从TMDB获取电影演员信息
- 智能角色颜色分配和标注样式
- 按电影名称组织图片存储结构

### 🖼️ 图片处理流程  
- 多源图片收集 (TMDB + 百度搜索)
- 图片质量评估和筛选
- 人脸检测和对齐
- 重复图片智能去重

### 🧠 AI人脸识别
- InsightFace高精度人脸识别
- 512维特征向量提取
- Faiss向量数据库存储
- 相似度搜索和匹配

### 🎥 视频识别功能
- 实时视频人脸识别
- 中文演员名字标注
- 多种标注框样式
- 批量视频处理

### 🌐 Web管理界面
- 响应式现代化设计
- 实时进度显示
- 数据库可视化管理
- 多格式文件预览

## 🚀 快速开始

### 方法1: Cloud Studio 一键部署 (推荐)

**步骤**：
1. 访问：https://cloudstudio.net/
2. 登录 → 创建工作空间 → 从Git导入
3. 仓库地址：`https://github.com/hellowydwyd/Actor-Dataset-Construct`
4. 选择Python 3.9环境
5. 在终端执行：
```bash
pip install -r requirements-china.txt
python start_cloudstudio.py
```
6. 点击"预览"按钮访问公网应用

### 方法2: 本地安装运行

#### 1. 克隆项目
```bash
git clone https://github.com/hellowydwyd/Actor-Dataset-Construct.git
cd Actor-Dataset-Construct
```

#### 2. 安装依赖
```bash
# 中国用户推荐
pip install -r requirements-china.txt

# 国际用户
pip install -r requirements.txt
```

#### 3. 配置API密钥
```bash
# 复制配置文件
cp config/env_example .env

# 编辑.env文件，添加TMDB API密钥
TMDB_API_KEY=your_api_key_here
```

获取TMDB API密钥：访问 [TMDB API](https://www.themoviedb.org/settings/api)

#### 4. 启动应用
```bash
# Web界面 (推荐)
python main.py web --host 0.0.0.0 --port 5000

# 或使用Cloud Studio启动脚本
python start_cloudstudio.py
```

## 💻 使用方法

### 🎭 构建演员数据集
```bash
# Web界面 (推荐)
访问 http://localhost:5000 → 数据集构建

# 命令行
python main.py build --movie "肖申克的救赎" --year 1994
python main.py build --movie "流浪地球2" --max-actors 15
```

### 🔍 人脸识别搜索
```bash
# Web界面人脸搜索
上传图片 → 自动识别相似演员

# 命令行搜索
python main.py search --image "path/to/photo.jpg"
```

### 🎥 视频人脸识别
```bash
# Web界面视频处理
上传视频 → 选择电影范围 → 实时人脸标注
```

## 🛠️ 技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **后端** | Python Flask | 3.0.0 | Web服务框架 |
| **AI模型** | InsightFace | 0.7.3 | 人脸识别引擎 |
| **图像处理** | OpenCV | 4.8.1 | 计算机视觉 |
| **向量数据库** | Faiss | 1.7.4 | 相似度搜索 |
| **前端** | Bootstrap 5 | 5.1.3 | 响应式界面 |
| **API接口** | TMDB API | - | 电影数据源 |

## 📊 性能特性

- ⚡ **高速识别**: 单张图片 < 1秒
- 🎯 **高精度**: 人脸识别准确率 > 95%
- 📈 **可扩展**: 支持数万级演员数据库
- 🌍 **跨平台**: Windows/Linux/macOS
- 📱 **响应式**: 支持移动端访问

## 🎯 系统要求

- Python 3.8+
- 2GB+ RAM (用于AI模型)
- 5GB+ 存储空间
- 网络连接 (TMDB API访问)

## 📖 文档

- 🔧 [中文渲染方案](docs/中文文字渲染解决方案.md)
- 📁 [目录结构说明](docs/图片目录结构迁移说明.md)
- ⚡ [视频预览优化](docs/视频预览功能优化说明.md)

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License
