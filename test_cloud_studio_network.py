#!/usr/bin/env python3
"""
Cloud Studio 网络连接测试脚本
诊断TMDB API连接问题并提供解决方案
"""
import sys
import os
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_basic_network():
    """测试基本网络连接"""
    print("🌐 测试基本网络连接...")
    
    try:
        import requests
        
        # 测试多个目标网站
        test_sites = [
            ('百度', 'https://www.baidu.com'),
            ('GitHub', 'https://api.github.com'),
            ('TMDB API', 'https://api.themoviedb.org/3'),
        ]
        
        results = {}
        
        for name, url in test_sites:
            try:
                start_time = time.time()
                response = requests.get(url, timeout=10)
                end_time = time.time()
                
                results[name] = {
                    'status': 'success',
                    'status_code': response.status_code,
                    'time': f"{(end_time - start_time)*1000:.0f}ms"
                }
                print(f"  ✅ {name}: {response.status_code} ({results[name]['time']})")
                
            except requests.exceptions.ConnectionError:
                results[name] = {'status': 'connection_error'}
                print(f"  ❌ {name}: 连接失败")
                
            except requests.exceptions.Timeout:
                results[name] = {'status': 'timeout'}
                print(f"  ⏰ {name}: 超时")
                
            except Exception as e:
                results[name] = {'status': 'error', 'error': str(e)}
                print(f"  ❌ {name}: {e}")
        
        return results
        
    except ImportError:
        print("  ❌ requests模块未安装")
        return {}

def test_proxy_connection():
    """测试代理连接"""
    print("\n🔧 测试代理配置...")
    
    # 检查环境变量
    http_proxy = os.getenv('http_proxy') or os.getenv('HTTP_PROXY')
    https_proxy = os.getenv('https_proxy') or os.getenv('HTTPS_PROXY')
    
    if not http_proxy and not https_proxy:
        print("  ℹ️  未检测到代理配置")
        return False
    
    print(f"  HTTP代理: {http_proxy or '未设置'}")
    print(f"  HTTPS代理: {https_proxy or '未设置'}")
    
    try:
        import requests
        
        # 使用代理测试连接
        proxies = {}
        if http_proxy:
            proxies['http'] = http_proxy
        if https_proxy:
            proxies['https'] = https_proxy
        
        response = requests.get('https://api.themoviedb.org/3', proxies=proxies, timeout=15)
        print(f"  ✅ 代理连接成功: {response.status_code}")
        return True
        
    except Exception as e:
        print(f"  ❌ 代理连接失败: {e}")
        return False

def test_tmdb_api():
    """测试TMDB API功能"""
    print("\n📽️  测试TMDB API功能...")
    
    try:
        from src.api.tmdb_client import TMDBClient
        
        print("  🔧 初始化TMDB客户端...")
        client = TMDBClient()
        print("  ✅ 客户端初始化成功")
        
        print("  🔍 测试电影搜索...")
        movies = client.search_movie('肖申克的救赎')
        print(f"  ✅ 搜索成功，找到 {len(movies)} 部电影")
        
        if movies:
            movie = movies[0]
            print(f"     电影: {movie.get('title', 'Unknown')}")
            
            print("  🎭 测试演员信息...")
            actors = client.get_movie_actors('肖申克的救赎', max_actors=3)
            print(f"  ✅ 获取演员成功，找到 {len(actors)} 位演员")
            
            for actor in actors:
                print(f"     演员: {actor['name']} - {actor.get('character', 'Unknown')}")
        
        return True
        
    except ValueError as e:
        if "API密钥" in str(e):
            print(f"  ❌ API配置错误: {e}")
            print("  💡 请在 config/config.yaml 中配置正确的 TMDB API 密钥")
        else:
            print(f"  ❌ 配置错误: {e}")
        return False
        
    except Exception as e:
        print(f"  ❌ TMDB API测试失败: {e}")
        
        # 检查是否是网络问题
        if any(keyword in str(e).lower() for keyword in ['connection', 'timeout', 'network']):
            print("  💡 这看起来是网络连接问题")
            return False
        
        return False

def suggest_solutions(network_results, proxy_works, api_works):
    """根据测试结果建议解决方案"""
    print("\n" + "="*50)
    print("💡 解决方案建议")
    print("="*50)
    
    if api_works:
        print("🎉 TMDB API 工作正常！")
        print("✅ 您可以正常使用所有功能")
        return
    
    if not network_results.get('TMDB API', {}).get('status') == 'success':
        print("❌ TMDB API 网络连接失败")
        print()
        print("🔧 推荐解决方案:")
        print()
        
        print("方案1: 配置HTTP代理")
        print("```bash")
        print("# 获取免费代理地址（访问以下网站）:")
        print("# - http://proxy-list.org/")
        print("# - https://free-proxy-list.net/")
        print()
        print("# 设置代理环境变量:")
        print("export http_proxy=http://proxy-ip:proxy-port")
        print("export https_proxy=http://proxy-ip:proxy-port")
        print()
        print("# 启动应用:")
        print("python start_cloudstudio_with_proxy.py")
        print("```")
        print()
        
        print("方案2: 修改配置文件")
        print("编辑 config/config.yaml:")
        print("```yaml")
        print("tmdb:")
        print("  proxy:")
        print("    enabled: true")
        print("    http_proxy: 'http://proxy-ip:proxy-port'")
        print("    https_proxy: 'http://proxy-ip:proxy-port'")
        print("```")
        print()
        
        print("方案3: 演示模式（推荐）")
        print("即使无法连接TMDB API，系统仍可正常演示:")
        print("• ✅ 人脸识别功能（上传本地图片）")
        print("• ✅ 视频处理功能（处理本地视频）")
        print("• ✅ 数据库管理界面")
        print("• ✅ 系统架构展示")
        print("• ✅ 使用模拟电影数据")
        print()
        print("启动命令:")
        print("python start_cloudstudio_with_proxy.py")
        print()
        
    else:
        print("❌ 其他配置问题")
        print("请检查 API 密钥和配置文件")

def main():
    """主函数"""
    print("🔍 Cloud Studio 网络诊断工具")
    print("="*50)
    
    # 基本网络测试
    network_results = test_basic_network()
    
    # 代理测试
    proxy_works = test_proxy_connection()
    
    # TMDB API测试
    api_works = test_tmdb_api()
    
    # 建议解决方案
    suggest_solutions(network_results, proxy_works, api_works)
    
    print("\n" + "="*50)
    print("📋 测试总结")
    print("="*50)
    print(f"🌐 基本网络: {'✅ 正常' if network_results.get('百度', {}).get('status') == 'success' else '❌ 异常'}")
    print(f"🔧 代理配置: {'✅ 已配置' if proxy_works else 'ℹ️ 未配置'}")
    print(f"📽️  TMDB API: {'✅ 正常' if api_works else '❌ 需要修复'}")
    
    if not api_works:
        print(f"\n💡 建议操作:")
        print(f"1. 配置代理服务器")
        print(f"2. 或直接启动演示模式: python start_cloudstudio_with_proxy.py")

if __name__ == '__main__':
    main()
