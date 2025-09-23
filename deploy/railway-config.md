# Railway 部署配置 (推荐)

## 为什么选择 Railway

基于您的项目特点：
- ✅ **AI模型支持**: 足够的内存运行InsightFace
- ✅ **存储支持**: 持久化存储卷保存数据
- ✅ **自动扩容**: 根据使用情况自动调整资源
- ✅ **成本可控**: 免费额度 + 按需付费

## 部署步骤

### 1. 环境变量配置

在Railway控制台设置以下环境变量：

```bash
# 必需的环境变量
TMDB_API_KEY=your_tmdb_api_key_here
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=false

# 可选优化
PYTHONPATH=/app
PYTHONUNBUFFERED=1
```

### 2. 资源配置建议

```yaml
# 推荐配置
Memory: 2GB (足够运行AI模型)
CPU: 1 vCPU (处理图像和视频)
Storage: 5GB (持久化存储)
```

### 3. 启动命令

Railway会自动检测Python项目，但可以手动指定：

```bash
# 在railway.json中配置
"startCommand": "python run_web.py"
```

### 4. 性能优化

#### 模型缓存优化
```python
# 在配置中启用模型缓存
face_recognition:
  model_cache: true
  lazy_loading: true  # 懒加载模型
```

#### 内存优化
```python
# 限制并发处理
crawler:
  concurrent_downloads: 3  # 降低并发数
  max_images_per_actor: 15  # 限制图片数量
```

### 5. 监控和维护

Railway提供内置监控：
- CPU/内存使用率
- 请求响应时间  
- 错误日志
- 部署历史

## 成本估算

### 免费额度
- 500小时运行时间/月
- $5 账户余额
- 足够轻中度使用

### 付费成本 (超出免费额度)
- 内存: $0.000463/GB-hour ($0.33/GB/月)
- CPU: $0.000231/vCPU-hour ($0.17/vCPU/月)
- 网络: $0.1/GB

**预估月成本**: $5-15 (中等使用量)

## 部署检查清单

- [ ] 代码推送到GitHub
- [ ] 创建Railway账户
- [ ] 连接GitHub仓库
- [ ] 配置环境变量
- [ ] 设置存储卷 (可选)
- [ ] 测试部署
- [ ] 配置域名 (可选)
