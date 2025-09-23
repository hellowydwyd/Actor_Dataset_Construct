#!/usr/bin/env python3
"""
Cloud Studio 专用启动脚本
解决网络连接和端口配置问题
"""
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    try:
        print("🌐 Cloud Studio 专用启动脚本")
        print("=" * 50)
        
        # 检查依赖
        print("📦 检查依赖...")
        try:
            import flask
            import cv2
            import numpy as np
            print("✅ 核心依赖已安装")
        except ImportError as e:
            print(f"❌ 缺少依赖: {e}")
            print("💡 请先运行: pip install -r requirements-china.txt")
            return
        
        # 设置环境变量
        os.environ['PYTHONPATH'] = str(project_root)
        os.environ['FLASK_ENV'] = 'development'
        
        # 导入应用
        from web.app import create_app
        from src.utils.logger import get_logger
        
        logger = get_logger(__name__)
        
        print("🚀 创建Flask应用...")
        app = create_app()
        
        # Cloud Studio 专用配置
        host = "0.0.0.0"  # 关键！必须绑定所有接口
        port = 5000       # 使用标准Flask端口
        debug = True      # 开发环境启用调试
        
        print(f"⚙️  启动配置:")
        print(f"   主机: {host} (绑定所有网络接口)")
        print(f"   端口: {port}")
        print(f"   调试: {debug}")
        print(f"   环境: Cloud Studio")
        
        print("\n🔗 访问方式:")
        print(f"   本地: http://localhost:{port}")
        print(f"   公网: 等待Cloud Studio分配...")
        
        print("\n📱 支持功能:")
        print("   • 电影演员数据集构建")
        print("   • 人脸识别和搜索")
        print("   • 视频人脸标注")
        print("   • 中文界面支持")
        
        print("\n✨ 启动应用中...")
        print("=" * 50)
        
        # 启动Flask应用
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True,
            use_reloader=False  # Cloud Studio环境建议关闭自动重载
        )
        
    except KeyboardInterrupt:
        print("\n👋 应用已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("\n🔧 故障排除:")
        print("1. 检查是否安装了所有依赖")
        print("2. 确认TMDB API密钥配置正确")
        print("3. 检查端口是否被占用")
        print("4. 查看详细错误日志")
        sys.exit(1)

if __name__ == '__main__':
    main()
