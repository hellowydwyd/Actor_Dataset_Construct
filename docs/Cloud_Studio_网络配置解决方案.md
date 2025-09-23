# Cloud Studio 网络配置解决方案

## 🔧 问题诊断：拒绝连接

### 常见原因
1. **端口配置问题**: Flask默认绑定127.0.0.1，Cloud Studio无法访问
2. **防火墙限制**: 端口未正确暴露
3. **启动参数错误**: host参数设置不正确

## ✅ 解决方案

### 方法1: 修改启动命令 (推荐)

确保使用正确的启动参数：
```bash
# ❌ 错误的启动方式 (会拒绝连接)
python main.py web
python run.py web

# ✅ 正确的启动方式
python main.py web --host 0.0.0.0 --port 8080
```

### 方法2: 修改配置文件

编辑 `config/config.yaml`：
```yaml
# Web界面配置
web:
  host: "0.0.0.0"     # 关键！必须是0.0.0.0，不能是127.0.0.1
  port: 8080          # 使用8080端口 (Cloud Studio友好)
  debug: true         # 开发环境可以开启调试
```

### 方法3: 使用专门的Cloud Studio启动脚本

创建 `start_cloudstudio.py`：
```python
#!/usr/bin/env python3
"""
Cloud Studio 专用启动脚本
"""
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from web.app import create_app
from src.utils.logger import get_logger

logger = get_logger(__name__)

if __name__ == '__main__':
    try:
        print("🚀 启动Cloud Studio版本...")
        
        # 创建应用
        app = create_app()
        
        # Cloud Studio专用配置
        host = "0.0.0.0"  # 必须使用0.0.0.0
        port = 8080       # 推荐端口
        debug = True      # 开发环境
        
        print(f"🌐 启动配置:")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Debug: {debug}")
        print(f"🔗 访问地址: http://localhost:{port}")
        print("📱 等待Cloud Studio分配公网地址...")
        
        # 启动应用
        app.run(
            host=host, 
            port=port, 
            debug=debug,
            threaded=True,
            use_reloader=False  # Cloud Studio环境建议关闭重载
        )
        
    except Exception as e:
        logger.error(f"启动失败: {e}")
        print(f"❌ 启动失败: {e}")
        sys.exit(1)
```

## 🎯 完整的Cloud Studio部署流程

### 1. 启动应用
```bash
# 进入项目目录
cd Actor-Dataset-Construct

# 安装依赖
pip install -r requirements-china.txt

# 配置API密钥
cp config/env_example .env
nano .env  # 添加 TMDB_API_KEY=your_key

# 启动应用 (关键步骤)
python main.py web --host 0.0.0.0 --port 8080
```

### 2. 配置Cloud Studio端口转发
1. 在Cloud Studio界面中，查看左下角的 **"端口"** 面板
2. 确认8080端口已经被检测到
3. 点击端口右侧的 **"打开"** 或 **"预览"** 按钮

### 3. 如果端口未自动检测
手动添加端口转发：
1. 点击 **"端口"** 面板的 **"+"** 按钮
2. 输入端口号：`8080`
3. 设置为 **"公开"**
4. 点击 **"确定"**

## 🔍 故障排除

### 问题1: 应用启动但无法访问

**检查启动日志**:
```bash
# 确认应用是否正确启动
# 应该看到类似输出：
# * Running on all addresses (0.0.0.0)
# * Running on http://127.0.0.1:8080
# * Running on http://[外网IP]:8080
```

**解决方案**:
```bash
# 确保使用正确参数
python main.py web --host 0.0.0.0 --port 8080
```

### 问题2: 端口被占用

**检查端口使用**:
```bash
# 检查8080端口
netstat -tlnp | grep 8080

# 或使用其他端口
python main.py web --host 0.0.0.0 --port 3000
```

### 问题3: 权限问题

**解决方案**:
```bash
# 确保有执行权限
chmod +x main.py
chmod +x run.py

# 或使用python明确执行
python main.py web --host 0.0.0.0 --port 8080
```

### 问题4: Cloud Studio端口转发问题

**手动配置**:
1. 点击Cloud Studio界面左下角的 **"端口"**
2. 添加端口 `8080`
3. 设置为 **"公开访问"**
4. 复制分配的公网地址

## 🌐 验证部署成功

### 检查清单
- [ ] 应用在终端显示启动成功
- [ ] Cloud Studio检测到8080端口
- [ ] 可以通过预览按钮访问
- [ ] 页面正常加载，显示项目界面
- [ ] 功能模块可以正常使用

### 成功标志
看到类似输出表示成功：
```
🚀 启动Cloud Studio版本...
🌐 启动配置:
   Host: 0.0.0.0
   Port: 8080
   Debug: True
🔗 访问地址: http://localhost:8080
📱 等待Cloud Studio分配公网地址...

 * Serving Flask app 'web.app'
 * Debug mode: on
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8080
 * Running on http://[::]:8080
```

## 🎯 推荐的启动方式

**最佳实践命令**:
```bash
python main.py web --host 0.0.0.0 --port 8080
```

**参数说明**:
- `--host 0.0.0.0`: 绑定所有网络接口 (关键！)
- `--port 8080`: 使用Cloud Studio友好的端口
- 不使用 `--debug` 参数避免潜在问题
