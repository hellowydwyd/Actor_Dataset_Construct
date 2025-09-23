#!/usr/bin/env python3
"""
Vercel部署专用API入口文件
将Flask应用适配为Vercel Serverless Functions
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置Vercel环境标识
os.environ['VERCEL_ENV'] = 'true'
os.environ['CLOUDSTUDIO_ENV'] = 'false'

# 导入Flask应用
from web.app import create_app

# 创建应用实例
app = create_app()

# Vercel需要的处理函数
def handler(request):
    """Vercel请求处理函数"""
    return app(request.environ, start_response)

def start_response(status, headers):
    """WSGI start_response函数"""
    pass

# 如果作为模块导入，返回app实例
if __name__ != '__main__':
    # Vercel会导入这个模块并使用app实例
    application = app
else:
    # 本地测试时可以直接运行
    app.run(debug=True)
