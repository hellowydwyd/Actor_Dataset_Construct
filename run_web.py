#!/usr/bin/env python3
"""
生产环境Web应用启动脚本
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from web.app import create_app
from src.utils.logger import get_logger

logger = get_logger(__name__)

if __name__ == '__main__':
    try:
        # 创建Flask应用
        app = create_app()
        
        # 从环境变量获取配置
        host = os.getenv('WEB_HOST', '0.0.0.0')
        port = int(os.getenv('WEB_PORT', os.getenv('PORT', 5000)))
        debug = os.getenv('WEB_DEBUG', 'false').lower() == 'true'
        
        # 启动应用
        logger.info(f"启动电影演员人脸数据库构建系统... (Host: {host}, Port: {port}, Debug: {debug})")
        app.run(host=host, port=port, debug=debug)
        
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        raise

