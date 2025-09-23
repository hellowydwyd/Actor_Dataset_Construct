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

try:
    # 导入Flask应用
    from web.app import create_app
    
    # 创建应用实例
    app = create_app()
    
    # Vercel Serverless Functions入口点
    def handler(request, response):
        """Vercel请求处理函数"""
        return app
    
    # 直接导出app供Vercel使用
    application = app
    
except Exception as e:
    print(f"Error creating app: {e}")
    # 创建一个简单的fallback应用
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def hello():
        return 'Hello from Vercel!'
    
    application = app
