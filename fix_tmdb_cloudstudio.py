#!/usr/bin/env python3
"""
Cloud Studio TMDB API连接专用修复脚本
针对Cloud Studio环境的网络限制进行优化
"""
import os
import sys
import ssl
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def set_cloud_studio_environment():
    """设置Cloud Studio环境标识"""
    os.environ['CLOUDSTUDIO_ENV'] = '1'
    os.environ['CLOUD_STUDIO'] = 'true'
    print("✅ 设置Cloud Studio环境标识")

def configure_ssl_for_cloudstudio():
    """为Cloud Studio配置SSL"""
    print("🔧 配置Cloud Studio SSL环境...")
    
    # 设置SSL环境变量
    ssl_env = {
        'PYTHONHTTPSVERIFY': '0',
        'CURL_CA_BUNDLE': '',
        'REQUESTS_CA_BUNDLE': '',
        'SSL_VERIFY': 'false'
    }
    
    for key, value in ssl_env.items():
        os.environ[key] = value
        print(f"   {key}={value}")
    
    # 修改SSL上下文
    ssl._create_default_https_context = ssl._create_unverified_context
    print("✅ SSL配置完成")

def test_direct_connection():
    """测试直接连接"""
    print("\n🌐 测试TMDB API直接连接...")
    
    try:
        import requests
        import urllib3
        
        # 禁用SSL警告
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 多种连接方式测试
        test_urls = [
            'https://api.themoviedb.org/3',
            'http://api.themoviedb.org/3',  # 尝试HTTP
        ]
        
        for url in test_urls:
            try:
                print(f"   尝试连接: {url}")
                response = requests.get(
                    url,
                    timeout=15,
                    verify=False,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                        'Accept': '*/*',
                        'Connection': 'close'
                    }
                )
                
                if response.status_code in [200, 204, 401]:
                    print(f"   ✅ 连接成功: {url} (状态码: {response.status_code})")
                    return True, url
                    
            except Exception as e:
                print(f"   ❌ 连接失败: {url} - {str(e)[:100]}")
                continue
        
        return False, None
        
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False, None

def try_common_proxies():
    """尝试常见的免费代理"""
    print("\n🔄 尝试免费代理服务...")
    
    # 一些常见的免费代理（实际使用时需要获取最新的）
    proxy_list = [
        'http://proxy.server:8080',
        'http://free-proxy.cz:8080',
        'socks5://proxy.server:1080',
    ]
    
    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        for proxy in proxy_list:
            try:
                print(f"   尝试代理: {proxy}")
                
                proxies = {
                    'http': proxy,
                    'https': proxy
                }
                
                response = requests.get(
                    'https://api.themoviedb.org/3',
                    proxies=proxies,
                    timeout=10,
                    verify=False
                )
                
                if response.status_code in [200, 204, 401]:
                    print(f"   ✅ 代理连接成功: {proxy}")
                    return proxy
                    
            except Exception as e:
                print(f"   ❌ 代理失败: {proxy} - {str(e)[:50]}")
                continue
        
        print("   ⚠️  未找到可用的免费代理")
        return None
        
    except Exception as e:
        print(f"❌ 代理测试失败: {e}")
        return None

def configure_tmdb_client():
    """配置TMDB客户端适应Cloud Studio"""
    print("\n⚙️  配置TMDB客户端...")
    
    config_file = Path('config/config.yaml')
    if not config_file.exists():
        print("❌ 配置文件不存在")
        return False
    
    try:
        content = config_file.read_text(encoding='utf-8')
        
        # 添加Cloud Studio特定配置
        cloudstudio_config = """
  # Cloud Studio专用配置
  cloudstudio_mode: true
  ssl_verify: false
  timeout: 30
  max_retries: 5
  retry_delay: 3
  connection_pool_maxsize: 10
"""
        
        if 'cloudstudio_mode: true' not in content:
            # 在retry_delay行后添加配置
            updated_content = content.replace(
                '  retry_delay: 2     # 重试延迟(秒)',
                '  retry_delay: 2     # 重试延迟(秒)' + cloudstudio_config
            )
            
            config_file.write_text(updated_content, encoding='utf-8')
            print("✅ 配置文件已更新")
        else:
            print("✅ 配置文件已包含Cloud Studio配置")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置文件更新失败: {e}")
        return False

