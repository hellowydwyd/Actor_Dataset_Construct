#!/usr/bin/env python3
"""
中国环境优化启动脚本
针对国内网络环境和云平台进行优化
"""
import os
import sys
import locale
from pathlib import Path

# 设置中文环境
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['TZ'] = 'Asia/Shanghai'
os.environ['LANG'] = 'zh_CN.UTF-8'

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from web.app import create_app
from src.utils.logger import get_logger

logger = get_logger(__name__)

def setup_chinese_environment():
    """设置中文环境"""
    try:
        # 尝试设置中文locale
        locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
        logger.info("中文环境设置成功")
    except locale.Error:
        try:
            # 备用设置
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
            logger.info("使用UTF-8环境")
        except locale.Error:
            logger.warning("无法设置中文环境，使用默认设置")

def check_network():
    """检查网络连接"""
    import requests
    
    test_urls = [
        "https://api.themoviedb.org/3",
        "https://pypi.tuna.tsinghua.edu.cn/simple",
        "https://www.baidu.com"
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                logger.info(f"网络连接正常: {url}")
            else:
                logger.warning(f"网络连接异常: {url} (状态码: {response.status_code})")
        except Exception as e:
            logger.warning(f"网络连接测试失败: {url} - {e}")

def optimize_for_china():
    """中国环境优化设置"""
    # 设置pip镜像源
    pip_conf_dir = Path.home() / '.pip'
    pip_conf_dir.mkdir(exist_ok=True)
    
    pip_conf_file = pip_conf_dir / 'pip.conf'
    if not pip_conf_file.exists():
        pip_conf_content = """[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
timeout = 30
"""
        with open(pip_conf_file, 'w', encoding='utf-8') as f:
            f.write(pip_conf_content)
        logger.info("已配置pip国内镜像源")
    
    # 设置环境变量
    os.environ['PIP_INDEX_URL'] = 'https://pypi.tuna.tsinghua.edu.cn/simple'
    os.environ['PIP_TRUSTED_HOST'] = 'pypi.tuna.tsinghua.edu.cn'

def main():
    """主函数"""
    try:
        print("🇨🇳 启动中国优化版本...")
        print("="*50)
        
        # 环境设置
        setup_chinese_environment()
        optimize_for_china()
        
        # 网络检查
        logger.info("检查网络连接...")
        check_network()
        
        # 创建应用
        logger.info("初始化应用...")
        app = create_app()
        
        # 配置参数
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 8080))
        debug = os.getenv('DEBUG', 'false').lower() == 'true'
        
        # 显示启动信息
        print(f"🚀 应用启动配置:")
        print(f"   主机: {host}")
        print(f"   端口: {port}")
        print(f"   调试: {debug}")
        print(f"   环境: 中国优化版")
        print("="*50)
        
        logger.info(f"启动中国优化版本... (Host: {host}, Port: {port}, Debug: {debug})")
        
        # 启动提示
        if host == '0.0.0.0':
            print(f"🌐 本地访问: http://localhost:{port}")
            print(f"🌐 网络访问: http://你的IP地址:{port}")
        else:
            print(f"🌐 访问地址: http://{host}:{port}")
        
        print("\n✨ 应用启动中，请稍候...")
        print("📱 支持的功能:")
        print("   • 电影演员数据集构建")
        print("   • 人脸识别和向量搜索") 
        print("   • 视频人脸标注")
        print("   • 中文界面支持")
        
        # 启动应用
        app.run(host=host, port=port, debug=debug, threaded=True)
        
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        print("\n👋 应用已停止")
    except Exception as e:
        logger.error(f"启动失败: {e}")
        print(f"\n❌ 启动失败: {e}")
        print("\n🔧 故障排除建议:")
        print("1. 检查端口是否被占用")
        print("2. 确认网络连接正常")
        print("3. 检查依赖是否完整安装")
        print("4. 查看日志文件获取详细错误信息")
        sys.exit(1)

if __name__ == '__main__':
    main()
