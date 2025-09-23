#!/usr/bin/env python3
"""
Cloud Studio SSL连接问题修复脚本
解决 TLS/SSL connection has been closed (EOF) 错误
"""
import os
import sys
import ssl
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_ssl_environment():
    """修复SSL环境配置"""
    print("🔧 修复Cloud Studio SSL环境...")
    
    # 设置SSL相关环境变量
    ssl_fixes = {
        'PYTHONHTTPSVERIFY': '0',  # 禁用Python HTTPS验证
        'CURL_CA_BUNDLE': '',      # 清除curl证书路径
        'REQUESTS_CA_BUNDLE': '',  # 清除requests证书路径
        'SSL_VERIFY': '0'          # 自定义SSL验证标志
    }
    
    for key, value in ssl_fixes.items():
        os.environ[key] = value
        print(f"  ✅ 设置 {key}={value}")
    
    # 配置SSL上下文
    ssl._create_default_https_context = ssl._create_unverified_context
    print("  ✅ 配置SSL上下文为不验证模式")
    
    print("🎯 SSL环境修复完成")

def test_tmdb_connection():
    """测试TMDB连接"""
    print("\n🌐 测试TMDB API连接...")
    
    try:
        import requests
        import urllib3
        
        # 禁用SSL警告
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 测试基本连接
        response = requests.get(
            'https://api.themoviedb.org/3',
            timeout=10,
            verify=False  # 关键：禁用SSL验证
        )
        
        if response.status_code in [200, 204, 401]:
            print("  ✅ TMDB API基础连接成功")
            return True
        else:
            print(f"  ⚠️  TMDB API返回状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ 连接测试失败: {e}")
        return False

def test_tmdb_api_with_key():
    """使用API密钥测试完整功能"""
    print("\n🎬 测试TMDB API完整功能...")
    
    try:
        from src.api.tmdb_client import TMDBClient
        
        # 创建客户端
        client = TMDBClient()
        print("  ✅ TMDB客户端初始化成功")
        
        # 测试搜索
        movies = client.search_movie('肖申克的救赎')
        print(f"  ✅ 电影搜索成功，找到 {len(movies)} 部电影")
        
        if movies:
            # 测试演员获取
            actors = client.get_movie_actors('肖申克的救赎', max_actors=3)
            print(f"  ✅ 演员信息获取成功，找到 {len(actors)} 位演员")
            
            for actor in actors:
                print(f"    - {actor['name']}: {actor.get('character', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ API测试失败: {e}")
        return False

def apply_permanent_fix():
    """应用永久修复方案"""
    print("\n🛠️  应用永久SSL修复方案...")
    
    # 检查是否已经修复
    config_file = Path('config/config.yaml')
    if config_file.exists():
        content = config_file.read_text(encoding='utf-8')
        if 'ssl_verify: false' not in content:
            # 添加SSL配置
            ssl_config = """
  # SSL配置 (Cloud Studio环境)
  ssl_verify: false    # 禁用SSL验证解决Cloud Studio连接问题
  timeout: 30          # 增加超时时间
"""
            
            # 在tmdb配置块中添加SSL配置
            updated_content = content.replace(
                '  retry_delay: 2     # 重试延迟(秒)',
                '  retry_delay: 2     # 重试延迟(秒)' + ssl_config
            )
            
            config_file.write_text(updated_content, encoding='utf-8')
            print("  ✅ 已更新config.yaml添加SSL配置")
        else:
            print("  ℹ️  config.yaml已包含SSL配置")
    
    print("  ✅ 永久修复方案已应用")

def main():
    """主函数"""
    print("🚨 Cloud Studio SSL连接问题修复工具")
    print("="*50)
    
    # 1. 修复SSL环境
    fix_ssl_environment()
    
    # 2. 测试基础连接
    basic_ok = test_tmdb_connection()
    
    # 3. 测试完整API功能
    api_ok = test_tmdb_api_with_key()
    
    # 4. 应用永久修复
    apply_permanent_fix()
    
    # 5. 总结
    print("\n" + "="*50)
    print("📋 修复结果总结")
    print("="*50)
    print(f"🌐 基础连接: {'✅ 正常' if basic_ok else '❌ 异常'}")
    print(f"🎬 API功能: {'✅ 正常' if api_ok else '❌ 异常'}")
    
    if basic_ok and api_ok:
        print("\n🎉 SSL问题已完全修复！")
        print("✅ 您现在可以正常使用所有TMDB API功能")
        print("\n🚀 推荐启动命令:")
        print("   python start_cloudstudio_with_proxy.py")
        
    elif basic_ok and not api_ok:
        print("\n⚠️  基础连接正常，但API功能异常")
        print("💡 可能是API密钥问题，请检查config.yaml中的api_key配置")
        print("🔄 系统会自动使用模拟数据，演示功能不受影响")
        
    else:
        print("\n❌ SSL问题仍然存在")
        print("💡 建议方案:")
        print("   1. 重启Cloud Studio环境")
        print("   2. 使用演示模式（系统会自动降级到模拟数据）")
        print("   3. 联系Cloud Studio技术支持")
        
    print(f"\n📖 详细问题说明:")
    print(f"   SSL错误 'TLS/SSL connection has been closed (EOF)' 是Cloud Studio")
    print(f"   环境下的常见问题，通常由云端网络代理或SSL证书配置引起。")
    print(f"   本脚本通过禁用SSL验证来解决此问题。")

if __name__ == '__main__':
    main()
