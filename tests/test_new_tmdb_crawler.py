#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试新的纯TMDB图片爬虫
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent))

from src.crawler.image_crawler import ImageCrawler
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_single_actor():
    """测试单个演员图片收集"""
    print("="*60)
    print("测试单个演员图片收集")
    print("="*60)
    
    crawler = ImageCrawler()
    
    # 测试演员
    test_actor = "阿尔·帕西诺"
    test_movie = "教父"
    
    try:
        image_paths = crawler.collect_actor_images(
            actor_name=test_actor,
            movie_title=test_movie
        )
        
        print(f"\n✅ 单个演员测试完成:")
        print(f"   演员: {test_actor}")
        print(f"   电影: {test_movie}")
        print(f"   图片数量: {len(image_paths)}")
        
        if image_paths:
            print(f"   保存路径示例:")
            for i, path in enumerate(image_paths[:3], 1):
                print(f"     {i}. {path}")
            if len(image_paths) > 3:
                print(f"     ... 还有 {len(image_paths) - 3} 张图片")
        
        return len(image_paths) > 0
        
    except Exception as e:
        print(f"❌ 单个演员测试失败: {e}")
        return False


def test_batch_actors():
    """测试批量演员图片收集"""
    print("\n" + "="*60)
    print("测试批量演员图片收集")
    print("="*60)
    
    crawler = ImageCrawler()
    
    # 测试演员列表
    test_actors = [
        {"name": "阿尔·帕西诺", "id": 1158},
        {"name": "马龙·白兰度", "id": 3084},
        {"name": "詹姆斯·凯恩", "id": 3085}
    ]
    test_movie = "教父"
    
    try:
        results = crawler.batch_collect_images(
            actors=test_actors,
            movie_title=test_movie
        )
        
        print(f"\n✅ 批量演员测试完成:")
        print(f"   电影: {test_movie}")
        print(f"   演员数量: {len(test_actors)}")
        
        total_images = 0
        for actor_name, image_paths in results.items():
            print(f"   {actor_name}: {len(image_paths)} 张图片")
            total_images += len(image_paths)
        
        print(f"   总图片数: {total_images}")
        
        return total_images > 0
        
    except Exception as e:
        print(f"❌ 批量演员测试失败: {e}")
        return False


def test_crawler_stats():
    """测试爬虫统计信息"""
    print("\n" + "="*60)
    print("爬虫统计信息")
    print("="*60)
    
    crawler = ImageCrawler()
    
    # 先运行一个小测试产生统计数据
    crawler.collect_actor_images("汤姆·汉克斯", movie_title="阿甘正传")
    
    stats = crawler.get_crawler_stats()
    
    print("📊 统计信息:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    return True


def main():
    """主测试函数"""
    print("开始测试新的纯TMDB图片爬虫")
    print("="*60)
    
    test_results = []
    
    # 测试1: 单个演员
    test_results.append(("单个演员测试", test_single_actor()))
    
    # 测试2: 批量演员
    test_results.append(("批量演员测试", test_batch_actors()))
    
    # 测试3: 统计信息
    test_results.append(("统计信息测试", test_crawler_stats()))
    
    # 输出测试结果
    print("\n" + "="*60)
    print("测试结果总结")
    print("="*60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总结: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试都通过了！新的TMDB图片爬虫工作正常。")
    else:
        print("⚠️  有测试失败，请检查错误信息。")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
