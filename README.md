# 电影演员人脸数据库构建系统

## 项目简介

这是一个自动化的电影演员人脸数据库构建系统，能够：
- 根据电影名称获取演员信息
- 自动收集演员高质量人脸图片
- 使用InsightFace提取人脸特征向量
- 构建可搜索的人脸向量数据库

## 系统架构

```
Actor_dataset_contruct/
├── src/
│   ├── api/           # TMDB API接口模块
│   ├── crawler/       # 图片爬取模块
│   ├── face_recognition/  # 人脸识别和特征提取
│   ├── database/      # 向量数据库管理
│   └── utils/         # 工具函数
├── data/
│   ├── images/        # 原始图片存储
│   ├── embeddings/    # 人脸向量数据
│   └── metadata/      # 元数据信息
├── config/            # 配置文件
├── web/              # Web管理界面
└── tests/            # 测试文件
```

## 核心功能

1. **电影信息获取**：使用TMDB API获取电影演员列表
2. **图片收集**：多源爬取演员高质量图片
3. **人脸处理**：InsightFace进行人脸检测和特征提取
4. **向量存储**：Faiss/ChromaDB构建可搜索的向量数据库
5. **质量控制**：图片质量评估和去重机制
6. **Web界面**：可视化管理和查询界面

## 快速开始

### 1. 自动安装
```bash
# 克隆或下载项目后，运行自动安装脚本
python install.py
```

### 2. 配置API密钥
获取TMDB API密钥：
1. 访问 [TMDB API](https://www.themoviedb.org/settings/api)
2. 注册账号并申请API密钥
3. 编辑 `.env` 文件或 `config/config.yaml`，设置：
```bash
TMDB_API_KEY=你的API密钥
```

### 3. 快速启动
```bash
# 使用快速启动脚本 (推荐)
python run.py build --movie "复仇者联盟"
python run.py web  # 启动Web界面

# 或直接使用主程序
python main.py build --movie "复仇者联盟" --year 2012
python main.py web
```

### 4. 系统测试
```bash
# 测试系统组件
python test_system.py

# 运行使用示例
python example.py
```

## 详细使用说明

### 命令行界面

#### 构建数据集
```bash
# 基本用法
python main.py build --movie "电影名称"

# 指定年份和演员数量
python main.py build --movie "复仇者联盟" --year 2012 --max-actors 15

# 使用快速启动脚本
python run.py build -m "钢铁侠" -y 2008
```

#### 人脸搜索
```bash
# 搜索相似人脸
python main.py search --image "path/to/photo.jpg" --top-k 10

# 使用快速启动脚本
python run.py search -i "photo.jpg" -k 5
```

#### 查看数据库信息
```bash
python main.py info
python run.py info
```

### Web界面
启动Web服务：
```bash
python main.py web --host 0.0.0.0 --port 5000
python run.py web  # 使用默认配置
```

然后在浏览器中访问 `http://localhost:5000`

Web界面功能：
- 🔍 电影搜索和演员信息获取
- 🏗️ 可视化数据集构建过程
- 📸 人脸相似度搜索
- 📊 数据库统计和管理

### 高级配置

编辑 `config/config.yaml` 自定义系统行为：

```yaml
# 人脸识别配置
face_recognition:
  model_name: "buffalo_l"  # 可选: buffalo_s, buffalo_m, buffalo_l
  detection_threshold: 0.6
  
# 爬虫配置  
crawler:
  max_images_per_actor: 20
  sources:
    - name: "tmdb_images"
      enabled: true
    - name: "google_images"  # 需要Google API密钥
      enabled: false
      
# 向量数据库配置
vector_database:
  type: "faiss"  # 或 "chromadb"
  index_type: "IVF"
```

## 技术特点

- **多源数据**：整合TMDB、豆瓣等多个数据源
- **高质量图片**：智能筛选高清正脸图片
- **向量检索**：支持相似人脸快速检索
- **增量更新**：支持数据库增量更新
- **Web管理**：直观的可视化管理界面
