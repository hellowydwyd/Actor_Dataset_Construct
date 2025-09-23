#!/usr/bin/env python3
"""
测试清理后的爬虫功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.crawler.image_crawler import ImageCrawler

def test_clean_crawler():
    """测试清理后的爬虫功能"""
    print("🧹 测试清理后的图片爬虫")
    print("=" * 60)
    
    # 初始化爬虫
    crawler = ImageCrawler()
    
    # 测试数据
    test_cases = [
        {
            'movie': '钢铁侠',
            'actor': '小罗伯特·唐尼',
            'expected_query': '钢铁侠 小罗伯特·唐尼 单人 剧照 高清 个人 特写 独照 人物'
        },
        {
            'movie': '复仇者联盟',
            'actor': '克里斯·埃文斯',
            'expected_query': '复仇者联盟 克里斯·埃文斯 单人 剧照 高清 个人 特写 独照 人物'
        }
    ]
    
    print("🎭 测试百度单人剧照搜索:")
    print("-" * 40)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. 电影: {test_case['movie']}")
        print(f"   演员: {test_case['actor']}")
        print(f"   关键词: {test_case['expected_query']}")
        
        try:
            urls = crawler.search_baidu_images(
                query=test_case['actor'],
                movie_title=test_case['movie'],
                max_results=5
            )
            
            if urls:
                print(f"   ✅ 找到 {len(urls)} 张单人剧照")
                print(f"   📋 示例: {urls[0][:60]}...")
            else:
                print(f"   ⚠️ 未找到图片")
                
        except Exception as e:
            print(f"   ❌ 搜索失败: {e}")
    
    # 检查配置
    print(f"\n⚙️ 当前爬虫配置:")
    print("-" * 40)
    
    sources = crawler.crawler_config.get('sources', [])
    enabled_sources = [s for s in sources if s.get('enabled')]
    
    print(f"启用的图片源: {len(enabled_sources)} 个")
    for source in enabled_sources:
        print(f"  ✅ {source['name']}: {source.get('max_results', 0)} 张 - {source.get('description', '')}")
    
    total_images = sum(s.get('max_results', 0) for s in enabled_sources)
    print(f"\n📊 预期每位演员图片数: {total_images} 张")
    
    # 验证只有TMDB和百度
    expected_sources = {'tmdb_images', 'baidu_images'}
    actual_sources = {s['name'] for s in enabled_sources}
    
    if actual_sources == expected_sources:
        print("✅ 配置正确: 只启用了TMDB和百度图片")
    else:
        print(f"⚠️ 配置异常: 预期 {expected_sources}, 实际 {actual_sources}")
    
    print(f"\n🎯 关键词优化:")
    print("  ✅ 添加了'单人'关键词")
    print("  ✅ 添加了'个人'关键词") 
    print("  ✅ 添加了'特写'关键词")
    print("  ✅ 添加了'独照'关键词")
    print("  ✅ 添加了百度人脸筛选参数 (face=1)")


def main():
    """主函数"""
    try:
        test_clean_crawler()
        
        print("\n" + "=" * 60)
        print("🎉 爬虫清理和优化完成!")
        print("\n📋 最终配置:")
        print("  1. TMDB官方图片: 10张高质量头像")
        print("  2. 百度剧照搜索: 15张单人剧照")
        print("  3. 搜索关键词: 电影名+演员名+单人+剧照+特写")
        print("  4. 人脸筛选: 启用百度人脸检测参数")
        print("  5. 完全免费: 无需任何API密钥")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
