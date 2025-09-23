#!/usr/bin/env python3
"""
子路径部署启动脚本
适配 Nginx 反向代理环境
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from web.app import create_app
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """启动子路径Flask应用"""
    try:
        print("🌐 启动阿里云子路径部署版本...")
        print("="*50)
        
        # 创建应用
        app = create_app()
        
        # 子路径部署配置
        host = '127.0.0.1'  # 只监听本地，通过Nginx代理
        port = 5000         # 内部端口
        debug = False       # 生产环境
        
        print(f"⚙️  服务器配置:")
        print(f"   内部地址: http://{host}:{port}")
        print(f"   代理访问: http://灵织.cn/actor/")
        print(f"   API接口: http://灵织.cn/actor/api/")
        print(f"   生产模式: {not debug}")
        
        print(f"\n📋 访问方式:")
        print(f"   🌐 主站: http://灵织.cn/")
        print(f"   🎬 人脸识别: http://灵织.cn/actor/")
        print(f"   📡 API: http://灵织.cn/actor/api/")
        
        print(f"\n🔧 系统要求:")
        print(f"   • Nginx反向代理已配置")
        print(f"   • 端口5000未被占用")
        print(f"   • 防火墙已开放80/443端口")
        
        print(f"\n" + "="*50)
        print(f"🚀 正在启动服务器...")
        print(f"="*50)
        
        # 启动应用
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True,
            use_reloader=False  # 生产环境关闭重载
        )
        
    except KeyboardInterrupt:
        logger.info("用户中断启动")
        print("\n👋 服务已停止")
        
    except Exception as e:
        logger.error(f"启动失败: {e}")
        print(f"\n❌ 启动失败: {e}")
        print(f"\n🔧 故障排除:")
        print(f"1. 检查端口5000是否被占用: netstat -tlnp | grep 5000")
        print(f"2. 检查依赖是否完整安装")
        print(f"3. 检查API密钥配置")
        print(f"4. 查看详细日志: tail -f logs/system.log")
        sys.exit(1)

if __name__ == '__main__':
    main()
