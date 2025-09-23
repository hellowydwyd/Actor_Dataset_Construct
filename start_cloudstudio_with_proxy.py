#!/usr/bin/env python3
"""
Cloud Studio 专用启动脚本 (带代理配置)
解决TMDB API网络连接问题
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

def setup_proxy_environment():
    """设置代理环境变量"""
    
    print("🔧 配置代理环境...")
    
    # 常用的免费代理列表 (需要用户自己找最新的可用代理)
    # 这里提供几个示例，实际使用时需要替换为可用的代理
    proxy_suggestions = [
        "http://proxy-server:port",
        "socks5://proxy-server:port"
    ]
    
    # 检查是否已经设置了代理
    current_http_proxy = os.getenv('http_proxy') or os.getenv('HTTP_PROXY')
    current_https_proxy = os.getenv('https_proxy') or os.getenv('HTTPS_PROXY')
    
    if current_http_proxy or current_https_proxy:
        print(f"✅ 检测到已设置代理:")
        if current_http_proxy:
            print(f"   HTTP代理: {current_http_proxy}")
        if current_https_proxy:
            print(f"   HTTPS代理: {current_https_proxy}")
        return True
    
    print("❌ 未检测到代理配置")
    print("💡 TMDB API可能无法访问，建议配置代理:")
    print("   方法1: 设置环境变量")
    print("     export http_proxy=http://your-proxy:port")
    print("     export https_proxy=http://your-proxy:port")
    print()
    print("   方法2: 修改 config/config.yaml")
    print("     tmdb.proxy.enabled: true")
    print("     tmdb.proxy.http_proxy: 'http://your-proxy:port'")
    print()
    print("   方法3: 使用免费代理服务")
    for proxy in proxy_suggestions:
        print(f"     {proxy}")
    print()
    print("🎯 即使无代理，系统也会使用模拟数据进行演示")
    
    return False

def test_network_connectivity():
    """测试网络连接性"""
    print("🌐 测试网络连接...")
    
    try:
        import requests
        
        # 测试基本网络连接
        response = requests.get('https://api.themoviedb.org/3', timeout=10)
        if response.status_code in [200, 204, 401]:  # 401也表示网络连通，只是缺少API密钥
            print("✅ TMDB API 网络连接正常")
            return True
        else:
            print(f"⚠️  TMDB API 返回状态码: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 网络连接失败，可能需要代理")
        return False
    except requests.exceptions.Timeout:
        print("❌ 网络超时，建议使用代理")
        return False
    except Exception as e:
        print(f"❌ 网络测试失败: {e}")
        return False

def show_deployment_instructions():
    """显示部署说明"""
    print("\n" + "="*50)
    print("🚀 Cloud Studio 部署指南")
    print("="*50)
    print()
    print("📋 完整部署步骤:")
    print("1. 安装依赖: pip install -r requirements-china.txt")
    print("2. 配置API: 编辑 config/config.yaml 中的 api_key")
    print("3. 启动应用: python start_cloudstudio_with_proxy.py")
    print("4. 访问端口: Cloud Studio会自动分配公网地址")
    print()
    print("🔧 如果TMDB API无法访问:")
    print("• 方案1: 配置代理服务器")
    print("• 方案2: 使用演示模式(系统会使用模拟数据)")
    print("• 方案3: 展示已构建的数据库内容")
    print()
    print("💡 推荐演示流程:")
    print("1. 展示系统架构和代码结构")
    print("2. 演示人脸识别功能 (上传本地图片)")
    print("3. 演示视频处理功能 (处理本地视频)")
    print("4. 展示数据库管理界面")
    print()

if __name__ == '__main__':
    try:
        print("🎬 Cloud Studio 演员人脸识别系统启动")
        print("=" * 50)
        
        # 显示部署指南
        show_deployment_instructions()
        
        # 检查代理配置
        has_proxy = setup_proxy_environment()
        
        # 测试网络连接
        network_ok = test_network_connectivity()
        
        if not network_ok and not has_proxy:
            print("\n⚠️  网络连接问题检测到!")
            print("💡 系统将启用模拟数据模式，您仍然可以:")
            print("   • 演示系统界面和功能")
            print("   • 测试人脸识别 (上传图片)")
            print("   • 处理视频文件")
            print("   • 管理现有数据库")
            
            choice = input("\n🤔 是否继续启动? (y/n): ").lower().strip()
            if choice != 'y':
                print("👋 启动已取消")
                sys.exit(0)
        
        print("\n🚀 启动Web应用...")
        
        # 创建Flask应用
        app = create_app()
        
        # Cloud Studio专用配置
        host = "0.0.0.0"  # 必须使用0.0.0.0
        port = int(os.getenv('PORT', 8080))  # Cloud Studio环境变量或默认8080
        debug = True
        
        print(f"\n🌐 服务器配置:")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Debug: {debug}")
        print(f"   代理状态: {'已配置' if has_proxy else '未配置'}")
        print(f"   网络状态: {'正常' if network_ok else '需要代理'}")
        
        print(f"\n🔗 访问地址:")
        print(f"   本地: http://localhost:{port}")
        print(f"   Cloud Studio: 等待分配公网地址...")
        
        print(f"\n📋 启动完成后，您可以:")
        print(f"   • 点击 Cloud Studio 的预览按钮")
        print(f"   • 或在端口面板中打开 {port} 端口")
        
        print("\n" + "="*50)
        print("🎉 正在启动服务器...")
        print("="*50)
        
        # 启动应用
        app.run(
            host=host, 
            port=port, 
            debug=debug,
            threaded=True,
            use_reloader=False  # Cloud Studio环境建议关闭重载
        )
        
    except KeyboardInterrupt:
        print("\n👋 用户中断启动")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("\n🔧 故障排除建议:")
        print("1. 检查端口是否被占用: netstat -tlnp | grep 8080")
        print("2. 尝试不同端口: PORT=3000 python start_cloudstudio_with_proxy.py")
        print("3. 检查防火墙设置")
        print("4. 查看详细错误日志")
        sys.exit(1)