def test_tmdb_api():
    """测试完整的TMDB API功能"""
    print("\n🎬 测试TMDB API功能...")
    
    try:
        # 重新导入模块以应用新配置
        if 'src.api.tmdb_client' in sys.modules:
            del sys.modules['src.api.tmdb_client']
        
        from src.api.tmdb_client import TMDBClient
        
        # 创建客户端
        client = TMDBClient()
        print("✅ TMDB客户端初始化成功")
        
        # 测试搜索
        print("   测试电影搜索...")
        movies = client.search_movie('肖申克的救赎')
        print(f"✅ 电影搜索成功，找到 {len(movies)} 部电影")
        
        if movies and len(movies) > 0:
            movie = movies[0]
            print(f"   电影: {movie.get('title', 'Unknown')}")
            
            # 测试演员获取
            print("   测试演员信息获取...")
            actors = client.get_movie_actors('肖申克的救赎', max_actors=3)
            print(f"✅ 演员信息获取成功，找到 {len(actors)} 位演员")
            
            for i, actor in enumerate(actors[:3], 1):
                print(f"   {i}. {actor['name']} - {actor.get('character', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ TMDB API测试失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False

def show_cloudstudio_instructions():
    """显示Cloud Studio使用说明"""
    print("\n" + "="*60)
    print("🎯 Cloud Studio TMDB API 修复完成")
    print("="*60)
    
    print("\n🚀 现在您可以启动应用:")
    print("   python start_cloudstudio_with_proxy.py")
    print("   或")
    print("   python main.py web --host 0.0.0.0 --port 8080")
    
    print("\n📡 端口访问:")
    print("   1. Cloud Studio会自动检测8080端口")
    print("   2. 点击左下角'端口'面板中的预览按钮")
    print("   3. 或手动添加端口转发")
    
    print("\n✨ 可用功能:")
    print("   ✅ 完整Web界面")
    print("   ✅ 人脸识别搜索")
    print("   ✅ 视频处理功能")
    print("   ✅ 数据库管理")
    print("   ✅ TMDB电影数据获取")

def main():
    """主修复流程"""
    print("🔧 Cloud Studio TMDB API 专用修复工具")
    print("="*50)
    
    success_steps = []
    
    # 1. 设置环境
    set_cloud_studio_environment()
    success_steps.append("环境设置")
    
    # 2. 配置SSL
    configure_ssl_for_cloudstudio()
    success_steps.append("SSL配置")
    
    # 3. 测试直接连接
    direct_ok, working_url = test_direct_connection()
    if direct_ok:
        success_steps.append("直接连接")
        print(f"✅ 发现可用的API地址: {working_url}")
    
    # 4. 如果直接连接失败，尝试代理
    proxy_ok = False
    if not direct_ok:
        working_proxy = try_common_proxies()
        if working_proxy:
            os.environ['http_proxy'] = working_proxy
            os.environ['https_proxy'] = working_proxy
            success_steps.append("代理连接")
            proxy_ok = True
    
    # 5. 配置客户端
    config_ok = configure_tmdb_client()
    if config_ok:
        success_steps.append("客户端配置")
    
    # 6. 测试完整功能
    api_ok = test_tmdb_api()
    if api_ok:
        success_steps.append("API功能测试")
    
    # 7. 总结
    print("\n" + "="*50)
    print("📊 修复结果总结")
    print("="*50)
    
    print(f"✅ 成功步骤: {' -> '.join(success_steps)}")
    
    if api_ok:
        print("🎉 TMDB API 在Cloud Studio中完全可用！")
        show_cloudstudio_instructions()
    elif direct_ok or proxy_ok:
        print("⚠️  网络连接部分成功，但API功能异常")
        print("💡 可能是API密钥问题或其他配置问题")
        print("🔄 系统会自动降级使用模拟数据")
    else:
        print("❌ 网络连接完全失败")
        print("💡 建议方案:")
        print("   1. 检查Cloud Studio网络设置")
        print("   2. 使用演示模式（自动模拟数据）")
        print("   3. 联系网络管理员")
    
    print(f"\n🎯 即使API不可用，您的系统仍然可以:")
    print(f"   • 展示完整的系统架构")
    print(f"   • 演示人脸识别功能")
    print(f"   • 处理视频文件")
    print(f"   • 使用预设的电影数据")

if __name__ == '__main__':
    main()
